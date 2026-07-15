"""
Coding commands for CoderAgent
Handles /coding start, /coding end commands and AI chat in CodingRooms
"""
import discord
from discord.ext import commands
from discord import app_commands
from logger import setup_logger
from modules.security.permissions import PermissionLevel, PermissionManager
from modules.database.repository import UserRepository, APIKeyRepository, MessageRepository, SessionRepository
from modules.session.manager import SessionManager
from modules.ai.openrouter import OpenRouterClient, AIService
import asyncio

logger = setup_logger(__name__)


class CodingPanelView(discord.ui.View):
    """Persistent View for /coding panel (Public Panel)"""
    
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.bot = bot
        self.session_manager = SessionManager(bot)
    
    @discord.ui.select(
        placeholder="🎯 操作を選択してください",
        options=[
            discord.SelectOption(label="開発開始", value="start", emoji="🚀", description="新しいコーディングセッションを開始します"),
            discord.SelectOption(label="プロジェクト一覧", value="list", emoji="📋", description="あなたのプロジェクト一覧を表示します"),
            discord.SelectOption(label="プロジェクト詳細", value="info", emoji="ℹ️", description="プロジェクトの詳細情報を確認します"),
            discord.SelectOption(label="プロジェクト名変更", value="rename", emoji="✏️", description="プロジェクト名を変更します"),
        ],
        custom_id="persistent:coding_panel_select"
    )
    async def panel_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        """Handle selection from Public Panel"""
        await interaction.response.defer(ephemeral=True)
        
        action = select.values[0]
        if action == "start":
            await self._handle_start(interaction)
        elif action == "list":
            await self._handle_list(interaction)
        elif action == "info":
            await self._handle_info(interaction)
        elif action == "rename":
            await self._handle_rename(interaction)
    
    async def _handle_start(self, interaction: discord.Interaction):
        """Handle start (New Ephemeral)"""
        user_id = str(interaction.user.id)
        active_session = self.session_manager.get_user_active_session(user_id)
        
        if active_session:
            await interaction.followup.send(
                f"❌ すでにアクティブなセッションがあります: `{active_session[:8]}`\n"
                f"新しく開始する前に `/coding end` で終了してください。",
                ephemeral=True
            )
            return
        
        db_session = self.bot.db_manager.get_session()
        try:
            user = await UserRepository.get_or_create_user(db_session, user_id, interaction.user.name, interaction.user.discriminator)
            api_key = await APIKeyRepository.get_active_api_key(db_session, user.id)
            
            if not api_key:
                await interaction.followup.send(
                    "❌ OpenRouterのAPIキーが見つかりません！\n先に `/setting` からAPIキーを登録してください。",
                    ephemeral=True
                )
                return
            
            # セッションIDを生成
            import uuid
            short_uuid = str(uuid.uuid4())[:8]
            channel_name = f"session-{short_uuid}"
            
            session_uuid, coding_room = await self.session_manager.create_session(
                db_session, 
                interaction.user, 
                interaction.guild, 
                channel_name
            )
            
            embed = discord.Embed(
                title="✅ コーディングセッション開始",
                description=f"あなた専用のコーディングルームを作成しました！",
                color=discord.Color.green()
            )
            embed.add_field(name="セッションID", value=f"`{session_uuid[:8]}`", inline=False)
            embed.add_field(name="チャンネル", value=coding_room.mention, inline=False)
            embed.set_footer(text="Made by RovaexTeam")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            # Coding Room welcome
            welcome_embed = discord.Embed(
                title="🤖 コーディングセッションへようこそ",
                description="私はあなたのAIコーディングアシスタントです。何を作りたいか教えてください！",
                color=discord.Color.blue()
            )
            welcome_embed.add_field(name="ヒント", value="・作りたい機能や修正したいコードをチャットしてください。\n・`!download` で作成したファイルをダウンロードできます。\n・`/coding end` でセッションを終了できます。", inline=False)
            welcome_embed.set_footer(text="Made by RovaexTeam")
            await coding_room.send(embed=welcome_embed)
        except Exception as e:
            logger.error(f"Error in _handle_start: {e}", exc_info=True)
            await interaction.followup.send(f"❌ セッション開始中にエラーが発生しました: {str(e)}", ephemeral=True)
        finally:
            await db_session.close()
    
    async def _handle_list(self, interaction: discord.Interaction):
        await interaction.followup.send("📋 **プロジェクト一覧機能は準備中です。**", ephemeral=True)
    
    async def _handle_info(self, interaction: discord.Interaction):
        await interaction.followup.send("ℹ️ **プロジェクト詳細機能は準備中です。**", ephemeral=True)
    
    async def _handle_rename(self, interaction: discord.Interaction):
        await interaction.followup.send("✏️ **プロジェクト名変更機能は準備中です。**", ephemeral=True)


