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
    
    async def on_error(self, event: str, *args, **kwargs) -> None:
        """Handle errors from event listeners"""
        logger.error(f"Error in {event}: {args}", exc_info=True)
    
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        """Handle command errors"""
        if isinstance(error, commands.CommandNotFound):
            logger.warning(f"Command not found: {ctx.message.content}")
        elif isinstance(error, commands.MissingRequiredArgument):
            logger.warning(f"Missing argument for command {ctx.command}: {error}")
            await ctx.send(f"❌ Missing required argument: {error.param.name}")
        elif isinstance(error, commands.MissingPermissions):
            logger.warning(f"Permission denied for {ctx.author}: {error}")
            await ctx.send("❌ You don't have permission to use this command.")
        elif isinstance(error, commands.CheckFailure):
            # This handles our custom permission checks
            pass  # Message already sent by the check
        else:
            logger.error(f"Command error: {error}", exc_info=True)
            await ctx.send("❌ An error occurred while processing your command.")
    
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
