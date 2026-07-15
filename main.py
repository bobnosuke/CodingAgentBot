"""
CoderAgent - Main entry point
Discord Bot for AI-powered code generation and development
"""
import asyncio
import os
from pathlib import Path
import discord
from discord.ext import commands
from config import Config
from logger import setup_logger
from modules.database.database import get_db_manager
from modules.security.encryption import get_encryption_manager

logger = setup_logger(__name__)


class CoderAgent(commands.Bot):
    """
    Main CoderAgent Bot class
    Inherits from discord.ext.commands.Bot for command handling
    """
    
    def __init__(self, *args, **kwargs):
        """Initialize the bot with proper intents and configuration"""
        # Setup intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.guilds = True
        
        # Initialize parent class
        super().__init__(
            command_prefix=Config.BOT_PREFIX,
            intents=intents,
            *args,
            **kwargs
        )
        
        self.config = Config
        self.db_manager = None
        self.encryption_manager = None
        self.owner_id = int(os.getenv("OWNER_ID")) if os.getenv("OWNER_ID") else None
        
        logger.info("CoderAgent instance initialized")
    
    async def setup_hook(self) -> None:
        """Called when the bot is setting up"""
        logger.info("Setting up bot hooks...")
        
        # Initialize database
        try:
            self.db_manager = await get_db_manager()
            logger.info("✅ Database initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize database: {e}")
            raise
        
        # Initialize encryption manager
        try:
            self.encryption_manager = get_encryption_manager(Config.ENCRYPTION_KEY)
            logger.info("✅ Encryption manager initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize encryption manager: {e}")
            raise
        
        # Load cogs
        await self.load_cogs()

        # Setup global app command error handler
        from modules.security.errors import ErrorHandler
        self.tree.on_error = ErrorHandler.handle_error
        logger.info("✅ App command error handling initialized")
    
    async def load_cogs(self) -> None:
        """Load all cogs from cogs directory"""
        cogs_dir = Path(__file__).parent / "cogs"
        
        for filename in os.listdir(cogs_dir):
            if filename.endswith(".py") and not filename.startswith("_"):
                cog_name = filename[:-3]
                try:
                    await self.load_extension(f"cogs.{cog_name}")
                    logger.info(f"✅ Loaded cog: {cog_name}")
                except Exception as e:
                    logger.error(f"❌ Failed to load cog {cog_name}: {e}")
    
    async def on_ready(self) -> None:
        """Called when the bot has successfully connected to Discord"""
        logger.info(f"✅ Bot logged in as {self.user}")
        logger.info(f"Bot ID: {self.user.id}")
        logger.info(f"Connected to {len(self.guilds)} guild(s)")
        
        # Set bot status
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="for /coding commands"
            )
        )
        
        # Sync commands to Discord
        await self.tree.sync()
        logger.info("✅ Commands synced to Discord")

    async def reload_cogs(self) -> None:
        """Reload all cogs"""
        cogs_dir = Path(__file__).parent / "cogs"
        for filename in os.listdir(cogs_dir):
            if filename.endswith(".py") and not filename.startswith("_"):
                cog_name = filename[:-3]
                try:
                    await self.unload_extension(f"cogs.{cog_name}")
                    await self.load_extension(f"cogs.{cog_name}")
                    logger.info(f"🔄 Reloaded cog: {cog_name}")
                except Exception as e:
                    logger.error(f"❌ Failed to reload cog {cog_name}: {e}")

    @commands.command(name="reload", description="Reload all cogs (Owner only)")
    async def reload_command(self, ctx: commands.Context):
        """
        Reload all cogs
        
        Args:
            ctx: Command context
        """
        if ctx.author.id != self.owner_id:
            await ctx.send("❌ You are not the owner of this bot.", ephemeral=True)
            return

        await ctx.send("🔄 Reloading cogs...", ephemeral=True)
        await self.reload_cogs()
        await ctx.send("✅ Cogs reloaded successfully!", ephemeral=True)
    
    async def on_error(self, event: str, *args, **kwargs) -> None:
        """Handle errors from event listeners"""
        logger.error(f"Error in {event}: {args}", exc_info=True)
    
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        """Handle command errors using central handler"""
        from modules.security.errors import ErrorHandler
        await ErrorHandler.handle_error(ctx, error)
    
    async def close(self) -> None:
        """Cleanup before closing"""
        logger.info("Shutting down CoderAgent...")
        
        # Close database connections
        if self.db_manager:
            await self.db_manager.close()
        
        await super().close()


async def main():
    """Main entry point for the bot"""
    # Validate configuration
    if not Config.validate():
        logger.error("Configuration validation failed")
        return
    
    # Create bot instance
    bot = CoderAgent()
    
    # Start the bot
    try:
        async with bot:
            await bot.start(Config.DISCORD_TOKEN)
    except KeyboardInterrupt:
        logger.info("Bot interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
    finally:
        await bot.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application terminated by user")
    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)
