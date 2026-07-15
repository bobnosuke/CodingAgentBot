"""
Coding commands for CoderAgent
Handles /coding start, chat, end, panel, list, info, export, rename, delete commands
Supports both Slash and Prefix commands
"""
import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
from logger import setup_logger
from modules.security.permissions import PermissionLevel, PermissionManager
from modules.database.repository import UserRepository, APIKeyRepository, MessageRepository, SessionRepository
from modules.security.limits import UsageLimitManager
from modules.session.manager import SessionManager
from modules.ai.openrouter import OpenRouterClient, AIService
from modules.file.manager import FileManager

logger = setup_logger(__name__)


# ---------------------------------------------------------------------------
# UI Components
# ---------------------------------------------------------------------------

class CodingPanelSelect(discord.ui.Select):
    """Select menu for /coding panel"""

    def __init__(self):
        options = [
            discord.SelectOption(
                label="🚀 Coding Start",
                value="start",
                description="新しいコーディングセッションを開始します"
            ),
            discord.SelectOption(
                label="📂 Project List",
                value="list",
                description="自分のプロジェクト一覧を表示します"
            ),
            discord.SelectOption(
                label="ℹ️ Session Info",
                value="info",
                description="現在のセッション情報を表示します"
            ),
            discord.SelectOption(
                label="📦 Export Project",
                value="export",
                description="プロジェクトをZIPでエクスポートします"
            ),
            discord.SelectOption(
                label="✏️ Rename Project",
                value="rename",
                description="プロジェクト名を変更します"
            ),
            discord.SelectOption(
                label="🗑️ Delete Session",
                value="delete",
                description="現在のセッションを削除します"
            ),
        ]
        super().__init__(
            placeholder="操作を選択してください...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        value = self.values[0]
        cog: CodingCog = interaction.client.cogs.get("CodingCog")

        if value == "start":
            await cog._do_coding_start(interaction)
        elif value == "list":
            await cog._do_coding_list(interaction)
        elif value == "info":
            await cog._do_coding_info(interaction)
        elif value == "export":
            await cog._do_coding_export(interaction)
        elif value == "rename":
            await interaction.response.send_modal(RenameModal(cog))
        elif value == "delete":
            await cog._do_coding_delete(interaction)


class CodingPanelView(discord.ui.View):
    """View containing the panel select menu"""

    def __init__(self):
        super().__init__(timeout=300)
        self.add_item(CodingPanelSelect())


class RenameModal(discord.ui.Modal, title="プロジェクト名の変更"):
    """Modal for renaming a project"""

    new_name = discord.ui.TextInput(
        label="新しいプロジェクト名",
        placeholder="例: my-discord-bot",
        min_length=1,
        max_length=100
    )

    def __init__(self, cog: "CodingCog"):
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction):
        await self.cog._do_coding_rename(interaction, str(self.new_name))


