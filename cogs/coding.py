"""
Coding commands for CoderAgent
Handles /coding start, /coding chat, /coding end commands
"""
import discord
from discord.ext import commands
from discord import app_commands
from logger import setup_logger
from modules.security.permissions import PermissionLevel, PermissionManager
from modules.database.repository import UserRepository, APIKeyRepository, MessageRepository
from modules.session.manager import SessionManager
from modules.ai.openrouter import OpenRouterClient, AIService

logger = setup_logger(__name__)


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
    
    @coding_group.command(name="start", description="Start a new coding session")
    async def coding_start(self, interaction: discord.Interaction, project_name: str = None):
        """
        Start a new coding session
        
        Args:
            interaction: Discord interaction
            project_name: Optional project name
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
                        "Please register your API key first using `/api-key register`",
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
                    project_name
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
                          "2. Use `/coding chat` to start coding with AI\n"
                          "3. Use `/coding end` when done",
                    inline=False
                )
                embed.set_footer(text="Your coding room is private - only you, the bot, and admins can see it")
                
                await interaction.followup.send(embed=embed, ephemeral=True)
                
                # Send welcome message in coding room (visible to everyone with access)
                welcome_embed = discord.Embed(
                    title="🤖 Welcome to your Coding Session",
                    description="I'm your AI coding assistant. Tell me what you'd like to build!",
                    color=discord.Color.blue()
                )
                welcome_embed.add_field(
                    name="Examples",
                    value="• `/coding chat Create a Discord bot`\n"
                          "• `/coding chat Add login functionality`\n"
                          "• `/coding chat Fix this code: ...`\n"
                          "• `/coding chat Explain how decorators work`",
                    inline=False
                )
                welcome_embed.add_field(
                    name="Tips",
                    value="• Use `/save` to save generated code\n"
                          "• Use `/list` to see all saved files\n"
                          "• Use `/download` to download all files as ZIP",
                    inline=False
                )
                
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
    
    @coding_group.command(name="chat", description="Chat with AI in your coding session")
    async def coding_chat(self, interaction: discord.Interaction, message: str):
        """
        Chat with AI in coding session
        
        Args:
            interaction: Discord interaction
            message: User's message
        """
        try:
            user_id = str(interaction.user.id)
            
            # Check if user has active session
            session_uuid = self.session_manager.get_user_active_session(user_id)
            
            if not session_uuid:
                await interaction.response.send_message(
                    "❌ You don't have an active coding session. Use `/coding start` first.",
                    ephemeral=True
                )
                return
            
            # Check if this command is being used in the correct CodingRoom
            session_info = self.session_manager.get_session(session_uuid)
            
            if session_info and str(interaction.channel.id) != session_info["channel_id"]:
                await interaction.response.send_message(
                    "❌ This command can only be used in your coding room!",
                    ephemeral=True
                )
                return
            
            # Check if AI service is initialized
            if user_id not in self.ai_services:
                await interaction.response.send_message(
                    "❌ AI service not initialized. Please try starting a new session.",
                    ephemeral=True
                )
                return
            
            # Defer response
            await interaction.response.defer()
            
            # Get AI service
            ai_service = self.ai_services[user_id]
            
            # Send thinking message
            thinking_msg = await interaction.followup.send("🤔 Thinking...")
            
            try:
                # Generate response
                full_response = ""
                
                async for chunk in ai_service.chat(message):
                    full_response += chunk
                    
                    # Update message every 50 characters or at the end
                    if len(full_response) % 50 == 0 or len(full_response) > 1900:
                        try:
                            await thinking_msg.edit(content=full_response[:2000])
                        except discord.errors.HTTPException:
                            pass  # Message too long or other error
                
                # Final update
                if full_response:
                    # Split into chunks if too long
                    if len(full_response) > 2000:
                        chunks = [full_response[i:i+2000] for i in range(0, len(full_response), 2000)]
                        
                        await thinking_msg.edit(content=chunks[0])
                        
                        for chunk in chunks[1:]:
                            await interaction.followup.send(chunk)
                    else:
                        await thinking_msg.edit(content=full_response)
                else:
                    await thinking_msg.edit(content="❌ No response generated")
            
            except Exception as e:
                logger.error(f"Error generating response: {e}")
                await thinking_msg.edit(content=f"❌ Error: {str(e)}")
        
        except Exception as e:
            logger.error(f"Error in coding_chat: {e}", exc_info=True)
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)
    
    @coding_group.command(name="end", description="End your current coding session")
    async def coding_end(self, interaction: discord.Interaction):
        """
        End the current coding session
        
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
            
            await interaction.response.defer(ephemeral=True)
            
            # Get database session
            db_session = self.bot.db_manager.get_session()
            
            try:
                session_info = self.session_manager.get_session(session_uuid)
                
                # Close session
                await self.session_manager.close_session(
                    db_session,
                    session_uuid,
                    delete_channel=True
                )
                
                # Remove AI service
                if user_id in self.ai_services:
                    del self.ai_services[user_id]
                
                await interaction.followup.send(
                    f"✅ Session `{session_uuid[:8]}` closed.\n"
                    f"Your coding room has been deleted.",
                    ephemeral=True
                )
                
                logger.info(f"Closed session {session_uuid} for {interaction.user.name}")
            
            finally:
                await db_session.close()
        
        except Exception as e:
            logger.error(f"Error in coding_end: {e}", exc_info=True)
            await interaction.response.send_message(
                f"❌ Error closing session: {str(e)}",
                ephemeral=True
            )


async def setup(bot: commands.Bot):
    """Setup function for loading cog"""
    cog = CodingCog(bot)
    await bot.add_cog(cog)
    # Add command group to app commands tree
    if cog.coding_group not in bot.tree.get_commands():
        bot.tree.add_command(cog.coding_group)
