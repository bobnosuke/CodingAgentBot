"""
Coding commands for CoderAgent
Handles /coding start, chat, end, panel, list, info, export, rename, delete commands
"""
import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
from logger import setup_logger
from modules.security.permissions import PermissionLevel, PermissionManager
from modules.database.repository import UserRepository, APIKeyRepository, MessageRepository, SessionRepository
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

    coding_group = app_commands.Group(name="coding", description="AI coding commands")

    # ------------------------------------------------------------------
    # /coding start
    # ------------------------------------------------------------------

    @coding_group.command(name="start", description="Start a new coding session")
    async def coding_start(self, interaction: discord.Interaction, project_name: str = None):
        await self._do_coding_start(interaction, project_name)

    async def _do_coding_start(self, interaction: discord.Interaction, project_name: str = None):
        """Internal handler for starting a coding session"""
        try:
            user_id = str(interaction.user.id)
            active_session = self.session_manager.get_user_active_session(user_id)

            if active_session:
                await interaction.response.send_message(
                    f"❌ すでにアクティブなセッションがあります: `{active_session[:8]}`\n"
                    f"先に `/coding end` で終了してください。",
                    ephemeral=True
                )
                return

            await interaction.response.defer(ephemeral=True)

            db_session = self.bot.db_manager.get_session()
            try:
                user = await UserRepository.get_or_create_user(
                    db_session,
                    user_id,
                    interaction.user.name,
                    interaction.user.discriminator
                )

                api_key = await APIKeyRepository.get_active_api_key(db_session, user.id)
                if not api_key:
                    await interaction.followup.send(
                        "❌ OpenRouter APIキーが登録されていません。\n"
                        "`/api-key register` でAPIキーを登録してください。",
                        ephemeral=True
                    )
                    return

                decrypted_key = self.bot.encryption_manager.decrypt(api_key.encrypted_key)

                session_uuid, coding_room = await self.session_manager.create_session(
                    db_session,
                    interaction.user,
                    interaction.guild,
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
                embed.add_field(
                    name="次のステップ",
                    value="1. コーディングルームへ移動\n"
                          "2. `/coding chat` でAIと対話\n"
                          "3. 完了したら `/coding end` で終了",
                    inline=False
                )
                embed.set_footer(text="コーディングルームはあなた、Bot、管理者のみアクセス可能です")

                await interaction.followup.send(embed=embed, ephemeral=True)

                welcome_embed = discord.Embed(
                    title="🤖 コーディングセッションへようこそ",
                    description="AIコーディングアシスタントです。何を作りたいか教えてください！",
                    color=discord.Color.blue()
                )
                welcome_embed.add_field(
                    name="使用例",
                    value="• `/coding chat Discord Botを作って`\n"
                          "• `/coding chat ログイン機能を追加して`\n"
                          "• `/coding chat このコードを修正して: ...`\n"
                          "• `/coding chat デコレータの使い方を教えて`",
                    inline=False
                )
                welcome_embed.add_field(
                    name="ヒント",
                    value="• `/save` でコードを保存\n"
                          "• `/list` で保存済みファイルを確認\n"
                          "• `/coding export` で全ファイルをZIPダウンロード\n"
                          "• `/coding info` でセッション情報を確認",
                    inline=False
                )
                await coding_room.send(embed=welcome_embed)

                logger.info(f"Created session {session_uuid} for {interaction.user.name}")

            finally:
                await db_session.close()

        except Exception as e:
            logger.error(f"Error in _do_coding_start: {e}", exc_info=True)
            try:
                await interaction.followup.send(f"❌ セッション開始エラー: {str(e)}", ephemeral=True)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # /coding chat
    # ------------------------------------------------------------------

    @coding_group.command(name="chat", description="Chat with AI in your coding session")
    async def coding_chat(self, interaction: discord.Interaction, message: str):
        try:
            user_id = str(interaction.user.id)
            session_uuid = self.session_manager.get_user_active_session(user_id)

            if not session_uuid:
                await interaction.response.send_message(
                    "❌ アクティブなコーディングセッションがありません。`/coding start` で開始してください。",
                    ephemeral=True
                )
                return

            session_info = self.session_manager.get_session(session_uuid)
            if session_info and str(interaction.channel.id) != session_info["channel_id"]:
                await interaction.response.send_message(
                    "❌ このコマンドはコーディングルーム内でのみ使用できます！",
                    ephemeral=True
                )
                return

            if user_id not in self.ai_services:
                await interaction.response.send_message(
                    "❌ AIサービスが初期化されていません。新しいセッションを開始してください。",
                    ephemeral=True
                )
                return

            await interaction.response.defer()

            ai_service = self.ai_services[user_id]
            thinking_msg = await interaction.followup.send("🤔 考え中...")

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
                    if len(full_response) > 2000:
                        chunks = [full_response[i:i+2000] for i in range(0, len(full_response), 2000)]
                        await thinking_msg.edit(content=chunks[0])
                        for chunk in chunks[1:]:
                            await interaction.followup.send(chunk)
                    else:
                        await thinking_msg.edit(content=full_response)
                else:
                    await thinking_msg.edit(content="❌ レスポンスが生成されませんでした")

            except Exception as e:
                logger.error(f"Error generating response: {e}")
                await thinking_msg.edit(content=f"❌ エラー: {str(e)}")

        except Exception as e:
            logger.error(f"Error in coding_chat: {e}", exc_info=True)
            await interaction.response.send_message(f"❌ エラー: {str(e)}", ephemeral=True)

    # ------------------------------------------------------------------
    # /coding end
    # ------------------------------------------------------------------

    @coding_group.command(name="end", description="End your current coding session")
    async def coding_end(self, interaction: discord.Interaction):
        try:
            user_id = str(interaction.user.id)
            session_uuid = self.session_manager.get_user_active_session(user_id)

            if not session_uuid:
                await interaction.response.send_message(
                    "❌ アクティブなコーディングセッションがありません。",
                    ephemeral=True
                )
                return

            await interaction.response.defer(ephemeral=True)

            db_session = self.bot.db_manager.get_session()
            try:
                await self.session_manager.close_session(
                    db_session,
                    session_uuid,
                    delete_channel=True
                )

                if user_id in self.ai_services:
                    del self.ai_services[user_id]

                await interaction.followup.send(
                    f"✅ セッション `{session_uuid[:8]}` を終了しました。\n"
                    f"コーディングルームを削除しました。",
                    ephemeral=True
                )
                logger.info(f"Closed session {session_uuid} for {interaction.user.name}")

            finally:
                await db_session.close()

        except Exception as e:
            logger.error(f"Error in coding_end: {e}", exc_info=True)
            await interaction.response.send_message(
                f"❌ セッション終了エラー: {str(e)}",
                ephemeral=True
            )

    # ------------------------------------------------------------------
    # /coding panel
    # ------------------------------------------------------------------

    @coding_group.command(name="panel", description="Show the CoderAgent operation panel")
    async def coding_panel(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🤖 CoderAgent パネル",
            description=(
                "CoderAgent へようこそ！\n"
                "下のメニューから操作を選択してください。"
            ),
            color=discord.Color.blurple()
        )
        embed.add_field(
            name="主な機能",
            value=(
                "🚀 **Coding Start** — 新しいセッションを開始\n"
                "📂 **Project List** — プロジェクト一覧を表示\n"
                "ℹ️ **Session Info** — 現在のセッション情報\n"
                "📦 **Export Project** — ZIPでエクスポート\n"
                "✏️ **Rename Project** — プロジェクト名を変更\n"
                "🗑️ **Delete Session** — セッションを終了・削除"
            ),
            inline=False
        )
        embed.add_field(
            name="注意事項",
            value=(
                "• セッション開始には OpenRouter APIキーの登録が必要です\n"
                "• `/api-key register` でAPIキーを登録してください\n"
                "• 各操作はコーディングルーム内でも直接コマンドで実行できます"
            ),
            inline=False
        )
        embed.set_footer(text="CoderAgent — AI-powered coding on Discord")

        view = CodingPanelView()
        await interaction.response.send_message(embed=embed, view=view)

    # ------------------------------------------------------------------
    # /coding list
    # ------------------------------------------------------------------

    @coding_group.command(name="list", description="Show your current and past projects")
    async def coding_list(self, interaction: discord.Interaction):
        await self._do_coding_list(interaction)

    async def _do_coding_list(self, interaction: discord.Interaction):
        """Internal handler for listing projects"""
        try:
            user_id = str(interaction.user.id)

            # Respond or defer depending on whether already responded
            responded = interaction.response.is_done()
            if not responded:
                await interaction.response.defer(ephemeral=True)

            db_session = self.bot.db_manager.get_session()
            try:
                user = await UserRepository.get_user_by_discord_id(db_session, user_id)
                if not user:
                    await interaction.followup.send(
                        "❌ ユーザー情報が見つかりません。まず `/coding start` を実行してください。",
                        ephemeral=True
                    )
                    return

                # Get all sessions for this user
                from sqlalchemy import select
                from modules.database.models import Session as SessionModel
                stmt = (
                    select(SessionModel)
                    .where(SessionModel.user_id == user.id)
                    .order_by(SessionModel.created_at.desc())
                    .limit(10)
                )
                result = await db_session.execute(stmt)
                sessions = result.scalars().all()

                if not sessions:
                    await interaction.followup.send(
                        "📂 プロジェクトがまだありません。`/coding start` でセッションを開始してください。",
                        ephemeral=True
                    )
                    return

                embed = discord.Embed(
                    title="📂 プロジェクト一覧",
                    description=f"直近 {len(sessions)} 件のプロジェクトを表示しています。",
                    color=discord.Color.blue()
                )

                for s in sessions:
                    status = "🟢 Active" if s.is_active else "⚫ Ended"
                    created = s.created_at.strftime("%Y/%m/%d %H:%M") if s.created_at else "不明"
                    model = s.ai_model or "デフォルト"
                    name = s.project_name or f"Session-{s.session_uuid[:8]}"

                    # Count files
                    file_count = len(self.file_manager.list_files(s.session_uuid))

                    embed.add_field(
                        name=f"{name}",
                        value=(
                            f"状態: {status}\n"
                            f"作成: {created}\n"
                            f"モデル: `{model}`\n"
                            f"ファイル数: {file_count}"
                        ),
                        inline=True
                    )

                await interaction.followup.send(embed=embed, ephemeral=True)

            finally:
                await db_session.close()

        except Exception as e:
            logger.error(f"Error in _do_coding_list: {e}", exc_info=True)
            await interaction.followup.send(f"❌ エラー: {str(e)}", ephemeral=True)

    # ------------------------------------------------------------------
    # /coding info
    # ------------------------------------------------------------------

    @coding_group.command(name="info", description="Show current session information")
    async def coding_info(self, interaction: discord.Interaction):
        await self._do_coding_info(interaction)

    async def _do_coding_info(self, interaction: discord.Interaction):
        """Internal handler for session info"""
        try:
            user_id = str(interaction.user.id)
            session_uuid = self.session_manager.get_user_active_session(user_id)

            responded = interaction.response.is_done()
            if not responded:
                await interaction.response.defer(ephemeral=True)

            if not session_uuid:
                await interaction.followup.send(
                    "❌ アクティブなセッションがありません。`/coding start` で開始してください。",
                    ephemeral=True
                )
                return

            session_info = self.session_manager.get_session(session_uuid)
            if not session_info:
                await interaction.followup.send("❌ セッション情報が取得できませんでした。", ephemeral=True)
                return

            db_session = self.bot.db_manager.get_session()
            try:
                from sqlalchemy import select
                from modules.database.models import Session as SessionModel, Message
                stmt = select(SessionModel).where(SessionModel.session_uuid == session_uuid)
                result = await db_session.execute(stmt)
                db_sess = result.scalar_one_or_none()

                # Count messages
                msg_stmt = select(Message).where(Message.session_id == db_sess.id) if db_sess else None
                msg_count = 0
                if msg_stmt is not None:
                    msg_result = await db_session.execute(msg_stmt)
                    msg_count = len(msg_result.scalars().all())

                # Count files
                file_count = len(self.file_manager.list_files(session_uuid))
                session_size = self.file_manager.get_session_size(session_uuid)

                created_at = session_info.get("created_at")
                if isinstance(created_at, datetime):
                    created_str = created_at.strftime("%Y/%m/%d %H:%M:%S")
                    elapsed = datetime.utcnow() - created_at
                    hours, rem = divmod(int(elapsed.total_seconds()), 3600)
                    minutes = rem // 60
                    elapsed_str = f"{hours}時間 {minutes}分"
                else:
                    created_str = "不明"
                    elapsed_str = "不明"

                project_name = db_sess.project_name if db_sess else None
                ai_model = db_sess.ai_model if db_sess else "デフォルト"
                channel_id = session_info.get("channel_id")

                embed = discord.Embed(
                    title="ℹ️ セッション情報",
                    color=discord.Color.blue()
                )
                embed.add_field(name="セッションID", value=f"`{session_uuid[:8]}`", inline=True)
                embed.add_field(name="プロジェクト名", value=project_name or "未設定", inline=True)
                embed.add_field(name="使用モデル", value=f"`{ai_model}`", inline=True)
                embed.add_field(name="開始日時", value=created_str, inline=True)
                embed.add_field(name="経過時間", value=elapsed_str, inline=True)
                embed.add_field(name="チャンネル", value=f"<#{channel_id}>" if channel_id else "不明", inline=True)
                embed.add_field(name="メッセージ数", value=str(msg_count), inline=True)
                embed.add_field(name="ファイル数", value=str(file_count), inline=True)
                embed.add_field(
                    name="使用容量",
                    value=f"{session_size / 1024:.1f} KB" if session_size > 0 else "0 KB",
                    inline=True
                )

                await interaction.followup.send(embed=embed, ephemeral=True)

            finally:
                await db_session.close()

        except Exception as e:
            logger.error(f"Error in _do_coding_info: {e}", exc_info=True)
            await interaction.followup.send(f"❌ エラー: {str(e)}", ephemeral=True)

    # ------------------------------------------------------------------
    # /coding export
    # ------------------------------------------------------------------

    @coding_group.command(name="export", description="Export current project as ZIP")
    async def coding_export(self, interaction: discord.Interaction):
        await self._do_coding_export(interaction)

    async def _do_coding_export(self, interaction: discord.Interaction):
        """Internal handler for exporting project"""
        try:
            user_id = str(interaction.user.id)
            session_uuid = self.session_manager.get_user_active_session(user_id)

            responded = interaction.response.is_done()
            if not responded:
                await interaction.response.defer(ephemeral=True)

            if not session_uuid:
                await interaction.followup.send(
                    "❌ アクティブなセッションがありません。`/coding start` で開始してください。",
                    ephemeral=True
                )
                return

            files = self.file_manager.list_files(session_uuid)
            if not files:
                await interaction.followup.send(
                    "❌ エクスポートするファイルがありません。`/save` でファイルを保存してください。",
                    ephemeral=True
                )
                return

            zip_path = self.file_manager.create_zip(session_uuid)
            zip_size = zip_path.stat().st_size

            if zip_size > 25 * 1024 * 1024:
                await interaction.followup.send(
                    f"❌ ZIPファイルが大きすぎます ({zip_size / 1024 / 1024:.1f}MB)。"
                    f"Discordの上限は25MBです。",
                    ephemeral=True
                )
                return

            db_session = self.bot.db_manager.get_session()
            try:
                from sqlalchemy import select
                from modules.database.models import Session as SessionModel
                stmt = select(SessionModel).where(SessionModel.session_uuid == session_uuid)
                result = await db_session.execute(stmt)
                db_sess = result.scalar_one_or_none()
                project_name = (db_sess.project_name if db_sess else None) or session_uuid[:8]
            finally:
                await db_session.close()

            safe_name = project_name.replace(" ", "_").replace("/", "_")
            discord_file = discord.File(zip_path, filename=f"{safe_name}.zip")

            embed = discord.Embed(
                title="📦 エクスポート完了",
                description="プロジェクトファイルをZIPにまとめました。",
                color=discord.Color.green()
            )
            embed.add_field(name="プロジェクト名", value=project_name, inline=True)
            embed.add_field(name="ファイル数", value=str(len(files)), inline=True)
            embed.add_field(name="ZIPサイズ", value=f"{zip_size / 1024:.1f} KB", inline=True)

            await interaction.followup.send(embed=embed, file=discord_file, ephemeral=True)
            logger.info(f"User {user_id} exported session {session_uuid}")

        except Exception as e:
            logger.error(f"Error in _do_coding_export: {e}", exc_info=True)
            await interaction.followup.send(f"❌ エクスポートエラー: {str(e)}", ephemeral=True)

    # ------------------------------------------------------------------
    # /coding rename
    # ------------------------------------------------------------------

    @coding_group.command(name="rename", description="Rename the current project")
    async def coding_rename(self, interaction: discord.Interaction, new_name: str):
        await self._do_coding_rename(interaction, new_name)

    async def _do_coding_rename(self, interaction: discord.Interaction, new_name: str):
        """Internal handler for renaming a project"""
        try:
            user_id = str(interaction.user.id)
            session_uuid = self.session_manager.get_user_active_session(user_id)

            responded = interaction.response.is_done()
            if not responded:
                await interaction.response.defer(ephemeral=True)

            if not session_uuid:
                await interaction.followup.send(
                    "❌ アクティブなセッションがありません。`/coding start` で開始してください。",
                    ephemeral=True
                )
                return

            new_name = new_name.strip()
            if not new_name:
                await interaction.followup.send("❌ プロジェクト名を入力してください。", ephemeral=True)
                return

            db_session = self.bot.db_manager.get_session()
            try:
                from sqlalchemy import update
                from modules.database.models import Session as SessionModel
                stmt = (
                    update(SessionModel)
                    .where(SessionModel.session_uuid == session_uuid)
                    .values(project_name=new_name)
                )
                await db_session.execute(stmt)
                await db_session.commit()

                # Also rename the Discord channel
                session_info = self.session_manager.get_session(session_uuid)
                if session_info:
                    channel = self.bot.get_channel(int(session_info["channel_id"]))
                    if channel:
                        safe_channel_name = new_name.lower().replace(" ", "-")[:100]
                        try:
                            await channel.edit(name=safe_channel_name)
                        except discord.Forbidden:
                            pass  # Bot may not have permission; non-fatal

                embed = discord.Embed(
                    title="✏️ プロジェクト名を変更しました",
                    color=discord.Color.green()
                )
                embed.add_field(name="新しいプロジェクト名", value=new_name, inline=False)

                await interaction.followup.send(embed=embed, ephemeral=True)
                logger.info(f"User {user_id} renamed session {session_uuid} to '{new_name}'")

            finally:
                await db_session.close()

        except Exception as e:
            logger.error(f"Error in _do_coding_rename: {e}", exc_info=True)
            await interaction.followup.send(f"❌ リネームエラー: {str(e)}", ephemeral=True)

    # ------------------------------------------------------------------
    # /coding delete
    # ------------------------------------------------------------------

    @coding_group.command(name="delete", description="Delete the current coding session")
    async def coding_delete(self, interaction: discord.Interaction):
        await self._do_coding_delete(interaction)

    async def _do_coding_delete(self, interaction: discord.Interaction):
        """Internal handler for deleting a session (shows confirmation)"""
        try:
            user_id = str(interaction.user.id)
            session_uuid = self.session_manager.get_user_active_session(user_id)

            responded = interaction.response.is_done()

            if not session_uuid:
                msg = "❌ アクティブなセッションがありません。"
                if responded:
                    await interaction.followup.send(msg, ephemeral=True)
                else:
                    await interaction.response.send_message(msg, ephemeral=True)
                return

            session_info = self.session_manager.get_session(session_uuid)
            project_name = "不明"
            if session_info:
                db_session = self.bot.db_manager.get_session()
                try:
                    from sqlalchemy import select
                    from modules.database.models import Session as SessionModel
                    stmt = select(SessionModel).where(SessionModel.session_uuid == session_uuid)
                    result = await db_session.execute(stmt)
                    db_sess = result.scalar_one_or_none()
                    if db_sess and db_sess.project_name:
                        project_name = db_sess.project_name
                finally:
                    await db_session.close()

            embed = discord.Embed(
                title="⚠️ セッションを終了しますか？",
                description=(
                    f"プロジェクト **{project_name}** (`{session_uuid[:8]}`) を終了します。\n\n"
                    "この操作を実行すると：\n"
                    "• コーディングルームが削除されます\n"
                    "• セッションキャッシュが削除されます\n"
                    "• 一時ファイルが削除されます\n\n"
                    "⚠️ APIキーは削除されません。"
                ),
                color=discord.Color.orange()
            )

            view = DeleteConfirmView(self)

            if responded:
                await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            else:
                await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

        except Exception as e:
            logger.error(f"Error in _do_coding_delete: {e}", exc_info=True)
            try:
                await interaction.followup.send(f"❌ エラー: {str(e)}", ephemeral=True)
            except Exception:
                pass

    async def _execute_session_delete(self, interaction: discord.Interaction):
        """Actually delete the session after confirmation"""
        try:
            user_id = str(interaction.user.id)
            session_uuid = self.session_manager.get_user_active_session(user_id)

            if not session_uuid:
                await interaction.response.edit_message(
                    content="❌ セッションが見つかりませんでした。",
                    embed=None,
                    view=None
                )
                return

            await interaction.response.defer()

            db_session = self.bot.db_manager.get_session()
            try:
                await self.session_manager.close_session(
                    db_session,
                    session_uuid,
                    delete_channel=True
                )

                # Clean up local files
                self.file_manager.cleanup_session(session_uuid)

                if user_id in self.ai_services:
                    del self.ai_services[user_id]

                await interaction.edit_original_response(
                    content=f"✅ セッション `{session_uuid[:8]}` を削除しました。",
                    embed=None,
                    view=None
                )
                logger.info(f"Deleted session {session_uuid} for {interaction.user.name}")

            finally:
                await db_session.close()

        except Exception as e:
            logger.error(f"Error in _execute_session_delete: {e}", exc_info=True)
            try:
                await interaction.edit_original_response(
                    content=f"❌ 削除エラー: {str(e)}",
                    embed=None,
                    view=None
                )
            except Exception:
                pass


async def setup(bot: commands.Bot):
    """Setup function for loading cog"""
    cog = CodingCog(bot)
    await bot.add_cog(cog)
    if cog.coding_group not in bot.tree.get_commands():
        bot.tree.add_command(cog.coding_group)
