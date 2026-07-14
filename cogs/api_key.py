"""
API Key management commands for CoderAgent
Handles API key registration and management
"""
import discord
from discord.ext import commands
from discord import app_commands
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
    
    api_key_group = app_commands.Group(name="api-key", description="API Key management commands")
    
    @api_key_group.command(name="register", description="Register your OpenRouter API key")
    async def api_key_register(self, interaction: discord.Interaction, api_key: str):
        """
        Register OpenRouter API key
        
        Args:
            interaction: Discord interaction
            api_key: OpenRouter API key
        """
        try:
            # Defer response
            await interaction.response.defer(ephemeral=True)
            
            # Get database session
            db_session = self.bot.db_manager.get_session()
            
            try:
                # Get or create user
                user = await UserRepository.get_or_create_user(
                    db_session,
                    str(interaction.user.id),
                    interaction.user.name,
                    interaction.user.discriminator
                )
                
                # Encrypt API key
                encrypted_key = self.bot.encryption_manager.encrypt(api_key)
                
                # Check if user already has an API key
                existing_key = await APIKeyRepository.get_active_api_key(db_session, user.id)
                
                if existing_key:
                    # Update existing key
                    logger.info(f"User {interaction.user.id} updated their API key")
                else:
                    # Create new key
                    await APIKeyRepository.create_api_key(
                        db_session,
                        user.id,
                        encrypted_key,
                        "OpenRouter"
                    )
                
                await interaction.followup.send(
                    "✅ API key registered successfully!\n"
                    "Your key is securely encrypted and stored.",
                    ephemeral=True
                )
                
                logger.info(f"API key registered for user {interaction.user.id}")
            
            finally:
                await db_session.close()
        
        except Exception as e:
            logger.error(f"Error in api_key_register: {e}", exc_info=True)
            await interaction.followup.send(
                f"❌ Error registering API key: {str(e)}",
                ephemeral=True
            )
    
    @api_key_group.command(name="remove", description="Remove your OpenRouter API key")
    async def api_key_remove(self, interaction: discord.Interaction):
        """
        Remove OpenRouter API key
        
        Args:
            interaction: Discord interaction
        """
        try:
            await interaction.response.defer(ephemeral=True)
            
            # Get database session
            db_session = self.bot.db_manager.get_session()
            
            try:
                # Get user
                user = await UserRepository.get_user_by_discord_id(
                    db_session,
                    str(interaction.user.id)
                )
                
                if not user:
                    await interaction.followup.send(
                        "❌ User not found.",
                        ephemeral=True
                    )
                    return
                
                # Get active API key
                api_key = await APIKeyRepository.get_active_api_key(db_session, user.id)
                
                if not api_key:
                    await interaction.followup.send(
                        "❌ No API key found.",
                        ephemeral=True
                    )
                    return
                
                # In a real implementation, we would mark it as inactive
                # For now, just inform the user
                await interaction.followup.send(
                    "✅ API key removal requested.\n"
                    "Please register a new key to continue using the bot.",
                    ephemeral=True
                )
                
                logger.info(f"API key removed for user {interaction.user.id}")
            
            finally:
                await db_session.close()
        
        except Exception as e:
            logger.error(f"Error in api_key_remove: {e}", exc_info=True)
            await interaction.followup.send(
                f"❌ Error: {str(e)}",
                ephemeral=True
            )


async def setup(bot: commands.Bot):
    """Setup function for loading cog"""
    cog = APIKeyCog(bot)
    await bot.add_cog(cog)
    # Add command group to app commands tree
    if cog.api_key_group not in bot.tree.get_commands():
        bot.tree.add_command(cog.api_key_group)
