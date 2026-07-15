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

logger = setup_logger(__name__)


class CodingPanelView(discord.ui.View):
    """View for /coding panel with Select Menu and Buttons"""
    
    def __init__(self, bot: commands.Bot, user_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.user_id = user_id
        self.session_manager = SessionManager(bot)
    
    @discord.ui.select(
        placeholder="🎯 操作を選択してください",
        options=[
            discord.SelectOption(
                label="開発開始",
                value="start",
                emoji="🚀",
                description="新しいコーディングセッションを開始します"
            ),
            discord.SelectOption(
                label="プロジェクト一覧",
                value="list",
                emoji="📋",
                description="あなたのプロジェクト一覧を表示します"
            ),
            discord.SelectOption(
                label="プロジェクト詳細",
                value="info",
                emoji="ℹ️",
                description="プロジェクトの詳細情報を確認します"
            ),
            discord.SelectOption(
                label="プロジェクト名変更",
                value="rename",
                emoji="✏️",
                description="プロジェクト名を変更します"
            ),
        ]
    )
    async def panel_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        """Handle panel selection"""
        # ここでの操作は「最初のephemeral」を送信するためのもの
        # ただし、すでにephemeralが送信されている場合はそれを更新したいが、
        # /coding panel 自体は公開メッセージなので、そこからの最初の応答は send_message になる
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
        """Handle start action"""
        user_id = str(interaction.user.id)
        
        # Check if user already has active session
        active_session = self.session_manager.get_user_active_session(user_id)
        
        if active_session:
            await interaction.followup.send(
                f"❌ You already have an active session: `{active_session[:8]}`\n"
                f"Use `/coding end` to close it first.",
                ephemeral=True
            )
            return
        
        # Get database session
        db_session = self.bot.db_manager.get_session()
        
        try:
            # Get or create user
            user = await UserRepository.get_or_create_user(
                db_session,
                user_id,
                interaction.user.name,
                interaction.user.discriminator
            )
            
            # Check if user has API key
            api_key = await APIKeyRepository.get_active_api_key(db_session, user.id)
            
            if not api_key:
                await interaction.followup.send(
                    "❌ No OpenRouter API key found!\n"
                    "Please register your API key first using `/setting`",
                    ephemeral=True
                )
                return
            
            # Decrypt API key
            decrypted_key = self.bot.encryption_manager.decrypt(api_key.encrypted_key)
            
            # Create session and CodingRoom
            session_uuid, coding_room = await self.session_manager.create_session(
                db_session,
                interaction.user,
                interaction.guild,
                "New Project"
            )
            
            # Initialize AI service for this user
            model_preset = getattr(user, "model_preset", "balance")
            
            openrouter_client = OpenRouterClient(decrypted_key)
            ai_service = AIService(openrouter_client)
            ai_service.set_model_by_preset(model_preset)
            
            # Send success message
            embed = discord.Embed(
                title="✅ Coding Session Started",
                description=f"Your private coding room has been created!",
                color=discord.Color.green()
            )
            embed.add_field(name="Session ID", value=f"`{session_uuid[:8]}`", inline=False)
            embed.add_field(name="Channel", value=coding_room.mention, inline=False)
            embed.add_field(
                name="Next Steps",
                value="1. Go to your coding room\n"
                      "2. Just type your message to chat with AI\n"
                      "3. Use `/coding end` when done",
                inline=False
            )
            embed.set_footer(text="Made by RovaexTeam")
            
            # セッション開始成功時は、ユーザーへの通知として新規ephemeralを送信
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            # Send welcome message in coding room
            welcome_embed = discord.Embed(
                title="🤖 Welcome to your Coding Session",
                description="I'm your AI coding assistant. Tell me what you'd like to build!",
                color=discord.Color.blue()
            )
            welcome_embed.add_field(
                name="Examples",
                value="• `Create a Discord bot`\n"
                      "• `Add login functionality`\n"
                      "• `Fix this code: ...`\n"
                      "• `Explain how decorators work`",
                inline=False
            )
            welcome_embed.add_field(
                name="Tips",
                value="• Use `!list` to see all saved files\n"
                      "• Use `!get <filename>` to view file content\n"
                      "• Use `!download` to download all files as ZIP",
                inline=False
            )
            welcome_embed.set_footer(text="Made by RovaexTeam")
            
            await coding_room.send(embed=welcome_embed)
            
            logger.info(f"Created session {session_uuid} for {interaction.user.name}")
        
        except Exception as e:
            logger.error(f"Error in _handle_start: {e}", exc_info=True)
            await interaction.followup.send(
                f"❌ Error starting session: {str(e)}",
                ephemeral=True
            )
        finally:
            await db_session.close()
    
    async def _handle_list(self, interaction: discord.Interaction):
        """Handle list action"""
        # パネルからの操作なので、最初のephemeralとして新規送信
        await interaction.followup.send(
            "📋 **プロジェクト一覧機能は準備中です。**\n"
            "現在のセッションで作成されたプロジェクトは、`/coding end` で確認できます。",
            ephemeral=True
        )
    
    async def _handle_info(self, interaction: discord.Interaction):
        """Handle info action"""
        await interaction.followup.send(
            "ℹ️ **プロジェクト詳細機能は準備中です。**\n"
            "プロジェクトの詳細情報は、`!readme` コマンドで確認できます。",
            ephemeral=True
        )
    
    async def _handle_rename(self, interaction: discord.Interaction):
        """Handle rename action"""
        await interaction.followup.send(
            "✏️ **プロジェクト名変更機能は準備中です。**\n"
            "セッション開始時に `project_name` パラメータを指定することで、プロジェクト名を設定できます。",
            ephemeral=True
        )


class CodingCog(commands.Cog):
    """Cog for coding-related commands"""
    
    def __init__(self, bot: commands.Bot):
        """
        Initialize coding cog
        
        Args:
            bot: Discord bot instance
        """
        self.bot = bot
        self.session_manager = SessionManager(bot)
        self.ai_services = {}  # Cache for AI services per user
    
    coding_group = app_commands.Group(name="coding", description="AI coding commands")
    
    @coding_group.command(name="panel", description="コーディング管理パネルを表示します")
    @PermissionManager.has_permission(PermissionLevel.ADMIN)
    async def coding_panel(self, interaction: discord.Interaction):
        """
        コーディング管理パネルを表示します
        
        Args:
            interaction: Discord interaction
        """
        try:
            embed = discord.Embed(
                title="🎮 コーディング管理パネル",
                description="以下のメニューから操作を選択してください。",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="🚀 開発開始",
                value="新しいコーディングセッションを開始します",
                inline=False
            )
            embed.add_field(
                name="📋 プロジェクト一覧",
                value="あなたのプロジェクト一覧を表示します",
                inline=False
            )
            embed.add_field(
                name="ℹ️ プロジェクト詳細",
                value="プロジェクトの詳細情報を確認します",
                inline=False
            )
            embed.add_field(
                name="✏️ プロジェクト名変更",
                value="プロジェクト名を変更します",
                inline=False
            )
            embed.set_footer(text="Made by RovaexTeam")
            
            view = CodingPanelView(self.bot, interaction.user.id)
            
            # 公開メッセージとして送信
            await interaction.response.send_message(embed=embed, view=view, ephemeral=False)
        
        except Exception as e:
            logger.error(f"Error in coding_panel: {e}", exc_info=True)
            await interaction.response.send_message(
                f"❌ Error: {str(e)}",
                ephemeral=True
            )
    
    @coding_group.command(name="start", description="新しいコーディングセッションを開始します")
    async def coding_start(self, interaction: discord.Interaction, project_name: str = None):
        """
        新しいコーディングセッションを開始します
        
        Args:
            interaction: Discord interaction
            project_name: オプションのプロジェクト名
        """
        try:
            # Check if user already has active session
            user_id = str(interaction.user.id)
            active_session = self.session_manager.get_user_active_session(user_id)
            
            if active_session:
                await interaction.response.send_message(
                    f"❌ You already have an active session: `{active_session[:8]}`\n"
                    f"Use `/coding end` to close it first.",
                    ephemeral=True
                )
                return
            
            # Defer response
            await interaction.response.defer(ephemeral=True)
            
            # Get database session
            db_session = self.bot.db_manager.get_session()
            
            try:
                # Get or create user
                user = await UserRepository.get_or_create_user(
                    db_session,
                    user_id,
                    interaction.user.name,
                    interaction.user.discriminator
                )
                
                # Check if user has API key
                api_key = await APIKeyRepository.get_active_api_key(db_session, user.id)
                
                if not api_key:
                    await interaction.followup.send(
                        "❌ No OpenRouter API key found!\n"
                        "Please register your API key first using `/setting`",
                        ephemeral=True
                    )
                    return
                
                # Decrypt API key
                decrypted_key = self.bot.encryption_manager.decrypt(api_key.encrypted_key)
                
                # Create session and CodingRoom
                session_uuid, coding_room = await self.session_manager.create_session(
                    db_session,
                    interaction.user,
                    interaction.guild,
                    project_name or "New Project"
                )
                
                # Initialize AI service for this user
                model_preset = getattr(user, "model_preset", "balance")
                
                openrouter_client = OpenRouterClient(decrypted_key)
                ai_service = AIService(openrouter_client)
                ai_service.set_model_by_preset(model_preset)
                self.ai_services[user_id] = ai_service
                
                # Send success message
                embed = discord.Embed(
                    title="✅ Coding Session Started",
                    description=f"Your private coding room has been created!",
                    color=discord.Color.green()
                )
                embed.add_field(name="Session ID", value=f"`{session_uuid[:8]}`", inline=False)
                embed.add_field(name="Channel", value=coding_room.mention, inline=False)
                
                if project_name:
                    embed.add_field(name="Project", value=project_name, inline=False)
                
                embed.add_field(
                    name="Next Steps",
                    value="1. Go to your coding room\n"
                          "2. Just type your message to chat with AI\n"
                          "3. Use `/coding end` when done",
                    inline=False
                )
                embed.set_footer(text="Made by RovaexTeam")
                
                await interaction.followup.send(embed=embed, ephemeral=True)
                
                # Send welcome message in coding room
                welcome_embed = discord.Embed(
                    title="🤖 Welcome to your Coding Session",
                    description="I'm your AI coding assistant. Tell me what you'd like to build!",
                    color=discord.Color.blue()
                )
                welcome_embed.set_footer(text="Made by RovaexTeam")
                await coding_room.send(embed=welcome_embed)
                
                logger.info(f"Created session {session_uuid} for {interaction.user.name}")
            finally:
                await db_session.close()
        except Exception as e:
            logger.error(f"Error in coding_start: {e}", exc_info=True)
            if interaction.response.is_done():
                await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)
            else:
                await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

    @coding_group.command(name="end", description="現在のコーディングセッションを終了します")
    async def coding_end(self, interaction: discord.Interaction):
        """
        現在のコーディングセッションを終了します
        
        Args:
            interaction: Discord interaction
        """
        try:
            user_id = str(interaction.user.id)
            session_uuid = self.session_manager.get_user_active_session(user_id)
            
            if not session_uuid:
                await interaction.response.send_message("❌ You don't have an active session.", ephemeral=True)
                return
            
            # 確認メッセージを送信
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
                    
                    await self.session_manager.end_session(self.session_uuid)
                    # 終了通知は既存メッセージを更新
                    await interaction.response.edit_message(content="✅ セッションを終了しました。", embed=None, view=None)
                
                @discord.ui.button(label="いいえ", style=discord.ButtonStyle.secondary, emoji="❌")
                async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                    if str(interaction.user.id) != self.user_id:
                        await interaction.response.send_message("この操作は実行者本人のみ可能です。", ephemeral=True)
                        return
                    
                    # キャンセル通知も既存メッセージを更新
                    await interaction.response.edit_message(content="セッションの終了をキャンセルしました。", embed=None, view=None)
            
            view = ConfirmView(self.session_manager, session_uuid, user_id)
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in coding_end: {e}", exc_info=True)
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

    @coding_group.command(name="server", description="サーバー内の統計情報を表示します")
    @PermissionManager.has_permission(PermissionLevel.ADMIN)
    async def coding_server(self, interaction: discord.Interaction):
        """サーバー内の統計情報を表示します"""
        try:
            await interaction.response.defer(ephemeral=True)
            
            db_session = self.bot.db_manager.get_session()
            try:
                # 統計情報の取得（仮の実装）
                user_count = await UserRepository.count_users(db_session)
                session_count = await SessionRepository.count_sessions(db_session)
                active_sessions = await SessionRepository.count_active_sessions(db_session)
                message_count = await MessageRepository.count_messages(db_session)
                
                embed = discord.Embed(
                    title="📊 サーバー統計情報",
                    color=discord.Color.blue()
                )
                embed.add_field(name="登録ユーザー数", value=str(user_count), inline=True)
                embed.add_field(name="総セッション数", value=str(session_count), inline=True)
                embed.add_field(name="アクティブセッション数", value=str(active_sessions), inline=True)
                embed.add_field(name="総メッセージ数", value=str(message_count), inline=True)
                embed.set_footer(text="Made by RovaexTeam")
                
                await interaction.followup.send(embed=embed, ephemeral=True)
            finally:
                await db_session.close()
        except Exception as e:
            logger.error(f"Error in coding_server: {e}", exc_info=True)
            await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)


async def setup(bot: commands.Bot):
    """Setup the cog"""
    cog = CodingCog(bot)
    await bot.add_cog(cog)
