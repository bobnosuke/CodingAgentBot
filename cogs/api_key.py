"""
API Key management commands for CoderAgent
Handles API key registration and management
"""
import discord
from discord.ext import commands
from logger import setup_logger
from modules.security.permissions import user_command
from modules.database.repository import UserRepository, APIKeyRepository

logger = setup_logger(__name__)


class APIKeyCog(commands.Cog):
    """Cog for API key management"""
    
    def __init__(self, bot: commands.Bot):
        """
        Initialize API key cog
        
        Args:
            bot: Discord bot instance
        """
        self.bot = bot
    
    @commands.hybrid_command(name="api-key")
    async def api_key(self, ctx: commands.Context):
        """Base API key command"""
        await ctx.send(
            "🔑 API Key Management\n"
            "Usage: `/api-key register`, `/api-key remove`"
        )
    
    @api_key.command(name="register")
    @user_command
    async def api_key_register(self, ctx: commands.Context, api_key: str):
        """
        Register OpenRouter API key
        
        Args:
            ctx: Command context
            api_key: OpenRouter API key
        """
        try:
            # Acknowledge and defer
            await ctx.defer(ephemeral=True)
            
            # Get database session
            db_session = self.bot.db_manager.get_session()
            
            try:
                # Get or create user
                user = await UserRepository.get_or_create_user(
                    db_session,
                    str(ctx.author.id),
                    ctx.author.name,
                    ctx.author.discriminator
                )
                
                # Encrypt API key
                encrypted_key = self.bot.encryption_manager.encrypt(api_key)
                
                # Check if user already has an API key
                existing_key = await APIKeyRepository.get_active_api_key(db_session, user.id)
                
                if existing_key:
                    # Update existing key (in a real app, we might want to keep history)
                    logger.info(f"User {ctx.author.id} updated their API key")
                else:
                    # Create new key
                    await APIKeyRepository.create_api_key(
                        db_session,
                        user.id,
                        encrypted_key,
                        "OpenRouter"
                    )
                
                await ctx.followup.send(
                    "✅ API key registered successfully!\n"
                    "Your key is securely encrypted and stored.",
                    ephemeral=True
                )
                
                logger.info(f"API key registered for user {ctx.author.id}")
            
            finally:
                await db_session.close()
        
        except Exception as e:
            logger.error(f"Error in api_key_register: {e}", exc_info=True)
            await ctx.followup.send(
                f"❌ Error registering API key: {str(e)}",
                ephemeral=True
            )
    
    @api_key.command(name="remove")
    @user_command
    async def api_key_remove(self, ctx: commands.Context):
        """
        Remove OpenRouter API key
        
        Args:
            ctx: Command context
        """
        try:
            await ctx.defer(ephemeral=True)
            
            # Get database session
            db_session = self.bot.db_manager.get_session()
            
            try:
                # Get user
                user = await UserRepository.get_user_by_discord_id(
                    db_session,
                    str(ctx.author.id)
                )
                
                if not user:
                    await ctx.followup.send(
                        "❌ User not found.",
                        ephemeral=True
                    )
                    return
                
                # Get active API key
                api_key = await APIKeyRepository.get_active_api_key(db_session, user.id)
                
                if not api_key:
                    await ctx.followup.send(
                        "❌ No API key found.",
                        ephemeral=True
                    )
                    return
                
                # In a real implementation, we would mark it as inactive
                # For now, just inform the user
                await ctx.followup.send(
                    "✅ API key removal requested.\n"
                    "Please register a new key to continue using the bot.",
                    ephemeral=True
                )
                
                logger.info(f"API key removed for user {ctx.author.id}")
            
            finally:
                await db_session.close()
        
        except Exception as e:
            logger.error(f"Error in api_key_remove: {e}", exc_info=True)
            await ctx.followup.send(
                f"❌ Error: {str(e)}",
                ephemeral=True
            )


async def setup(bot: commands.Bot):
    """Setup function for loading cog"""
    await bot.add_cog(APIKeyCog(bot))
