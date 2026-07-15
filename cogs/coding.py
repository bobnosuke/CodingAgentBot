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
            
            # ephemeral=False に変更（一般ユーザーも利用可能にするため）
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
            
            # Defer response as this may take a while
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
                # ユーザーのモデルプリセットを取得して反映
                model_preset = getattr(user, "model_preset", "balance")
                
                openrouter_client = OpenRouterClient(decrypted_key)
                ai_service = AIService(openrouter_client)
                ai_service.set_model_by_preset(model_preset)
                self.ai_services[user_id] = ai_service
                
                # Send success message (ephemeral - only visible to user)
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
                
                # Send welcome message in coding room (visible to everyone with access)
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
            
            finally:
                await db_session.close()
        
        except Exception as e:
            logger.error(f"Error in coding_start: {e}", exc_info=True)
            await interaction.followup.send(
                f"❌ Error starting session: {str(e)}",
                ephemeral=True
            )
    

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Ignore messages from bots
        if message.author.bot:
            return

        user_id = str(message.author.id)
        session_uuid = self.session_manager.get_user_active_session(user_id)

        # Check if message is in an active CodingRoom and from the session owner
        session_info = self.session_manager.get_session(session_uuid) if session_uuid else None
        if session_info and str(message.channel.id) == session_info["channel_id"]:
            # Ignore messages that start with the bot's prefix (commands)
            # According to COMMANDS.md, messages starting with '!' are commands.
            if message.content.startswith(self.bot.command_prefix):
                await self.bot.process_commands(message)
                return

            # Check if AI service is initialized
            if user_id not in self.ai_services:
                await message.channel.send(
                    "❌ AI service not initialized. Please try starting a new session."
                )
                await self.bot.process_commands(message)
                return

            # Get AI service
            ai_service = self.ai_services[user_id]

            # Send thinking message
            thinking_msg = await message.channel.send("🤔 Thinking...")

            try:
                full_response = ""
                async for chunk in ai_service.chat(message.content):
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
                            await message.channel.send(chunk)
                    else:
                        await thinking_msg.edit(content=full_response)
                else:
                    await thinking_msg.edit(content="❌ No response generated")

            except Exception as e:
                logger.error(f"Error generating response in on_message: {e}", exc_info=True)
                await thinking_msg.edit(content=f"❌ Error: {str(e)}")

            # Log message for usage tracking
            db_session = self.bot.db_manager.get_session()
            try:
                db_session_id = session_info["db_session_id"]
                # Save user message
                await MessageRepository.add_message(
                    db_session,
                    db_session_id,
                    "user",
                    message.content,
                    token_input=ai_service.last_input_tokens
                )
                # Save assistant response
                if full_response:
                    await MessageRepository.add_message(
                        db_session,
                        db_session_id,
                        "assistant",
                        full_response,
                        token_output=ai_service.last_output_tokens
                    )
            finally:
                await db_session.close()
            
            # Since we handled the AI chat, we don't need to process other commands
            return

        # Process commands for messages outside CodingRoom or prefix commands
        await self.bot.process_commands(message)

    @coding_group.command(name="server", description="View server statistics (Admin only)")
    @PermissionManager.has_permission(PermissionLevel.ADMIN)
    async def coding_server(self, interaction: discord.Interaction):
        """
        View server statistics
        
        Args:
            interaction: Discord interaction
        """
        try:
            # Defer response
            await interaction.response.defer(ephemeral=True)
            
            # Get database session
            db_session = self.bot.db_manager.get_session()
            
            try:
                # Get statistics
                total_users = await UserRepository.count_users(db_session)
                total_sessions = await SessionRepository.count_sessions(db_session)
                active_sessions = await SessionRepository.count_active_sessions(db_session)
                total_messages = await MessageRepository.count_messages(db_session)
                
                # Create embed
                embed = discord.Embed(
                    title="📊 Server Statistics",
                    description="CoderAgent の統計情報です",
                    color=discord.Color.blue()
                )
                embed.add_field(name="👥 Total Users", value=str(total_users), inline=True)
                embed.add_field(name="📝 Total Sessions", value=str(total_sessions), inline=True)
                embed.add_field(name="🟢 Active Sessions", value=str(active_sessions), inline=True)
                embed.add_field(name="💬 Total Messages", value=str(total_messages), inline=False)
                embed.set_footer(text="Made by RovaexTeam")
                
                await interaction.followup.send(embed=embed, ephemeral=True)
                
                logger.info(f"Admin {interaction.user.name} viewed server statistics")
            
            finally:
                await db_session.close()
        
        except Exception as e:
            logger.error(f"Error in coding_server: {e}", exc_info=True)
            await interaction.followup.send(
                f"❌ Error: {str(e)}",
                ephemeral=True
            )
    
    @coding_group.command(name="end", description="現在のコーディングセッションを終了します")
    async def coding_end(self, interaction: discord.Interaction):
        """
        現在のコーディングセッションを終了します
        
        Args:
            interaction: Discord interaction
        """
        try:
            user_id = str(interaction.user.id)
            
            # Check if user has active session
            session_uuid = self.session_manager.get_user_active_session(user_id)
            
            if not session_uuid:
                await interaction.response.send_message(
                    "❌ You don't have an active coding session.",
                    ephemeral=True
                )
                return
            
            # Defer response
            await interaction.response.defer(ephemeral=True)
            
            # End session
            await self.session_manager.end_session(session_uuid)
            
            # Clean up AI service
            if user_id in self.ai_services:
                del self.ai_services[user_id]
            
            embed = discord.Embed(
                title="✅ Coding Session Ended",
                description="Your coding room has been closed.",
                color=discord.Color.green()
            )
            embed.add_field(name="Session ID", value=f"`{session_uuid[:8]}`", inline=False)
            embed.set_footer(text="Made by RovaexTeam")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            logger.info(f"Ended session {session_uuid} for {interaction.user.name}")
        
        except Exception as e:
            logger.error(f"Error in coding_end: {e}", exc_info=True)
            await interaction.response.send_message(
                f"❌ Error ending session: {str(e)}",
                ephemeral=True
            )


async def setup(bot: commands.Bot):
    cog = CodingCog(bot)
    await bot.add_cog(cog)
    if cog.coding_group not in bot.tree.get_commands():
        bot.tree.add_command(cog.coding_group)
