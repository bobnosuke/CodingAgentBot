"""
Coding commands for CoderAgent
Handles /coding start, /coding chat, /coding end commands
"""
import discord
from discord.ext import commands
from logger import setup_logger
from modules.security.permissions import user_command, PermissionLevel, PermissionManager
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
    
    @commands.command(name="coding", aliases=["code"])
    async def coding(self, ctx: commands.Context):
        """Base coding command"""
        await ctx.send(
            "❓ Usage: `!coding start`, `!coding chat <message>`, `!coding end`\n"
            "Use `!coding start` to begin a coding session."
        )
    
    @commands.command(name="start", parent="coding")
    @user_command
    async def coding_start(self, ctx: commands.Context, project_name: str = None):
        """
        Start a new coding session
        
        Args:
            ctx: Command context
            project_name: Optional project name
        """
        try:
            # Check if user already has active session
            user_id = str(ctx.author.id)
            active_session = self.session_manager.get_user_active_session(user_id)
            
            if active_session:
                await ctx.send(
                    f"❌ You already have an active session: `{active_session[:8]}`\n"
                    f"Use `/coding end` to close it first."
                )
                return
            
            # Defer response as this may take a while
            await ctx.defer()
            
            # Get database session
            db_session = self.bot.db_manager.get_session()
            
            try:
                # Get or create user
                user = await UserRepository.get_or_create_user(
                    db_session,
                    user_id,
                    ctx.author.name,
                    ctx.author.discriminator
                )
                
                # Check if user has API key
                api_key = await APIKeyRepository.get_active_api_key(db_session, user.id)
                
                if not api_key:
                    await ctx.followup.send(
                        "❌ No OpenRouter API key found!\n"
                        "Please register your API key first using `/api-key register`"
                    )
                    return
                
                # Decrypt API key
                decrypted_key = self.bot.encryption_manager.decrypt(api_key.encrypted_key)
                
                # Create session
                session_uuid, coding_room = await self.session_manager.create_session(
                    db_session,
                    ctx.author,
                    ctx.guild,
                    project_name
                )
                
                # Initialize AI service for this user
                openrouter_client = OpenRouterClient(decrypted_key)
                self.ai_services[user_id] = AIService(openrouter_client)
                
                # Send success message
                embed = discord.Embed(
                    title="✅ Coding Session Started",
                    description=f"Your coding room is ready!",
                    color=discord.Color.green()
                )
                embed.add_field(name="Session ID", value=f"`{session_uuid[:8]}`", inline=False)
                embed.add_field(name="Channel", value=coding_room.mention, inline=False)
                
                if project_name:
                    embed.add_field(name="Project", value=project_name, inline=False)
                
                embed.set_footer(text="Use /coding chat to start coding!")
                
                await ctx.followup.send(embed=embed)
                
                # Send welcome message in coding room
                welcome_embed = discord.Embed(
                    title="🤖 Welcome to your Coding Session",
                    description="I'm your AI coding assistant. Tell me what you'd like to build!",
                    color=discord.Color.blue()
                )
                welcome_embed.add_field(
                    name="Examples",
                    value="• Create a Discord bot\n• Build a web scraper\n• Fix this code\n• Explain this concept",
                    inline=False
                )
                
                await coding_room.send(embed=welcome_embed)
            
            finally:
                await db_session.close()
        
        except Exception as e:
            logger.error(f"Error in coding_start: {e}", exc_info=True)
            await ctx.followup.send(f"❌ Error starting session: {str(e)}")
    
    @commands.command(name="chat")
    @user_command
    async def coding_chat(self, ctx: commands.Context, *, message: str):
        """
        Chat with AI in coding session
        
        Args:
            ctx: Command context
            message: User's message
        """
        try:
            user_id = str(ctx.author.id)
            
            # Check if user has active session
            session_uuid = self.session_manager.get_user_active_session(user_id)
            
            if not session_uuid:
                await ctx.send("❌ You don't have an active coding session. Use `/coding start` first.")
                return
            
            # Check if AI service is initialized
            if user_id not in self.ai_services:
                await ctx.send("❌ AI service not initialized. Please try starting a new session.")
                return
            
            # Defer response
            await ctx.defer()
            
            # Get AI service
            ai_service = self.ai_services[user_id]
            
            # Send thinking message
            thinking_msg = await ctx.followup.send("🤔 Thinking...")
            
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
                            await ctx.followup.send(chunk)
                    else:
                        await thinking_msg.edit(content=full_response)
                else:
                    await thinking_msg.edit(content="❌ No response generated")
            
            except Exception as e:
                logger.error(f"Error generating response: {e}")
                await thinking_msg.edit(content=f"❌ Error: {str(e)}")
        
        except Exception as e:
            logger.error(f"Error in coding_chat: {e}", exc_info=True)
            await ctx.send(f"❌ Error: {str(e)}")
    
    @commands.command(name="end")
    @user_command
    async def coding_end(self, ctx: commands.Context):
        """
        End the current coding session
        
        Args:
            ctx: Command context
        """
        try:
            user_id = str(ctx.author.id)
            
            # Check if user has active session
            session_uuid = self.session_manager.get_user_active_session(user_id)
            
            if not session_uuid:
                await ctx.send("❌ You don't have an active coding session.")
                return
            
            await ctx.defer()
            
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
                
                await ctx.followup.send(
                    f"✅ Session `{session_uuid[:8]}` closed.\n"
                    f"Your coding room has been deleted."
                )
            
            finally:
                await db_session.close()
        
        except Exception as e:
            logger.error(f"Error in coding_end: {e}", exc_info=True)
            await ctx.send(f"❌ Error closing session: {str(e)}")


async def setup(bot: commands.Bot):
    """Setup function for loading cog"""
    await bot.add_cog(CodingCog(bot))
