import discord
from discord.ext import commands
from discord import app_commands
import os
import asyncio
from dotenv import load_dotenv
from logger import setup_logger
from modules.database.database import DatabaseManager
from modules.security.encryption import EncryptionManager
from modules.utils.i18n import i18n, CommandTranslator

# Load environment variables
load_dotenv()

logger = setup_logger(__name__)

class CoderAgent(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None
        )
        
        self.db_manager = DatabaseManager()
        # Initialize encryption manager with key from environment
        master_key = os.getenv("ENCRYPTION_KEY")
        self.encryption_manager = EncryptionManager(master_key)

    async def setup_hook(self):
        logger.info("Setting up bot hooks...")
        
        # Initialize database
        await self.db_manager.initialize()
        logger.info("✅ Database initialized")
        
        # Register Translator
        await self.tree.set_translator(CommandTranslator())
        logger.info("✅ Command translator registered")
        
        # Load Cogs
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py") and not filename.startswith("__"):
                try:
                    await self.load_extension(f"cogs.{filename[:-3]}")
                    logger.info(f"✅ Loaded cog: {filename[:-3]}")
                except Exception as e:
                    logger.error(f"❌ Failed to load cog {filename[:-3]}: {e}")

        # Register persistent views
        from cogs.setting import SettingView
        from cogs.coding import CodingPanelView
        self.add_view(SettingView(self))
        self.add_view(CodingPanelView(self))
        logger.info("✅ Persistent views registered")

    async def on_ready(self):
        logger.info(f"✅ Bot logged in as {self.user}")
        logger.info(f"Bot ID: {self.user.id}")
        logger.info(f"Connected to {len(self.guilds)} guild(s)")
        
        try:
            # Sync commands
            await self.tree.sync()
            logger.info("✅ Commands synced to Discord")
        except Exception as e:
            logger.error(f"❌ Failed to sync commands: {e}")

    async def on_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(f"Cooldown: Try again in {error.retry_after:.2f}s", ephemeral=True)
        else:
            logger.error(f"App command error: {error}")
            if not interaction.response.is_done():
                await interaction.response.send_message("An error occurred while processing the command.", ephemeral=True)

async def main():
    bot = CoderAgent()
    
    # Setup global error handler for tree
    bot.tree.on_error = bot.on_app_command_error
    
    async with bot:
        token = os.getenv("DISCORD_TOKEN")
        if not token:
            logger.error("❌ DISCORD_TOKEN not found in .env")
            return
        await bot.start(token)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