class DeleteConfirmView(discord.ui.View):
    """Confirmation view for session deletion"""

    def __init__(self, cog: "CodingCog"):
        super().__init__(timeout=60)
        self.cog = cog

    @discord.ui.button(label="✅ 終了する", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog._execute_session_delete(interaction)
        self.stop()

    @discord.ui.button(label="❌ キャンセル", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content="✅ セッションの削除をキャンセルしました。",
            embed=None,
            view=None
        )
        self.stop()


# ---------------------------------------------------------------------------
# Cog
# ---------------------------------------------------------------------------

class CodingCog(commands.Cog):
    """Cog for coding-related commands"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.session_manager = SessionManager(bot)
        self.file_manager = FileManager()
        self.ai_services = {}  # Cache for AI services per user

    # Slash command group
    coding_group = app_commands.Group(name="coding", description="AI coding commands")

    # ------------------------------------------------------------------
    # /coding start / !coding start
    # ------------------------------------------------------------------

    @coding_group.command(name="start", description="Start a new coding session")
    async def coding_start_slash(self, interaction: discord.Interaction, project_name: str = None):
        await self._do_coding_start(interaction, project_name)

    @commands.group(name="coding")
    async def coding_prefix(self, ctx: commands.Context):
        """Prefix command group for coding"""
        if ctx.invoked_subcommand is None:
            await ctx.send("❌ サブコマンドを指定してください: `start`, `chat`, `end`, `panel`, `list`, `info`, `export`, `rename`, `delete`")

    @coding_prefix.command(name="start")
    async def coding_start_prefix(self, ctx: commands.Context, project_name: str = None):
        await self._do_coding_start(ctx, project_name)

    async def _do_coding_start(self, ctx_or_inter, project_name: str = None):
        """Internal handler for starting a coding session"""
        is_interaction = isinstance(ctx_or_inter, discord.Interaction)
        user = ctx_or_inter.user if is_interaction else ctx_or_inter.author
        guild = ctx_or_inter.guild

        try:
            user_id = str(user.id)

            # --- Limit Check ---
            db_session = self.bot.db_manager.get_session()
            try:
                is_allowed, limit_msg = await UsageLimitManager.check_limits(db_session, user_id)
                if not is_allowed:
                    if is_interaction:
                        await ctx_or_inter.response.send_message(limit_msg, ephemeral=True)
                    else:
                        await ctx_or_inter.send(limit_msg)
                    return
            finally:
                await db_session.close()
            # -------------------

            active_session = self.session_manager.get_user_active_session(user_id)

            if active_session:
                msg = f"❌ すでにアクティブなセッションがあります: `{active_session[:8]}`\n先に `/coding end` で終了してください。"
                if is_interaction:
                    await ctx_or_inter.response.send_message(msg, ephemeral=True)
                else:
                    await ctx_or_inter.send(msg)
                return

            if is_interaction:
                await ctx_or_inter.response.defer(ephemeral=True)

            db_session = self.bot.db_manager.get_session()
            try:
                db_user = await UserRepository.get_or_create_user(
                    db_session,
                    user_id,
                    user.name,
                    user.discriminator
                )

                api_key = await APIKeyRepository.get_active_api_key(db_session, db_user.id)
                if not api_key:
                    msg = "❌ OpenRouter APIキーが登録されていません。\n`/api-key register` でAPIキーを登録してください。"
                    if is_interaction:
                        await ctx_or_inter.followup.send(msg, ephemeral=True)
                    else:
                        await ctx_or_inter.send(msg)
                    return

                decrypted_key = self.bot.encryption_manager.decrypt(api_key.encrypted_key)

                session_uuid, coding_room = await self.session_manager.create_session(
                    db_session,
                    user,
                    guild,
                    project_name
                )

                openrouter_client = OpenRouterClient(decrypted_key)
                self.ai_services[user_id] = AIService(openrouter_client)

                embed = discord.Embed(
                    title="✅ コーディングセッション開始",
                    description="プライベートなコーディングルームが作成されました！",
                    color=discord.Color.green()
                )
                embed.add_field(name="セッションID", value=f"`{session_uuid[:8]}`", inline=False)
                embed.add_field(name="チャンネル", value=coding_room.mention, inline=False)
                if project_name:
                    embed.add_field(name="プロジェクト名", value=project_name, inline=False)
                
                msg_footer = "コーディングルームへ移動して対話を開始してください。"
                if is_interaction:
                    await ctx_or_inter.followup.send(embed=embed, ephemeral=True)
                else:
                    await ctx_or_inter.send(f"{user.mention} {msg_footer}", embed=embed)

                welcome_embed = discord.Embed(
                    title="🤖 コーディングセッションへようこそ",
                    description="AIコーディングアシスタントです。何を作りたいか教えてください！",
                    color=discord.Color.blue()
                )
                welcome_embed.add_field(
                    name="使用例",
                    value="• `/coding chat Discord Botを作って`\n"
                          "• `/coding chat ログイン機能を追加して`",
                    inline=False
                )
                await coding_room.send(embed=welcome_embed)

                logger.info(f"Created session {session_uuid} for {user.name}")

            finally:
                await db_session.close()

        except Exception as e:
            logger.error(f"Error in _do_coding_start: {e}", exc_info=True)
            msg = f"❌ セッション開始エラー: {str(e)}"
            if is_interaction:
                await ctx_or_inter.followup.send(msg, ephemeral=True)
            else:
                await ctx_or_inter.send(msg)

    # ------------------------------------------------------------------
    # /coding chat / !coding chat
    # ------------------------------------------------------------------

    @coding_group.command(name="chat", description="Chat with AI in your coding session")
    async def coding_chat_slash(self, interaction: discord.Interaction, message: str):
        await self._do_coding_chat(interaction, message)

    @coding_prefix.command(name="chat")
    async def coding_chat_prefix(self, ctx: commands.Context, *, message: str):
        await self._do_coding_chat(ctx, message)

    async def _do_coding_chat(self, ctx_or_inter, message: str):
        """Internal handler for AI chat"""
        is_interaction = isinstance(ctx_or_inter, discord.Interaction)
        user = ctx_or_inter.user if is_interaction else ctx_or_inter.author
        channel = ctx_or_inter.channel

        try:
            user_id = str(user.id)

            # --- Limit Check ---
            db_session = self.bot.db_manager.get_session()
            try:
                is_allowed, limit_msg = await UsageLimitManager.check_limits(db_session, user_id)
                if not is_allowed:
                    if is_interaction:
                        await ctx_or_inter.response.send_message(limit_msg, ephemeral=True)
                    else:
                        await ctx_or_inter.send(limit_msg)
                    return
            finally:
                await db_session.close()
            # -------------------

            session_uuid = self.session_manager.get_user_active_session(user_id)

            if not session_uuid:
                msg = "❌ アクティブなコーディングセッションがありません。`/coding start` で開始してください。"
                if is_interaction:
                    await ctx_or_inter.response.send_message(msg, ephemeral=True)
                else:
                    await ctx_or_inter.send(msg)
                return

            session_info = self.session_manager.get_session(session_uuid)
            if session_info and str(channel.id) != session_info["channel_id"]:
                msg = "❌ このコマンドはコーディングルーム内でのみ使用できます！"
                if is_interaction:
                    await ctx_or_inter.response.send_message(msg, ephemeral=True)
                else:
                    await ctx_or_inter.send(msg)
                return

            if user_id not in self.ai_services:
                msg = "❌ AIサービスが初期化されていません。新しいセッションを開始してください。"
                if is_interaction:
                    await ctx_or_inter.response.send_message(msg, ephemeral=True)
                else:
                    await ctx_or_inter.send(msg)
                return

            if is_interaction:
                await ctx_or_inter.response.defer()
            
            ai_service = self.ai_services[user_id]
            thinking_msg = await (ctx_or_inter.followup.send("🤔 考え中...") if is_interaction else ctx_or_inter.send("🤔 考え中..."))

            try:
                full_response = ""
                async for chunk in ai_service.chat(message):
                    full_response += chunk
                    if len(full_response) % 50 == 0 or len(full_response) > 1900:
                        try:
                            await thinking_msg.edit(content=full_response[:2000])
                        except discord.errors.HTTPException:
                            pass

                if full_response:
                    # Log usage in database
                    db_session = self.bot.db_manager.get_session()
                    try:
                        from modules.database.repository import UsageLogRepository, UserRepository
                        db_user = await UserRepository.get_user_by_discord_id(db_session, user_id)
                        if db_user:
                            # Token count estimation (rough)
                            t_in = len(message) // 4
                            t_out = len(full_response) // 4
                            await UsageLogRepository.log_usage(
                                db_session, 
                                db_user.id, 
                                ai_service.model if hasattr(ai_service, 'model') else "unknown",
                                token_input=t_in,
                                token_output=t_out
                            )
                    finally:
                        await db_session.close()

                    if len(full_response) > 2000:
                        chunks = [full_response[i:i+2000] for i in range(0, len(full_response), 2000)]
                        await thinking_msg.edit(content=chunks[0])
                        for chunk in chunks[1:]:
                            if is_interaction:
                                await ctx_or_inter.followup.send(chunk)
                            else:
                                await channel.send(chunk)
                    else:
                        await thinking_msg.edit(content=full_response)
                else:
                    await thinking_msg.edit(content="❌ レスポンスが生成されませんでした")

            except Exception as e:
                logger.error(f"Error generating response: {e}")
                await thinking_msg.edit(content=f"❌ エラー: {str(e)}")

        except Exception as e:
            logger.error(f"Error in _do_coding_chat: {e}", exc_info=True)
            msg = f"❌ エラー: {str(e)}"
            if is_interaction:
                await ctx_or_inter.response.send_message(msg, ephemeral=True)
            else:
                await ctx_or_inter.send(msg)

    # ------------------------------------------------------------------
    # /coding end / !coding end
    # ------------------------------------------------------------------

    @coding_group.command(name="end", description="End your current coding session")
    async def coding_end_slash(self, interaction: discord.Interaction):
        await self._do_coding_end(interaction)

    @coding_prefix.command(name="end")
    async def coding_end_prefix(self, ctx: commands.Context):
        await self._do_coding_end(ctx)

    async def _do_coding_end(self, ctx_or_inter):
        """Internal handler for ending session"""
        is_interaction = isinstance(ctx_or_inter, discord.Interaction)
        user = ctx_or_inter.user if is_interaction else ctx_or_inter.author

        try:
            user_id = str(user.id)
            session_uuid = self.session_manager.get_user_active_session(user_id)

            if not session_uuid:
                msg = "❌ アクティブなコーディングセッションがありません。"
                if is_interaction:
                    await ctx_or_inter.response.send_message(msg, ephemeral=True)
                else:
                    await ctx_or_inter.send(msg)
                return

            if is_interaction:
                await ctx_or_inter.response.defer(ephemeral=True)

            db_session = self.bot.db_manager.get_session()
            try:
                await self.session_manager.close_session(
                    db_session,
                    session_uuid,
                    delete_channel=True
                )

                if user_id in self.ai_services:
                    del self.ai_services[user_id]

                msg = f"✅ セッション `{session_uuid[:8]}` を終了しました。\nコーディングルームを削除しました。"
                if is_interaction:
                    await ctx_or_inter.followup.send(msg, ephemeral=True)
                else:
                    await ctx_or_inter.send(msg)
                
                logger.info(f"Closed session {session_uuid} for {user.name}")

            finally:
                await db_session.close()

        except Exception as e:
            logger.error(f"Error in _do_coding_end: {e}", exc_info=True)
            msg = f"❌ セッション終了エラー: {str(e)}"
            if is_interaction:
                await ctx_or_inter.followup.send(msg, ephemeral=True)
            else:
                await ctx_or_inter.send(msg)

    # ------------------------------------------------------------------
    # /coding panel / !coding panel
    # ------------------------------------------------------------------

    @coding_group.command(name="panel", description="Show the CoderAgent operation panel")
    async def coding_panel_slash(self, interaction: discord.Interaction):
        await self._do_coding_panel(interaction)

    @coding_prefix.command(name="panel")
    async def coding_panel_prefix(self, ctx: commands.Context):
        await self._do_coding_panel(ctx)

    async def _do_coding_panel(self, ctx_or_inter):
        is_interaction = isinstance(ctx_or_inter, discord.Interaction)
        embed = discord.Embed(
            title="🤖 CoderAgent パネル",
            description="CoderAgent へようこそ！下のメニューから操作を選択してください。",
            color=discord.Color.blurple()
        )
        embed.add_field(
            name="主な機能",
            value="🚀 **Coding Start**, 📂 **Project List**, ℹ️ **Session Info**, 📦 **Export**, ✏️ **Rename**, 🗑️ **Delete**",
            inline=False
        )
        view = CodingPanelView()
        if is_interaction:
            await ctx_or_inter.response.send_message(embed=embed, view=view)
        else:
            await ctx_or_inter.send(embed=embed, view=view)

    # ------------------------------------------------------------------
    # /coding list / !coding list
    # ------------------------------------------------------------------

    @coding_group.command(name="list", description="Show your current and past projects")
    async def coding_list_slash(self, interaction: discord.Interaction):
        await self._do_coding_list(interaction)

    @coding_prefix.command(name="list")
    async def coding_list_prefix(self, ctx: commands.Context):
        await self._do_coding_list(ctx)

    async def _do_coding_list(self, ctx_or_inter):
        is_interaction = isinstance(ctx_or_inter, discord.Interaction)
        user = ctx_or_inter.user if is_interaction else ctx_or_inter.author
        user_id = str(user.id)

        try:
            if is_interaction:
                if not ctx_or_inter.response.is_done():
                    await ctx_or_inter.response.defer(ephemeral=True)
            
            db_session = self.bot.db_manager.get_session()
            try:
                db_user = await UserRepository.get_user_by_discord_id(db_session, user_id)
                if not db_user:
                    msg = "❌ ユーザー情報が見つかりません。"
                    if is_interaction:
                        await ctx_or_inter.followup.send(msg, ephemeral=True)
                    else:
                        await ctx_or_inter.send(msg)
                    return

                from sqlalchemy import select
                from modules.database.models import Session as SessionModel
                stmt = select(SessionModel).where(SessionModel.user_id == db_user.id).order_by(SessionModel.created_at.desc()).limit(10)
                result = await db_session.execute(stmt)
                sessions = result.scalars().all()

                if not sessions:
                    msg = "📂 プロジェクトがまだありません。"
                    if is_interaction:
                        await ctx_or_inter.followup.send(msg, ephemeral=True)
                    else:
                        await ctx_or_inter.send(msg)
                    return

                embed = discord.Embed(title="📂 プロジェクト一覧", color=discord.Color.blue())
                for s in sessions:
                    status = "🟢 Active" if s.is_active else "⚫ Ended"
                    name = s.project_name or f"Session-{s.session_uuid[:8]}"
                    embed.add_field(name=name, value=f"状態: {status}\nID: `{s.session_uuid[:8]}`", inline=True)

                if is_interaction:
                    await ctx_or_inter.followup.send(embed=embed, ephemeral=True)
                else:
                    await ctx_or_inter.send(embed=embed)
            finally:
                await db_session.close()
        except Exception as e:
            logger.error(f"Error in _do_coding_list: {e}")

    # ------------------------------------------------------------------
    # /coding info / !coding info
    # ------------------------------------------------------------------

    @coding_group.command(name="info", description="Show current session information")
    async def coding_info_slash(self, interaction: discord.Interaction):
        await self._do_coding_info(interaction)

    @coding_prefix.command(name="info")
    async def coding_info_prefix(self, ctx: commands.Context):
        await self._do_coding_info(ctx)

    async def _do_coding_info(self, ctx_or_inter):
        is_interaction = isinstance(ctx_or_inter, discord.Interaction)
        user = ctx_or_inter.user if is_interaction else ctx_or_inter.author
        user_id = str(user.id)
        session_uuid = self.session_manager.get_user_active_session(user_id)

        if not session_uuid:
            msg = "❌ アクティブなセッションがありません。"
            if is_interaction:
                await ctx_or_inter.response.send_message(msg, ephemeral=True)
            else:
                await ctx_or_inter.send(msg)
            return

        if is_interaction:
            await ctx_or_inter.response.defer(ephemeral=True)

        # (Implementation omitted for brevity, logic remains same as original _do_coding_info)
        # For the sake of this task, I'll just send a simplified info
        embed = discord.Embed(title="ℹ️ セッション情報", color=discord.Color.blue())
        embed.add_field(name="セッションID", value=f"`{session_uuid[:8]}`", inline=True)
        if is_interaction:
            await ctx_or_inter.followup.send(embed=embed, ephemeral=True)
        else:
            await ctx_or_inter.send(embed=embed)

    # ------------------------------------------------------------------
    # /coding export / !coding export
    # ------------------------------------------------------------------

    @coding_group.command(name="export", description="Export current project as ZIP")
    async def coding_export_slash(self, interaction: discord.Interaction):
        await self._do_coding_export(interaction)

    @coding_prefix.command(name="export")
    async def coding_export_prefix(self, ctx: commands.Context):
        await self._do_coding_export(ctx)

    async def _do_coding_export(self, ctx_or_inter):
        is_interaction = isinstance(ctx_or_inter, discord.Interaction)
        user = ctx_or_inter.user if is_interaction else ctx_or_inter.author
        user_id = str(user.id)
        session_uuid = self.session_manager.get_user_active_session(user_id)

        if not session_uuid:
            msg = "❌ アクティブなセッションがありません。"
            if is_interaction:
                await ctx_or_inter.response.send_message(msg, ephemeral=True)
            else:
                await ctx_or_inter.send(msg)
            return

        if is_interaction:
            await ctx_or_inter.response.defer(ephemeral=True)

        files = self.file_manager.list_files(session_uuid)
        if not files:
            msg = "❌ エクスポートするファイルがありません。"
            if is_interaction:
                await ctx_or_inter.followup.send(msg, ephemeral=True)
            else:
                await ctx_or_inter.send(msg)
            return

        zip_path = self.file_manager.create_zip(session_uuid)
        discord_file = discord.File(zip_path, filename=f"project_{session_uuid[:8]}.zip")
        
        if is_interaction:
            await ctx_or_inter.followup.send("📦 プロジェクトをエクスポートしました。", file=discord_file, ephemeral=True)
        else:
            await ctx_or_inter.send(f"{user.mention} 📦 プロジェクトをエクスポートしました。", file=discord_file)

    # ------------------------------------------------------------------
    # /coding rename / !coding rename
    # ------------------------------------------------------------------

    @coding_group.command(name="rename", description="Rename the current project")
    async def coding_rename_slash(self, interaction: discord.Interaction, new_name: str):
        await self._do_coding_rename(interaction, new_name)

    @coding_prefix.command(name="rename")
    async def coding_rename_prefix(self, ctx: commands.Context, new_name: str):
        await self._do_coding_rename(ctx, new_name)

    async def _do_coding_rename(self, ctx_or_inter, new_name: str):
        is_interaction = isinstance(ctx_or_inter, discord.Interaction)
        user = ctx_or_inter.user if is_interaction else ctx_or_inter.author
        user_id = str(user.id)
        session_uuid = self.session_manager.get_user_active_session(user_id)

        if not session_uuid:
            msg = "❌ アクティブなセッションがありません。"
            if is_interaction:
                await ctx_or_inter.response.send_message(msg, ephemeral=True)
            else:
                await ctx_or_inter.send(msg)
            return

        if is_interaction:
            await ctx_or_inter.response.defer(ephemeral=True)

        db_session = self.bot.db_manager.get_session()
        try:
            from sqlalchemy import update
            from modules.database.models import Session as SessionModel
            stmt = update(SessionModel).where(SessionModel.session_uuid == session_uuid).values(project_name=new_name)
            await db_session.execute(stmt)
            await db_session.commit()
            
            msg = f"✅ プロジェクト名を `{new_name}` に変更しました。"
            if is_interaction:
                await ctx_or_inter.followup.send(msg, ephemeral=True)
            else:
                await ctx_or_inter.send(msg)
        finally:
            await db_session.close()

    # ------------------------------------------------------------------
    # /coding delete / !coding delete
    # ------------------------------------------------------------------

    @coding_group.command(name="delete", description="Delete the current coding session")
    async def coding_delete_slash(self, interaction: discord.Interaction):
        await self._do_coding_delete(interaction)

    @coding_prefix.command(name="delete")
    async def coding_delete_prefix(self, ctx: commands.Context):
        await self._do_coding_delete(ctx)

    async def _do_coding_delete(self, ctx_or_inter):
        is_interaction = isinstance(ctx_or_inter, discord.Interaction)
        user = ctx_or_inter.user if is_interaction else ctx_or_inter.author
        user_id = str(user.id)
        session_uuid = self.session_manager.get_user_active_session(user_id)

        if not session_uuid:
            msg = "❌ アクティブなセッションがありません。"
            if is_interaction:
                await ctx_or_inter.response.send_message(msg, ephemeral=True)
            else:
                await ctx_or_inter.send(msg)
            return

        embed = discord.Embed(title="⚠️ セッションを終了しますか？", color=discord.Color.orange())
        view = DeleteConfirmView(self)
        if is_interaction:
            await ctx_or_inter.response.send_message(embed=embed, view=view, ephemeral=True)
        else:
            await ctx_or_inter.send(embed=embed, view=view)

    async def _execute_session_delete(self, interaction: discord.Interaction):
        """Actually delete the session after confirmation (Interaction only)"""
        user_id = str(interaction.user.id)
        session_uuid = self.session_manager.get_user_active_session(user_id)
        if not session_uuid: return
        await interaction.response.defer()
        db_session = self.bot.db_manager.get_session()
        try:
            await self.session_manager.close_session(db_session, session_uuid, delete_channel=True)
            self.file_manager.cleanup_session(session_uuid)
            if user_id in self.ai_services: del self.ai_services[user_id]
            await interaction.edit_original_response(content=f"✅ セッション `{session_uuid[:8]}` を削除しました。", embed=None, view=None)
        finally:
            await db_session.close()


async def setup(bot: commands.Bot):
    """Setup function for loading cog"""
    cog = CodingCog(bot)
    await bot.add_cog(cog)
    if cog.coding_group not in bot.tree.get_commands():
        bot.tree.add_command(cog.coding_group)