class CodingCog(commands.Cog):
    """Cog for coding-related commands"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.session_manager = SessionManager(bot)
    
    coding_group = app_commands.Group(name="coding", description="AIコーディング関連のコマンド")
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Handle AI chat in CodingRooms"""
        # Ignore bot messages
        if message.author.bot:
            return
        
        # Check if message is in a CodingRoom
        channel_id = str(message.channel.id)
        
        # 1. Try to get from cache
        session_uuid = None
        for uuid, info in self.session_manager.active_sessions.items():
            if info["channel_id"] == channel_id:
                session_uuid = uuid
                break
        
        # 2. If not in cache, try to restore from DB
        if not session_uuid:
            db_session = self.bot.db_manager.get_session()
            try:
                from sqlalchemy import select
                from modules.database.models import Session
                stmt = select(Session).where((Session.channel_id == channel_id) & (Session.is_active == True))
                result = await db_session.execute(stmt)
                db_session_obj = result.scalar_one_or_none()
                
                if db_session_obj:
                    # Restore to cache
                    session_uuid = db_session_obj.session_uuid
                    self.session_manager.active_sessions[session_uuid] = {
                        "user_id": db_session_obj.user_id,
                        "discord_user_id": str(message.author.id), # Assuming the author is the session owner for now
                        "guild_id": str(message.guild.id),
                        "channel_id": channel_id,
                        "db_session_id": db_session_obj.id
                    }
                    logger.info(f"Restored session {session_uuid} from DB for channel {channel_id}")
            except Exception as e:
                logger.error(f"Error restoring session from DB: {e}")
            finally:
                await db_session.close()

        if not session_uuid:
            return

        # Check if it's a prefix command
        if message.content.startswith(self.bot.command_prefix):
            # Let the bot process commands
            return

        # Process AI Chat
        async with message.channel.typing():
            db_session = self.bot.db_manager.get_session()
            try:
                session_info = self.session_manager.active_sessions[session_uuid]
                user = await UserRepository.get_user_by_discord_id(db_session, str(message.author.id))
                api_key = await APIKeyRepository.get_active_api_key(db_session, user.id)
                
                if not api_key:
                    await message.reply("❌ APIキーが設定されていません。`/setting` で設定してください。")
                    return
                
                decrypted_key = self.bot.encryption_manager.decrypt(api_key.encrypted_key)
                
                # Get conversation history
                history = await MessageRepository.get_session_messages(db_session, session_info["db_session_id"])
                formatted_history = [{"role": m.role, "content": m.content} for m in history[-10:]] # Last 10 messages
                
                # Initialize AI service
                client = OpenRouterClient(decrypted_key)
                ai_service = AIService(client)
                ai_service.set_model_by_preset(getattr(user, "model_preset", "balance"))
                
                # Save user message
                await MessageRepository.add_message(db_session, session_info["db_session_id"], "user", message.content)
                
                # Send initial response message
                response_msg = await message.reply("🤔 思考中...")
                
                full_response = ""
                chunk_counter = 0
                
                async for chunk in ai_service.chat(message.content, formatted_history):
                    full_response += chunk
                    chunk_counter += 1
                    
                    # Update message every 10 chunks to avoid rate limit
                    if chunk_counter % 15 == 0:
                        await response_msg.edit(content=full_response + " ▌")
                
                # Final edit
                if full_response:
                    await response_msg.edit(content=full_response)
                    # Save AI response
                    await MessageRepository.add_message(db_session, session_info["db_session_id"], "assistant", full_response)
                else:
                    await response_msg.edit(content="⚠️ AIからの応答が空でした。もう一度お試しください。")
                
                await db_session.commit()
            except Exception as e:
                logger.error(f"Error in AI chat: {e}", exc_info=True)
                await message.reply(f"❌ エラーが発生しました: {str(e)}")
            finally:
                await db_session.close()

    @coding_group.command(name="panel", description="コーディング管理パネルを表示します")
    @PermissionManager.has_permission(PermissionLevel.ADMIN)
    async def coding_panel(self, interaction: discord.Interaction):
        """Show Public Panel"""
        embed = discord.Embed(
            title="🎮 コーディング管理パネル",
            description="以下のメニューから操作を選択してください。",
            color=discord.Color.blue()
        )
        embed.set_footer(text="Made by RovaexTeam")
        view = CodingPanelView(self.bot)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=False)
    
    @coding_group.command(name="start", description="新しいコーディングセッションを開始します")
    async def coding_start(self, interaction: discord.Interaction, project_name: str = None):
        """Start Session (New Ephemeral)"""
        user_id = str(interaction.user.id)
        active_session = self.session_manager.get_user_active_session(user_id)
        
        if active_session:
            await interaction.response.send_message(f"❌ すでにアクティブなセッションがあります: `{active_session[:8]}`", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        db_session = self.bot.db_manager.get_session()
        try:
            user = await UserRepository.get_or_create_user(db_session, user_id, interaction.user.name, interaction.user.discriminator)
            api_key = await APIKeyRepository.get_active_api_key(db_session, user.id)
            
            if not api_key:
                await interaction.followup.send("❌ OpenRouterのAPIキーが見つかりません！", ephemeral=True)
                return
            
            import uuid
            short_uuid = str(uuid.uuid4())[:8]
            channel_name = project_name or f"session-{short_uuid}"
            
            session_uuid, coding_room = await self.session_manager.create_session(
                db_session, 
                interaction.user, 
                interaction.guild, 
                channel_name
            )
            
            embed = discord.Embed(
                title="✅ コーディングセッション開始",
                description=f"あなた専用のコーディングルームを作成しました！",
                color=discord.Color.green()
            )
            embed.add_field(name="チャンネル", value=coding_room.mention, inline=False)
            embed.set_footer(text="Made by RovaexTeam")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            # Coding Room welcome
            welcome_embed = discord.Embed(
                title="🤖 コーディングセッションへようこそ",
                description="私はあなたのAIコーディングアシスタントです。何を作りたいか教えてください！",
                color=discord.Color.blue()
            )
            welcome_embed.set_footer(text="Made by RovaexTeam")
            await coding_room.send(embed=welcome_embed)
        finally:
            await db_session.close()

    @coding_group.command(name="end", description="現在のコーディングセッションを終了します")
    async def coding_end(self, interaction: discord.Interaction):
        """End Session (New Ephemeral Confirmation)"""
        user_id = str(interaction.user.id)
        session_uuid = self.session_manager.get_user_active_session(user_id)
        
        if not session_uuid:
            await interaction.response.send_message("❌ アクティブなセッションが見つかりません。", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="⚠️ セッション終了確認",
            description="本当にセッションを終了しますか？\n終了するとこのチャンネルは削除されます。",
            color=discord.Color.red()
        )
        embed.set_footer(text="Made by RovaexTeam")
        
        class ConfirmView(discord.ui.View):
            def __init__(self, session_manager, session_uuid, user_id):
                super().__init__(timeout=60)
                self.session_manager = session_manager
                self.session_uuid = session_uuid
                self.user_id = user_id
            
            @discord.ui.button(label="はい", style=discord.ButtonStyle.danger, emoji="✅")
            async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                if str(interaction.user.id) != self.user_id:
                    await interaction.response.send_message("この操作は実行者本人のみ可能です。", ephemeral=True)
                    return
                
                # データベースセッションを取得して終了処理
                db_session = self.session_manager.bot.db_manager.get_session()
                try:
                    await self.session_manager.close_session(db_session, self.session_uuid)
                    await db_session.commit()
                finally:
                    await db_session.close()
                
                await interaction.response.edit_message(content="✅ セッションを終了しました。", embed=None, view=None)
            
            @discord.ui.button(label="いいえ", style=discord.ButtonStyle.secondary, emoji="❌")
            async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                if str(interaction.user.id) != self.user_id:
                    await interaction.response.send_message("この操作は実行者本人のみ可能です。", ephemeral=True)
                    return
                
                await interaction.response.edit_message(content="セッションの終了をキャンセルしました。", embed=None, view=None)
        
        view = ConfirmView(self.session_manager, session_uuid, user_id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def setup(bot: commands.Bot):
    """Setup the cog"""
    cog = CodingCog(bot)
    await bot.add_cog(cog)
