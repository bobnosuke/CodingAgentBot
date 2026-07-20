import os
# Set API keys from user input BEFORE any other imports that might load config.py


os.environ["DISCORD_TOKEN"] = "dummy_discord_token"


os.environ["ENCRYPTION_KEY"] = "A4LLtpT--YdjP_E2ribBM5R3pur5_OwOXFPdgGyDWvk=" # Set a dummy key for testing

import asyncio
import uuid
from typing import Any
from datetime import datetime, timezone

import discord
from discord.ext import commands
from discord import app_commands

from config import Config
from logger import setup_logger
from modules.database.database import DatabaseManager
from modules.database.repository import UserRepository, APIKeyRepository, SessionRepository, RequirementRepository, TaskRepository
from modules.security.encryption import EncryptionManager
from modules.utils.i18n import i18n
from modules.ai.views import RequirementApprovalView, RefinementModal
from modules.ai.agent import CodingAgent as OldCodingAgent # Avoid name conflict with test bot

# Setup logger
logger = setup_logger(__name__)

# Mock Discord objects
class MockUser:
    def __init__(self, id, name, discriminator="0000"):
        self.id = id
        self.name = name
        self.discriminator = discriminator
        self.mention = f"<@{self.id}>"

class MockGuild:
    def __init__(self, id, name="Test Guild"):
        self.id = id
        self.name = name
        self.default_role = "dummy_default_role"
        self.categories = []

    async def create_category(self, name):
        class MockCategory:
            def __init__(self, name):
                self.name = name
        category = MockCategory(name)
        self.categories.append(category)
        return category

    async def create_text_channel(self, name, category=None, overwrites=None, topic=None):
        class MockChannel:
            def __init__(self, id, name):
                self.id = id
                self.name = name
                self.mention = f"<#{self.id}>"

            async def send(self, content=None, embed=None, view=None):
                logger.info(f"[MockChannel (from create_text_channel)] send: {content if content else embed}")
                if view:
                    logger.info(f"[MockChannel (from create_text_channel)] with view: {view.__class__.__name__}")
        return MockChannel(id=99999, name=name)

    async def send(self, content=None, embed=None, view=None):
        logger.info(f"[MockChannel] send: {content if content else embed}")
        if view:
            logger.info(f"[MockChannel] with view: {view.__class__.__name__}")

class MockTextChannel:
    def __init__(self, id, name="test-channel"):
        self.id = id
        self.name = name

class MockMessage:
    def __init__(self, content, author, channel, guild):
        self.content = content
        self.author = author
        self.channel = channel
        self.guild = guild
        self.id = 123456789012345678 # Dummy message ID

class MockInteraction(discord.Interaction):
    def __init__(self, client, user, channel, guild, command_name=None):
        self._client = client
        self._user = user
        self._channel = channel
        self._guild = guild

        self.response = MockInteractionResponse()
        self.data = {"name": command_name, "options": []} if command_name else {}




    async def _dummy_callback(self): pass

    @property
    def followup(self):
        return self.response

    @property
    def client(self):
        return self._client

    @property
    def user(self):
        return self._user

    @property
    def channel(self):
        return self._channel

    @property
    def guild(self):
        return self._guild

    async def response_send_message(self, content, ephemeral=False, view=None):
        logger.info(f"[MockInteractionResponse] send_message: {content}")
        if view:
            logger.info(f"[MockInteractionResponse] with view: {view.__class__.__name__}")
            # Simulate view interaction if needed for deeper testing

    async def response_defer(self, ephemeral=False, thinking=True):
        logger.info(f"[MockInteractionResponse] defer (thinking={thinking})")

    async def follow_up_send_message(self, content, ephemeral=False, view=None):
        logger.info(f"[MockInteractionResponse] follow_up_send_message: {content}")
        if view:
            logger.info(f"[MockInteractionResponse] with view: {view.__class__.__name__}")

class MockInteractionResponse:
    def __init__(self):
        self._is_done = False

    async def send_message(self, content=None, ephemeral=False, view=None, embed=None):
        logger.info(f"[MockInteractionResponse] send_message: {content if content else embed}")
        self._is_done = True
        if view:
            logger.info(f"[MockInteractionResponse] with view: {view.__class__.__name__}")

    async def defer(self, ephemeral=False, thinking=True):
        logger.info(f"[MockInteractionResponse] defer (thinking={thinking})")
        self._is_done = True

    async def follow_up_send_message(self, content=None, ephemeral=False, view=None, embed=None):
        logger.info(f"[MockInteractionResponse] follow_up_send_message: {content if content else embed}")
        if view:
            logger.info(f"[MockInteractionResponse] with view: {view.__class__.__name__}")

    async def send(self, content=None, ephemeral=False, view=None, embed=None):
        # Alias for follow_up_send_message for compatibility with interaction.followup.send
        await self.follow_up_send_message(content, ephemeral, view, embed)



    @property
    def is_done(self):
        return self._is_done

# Mock Bot class to provide necessary attributes
class MockBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.default())
        self.db_manager = DatabaseManager()
        master_key = os.getenv("ENCRYPTION_KEY") # Read from env, not generate
        self.encryption_manager = EncryptionManager(master_key)
        self.user_repo = UserRepository
        self.api_key_repo = APIKeyRepository
        self.session_repo = SessionRepository
        self.requirement_repo = RequirementRepository
        self.task_repo = TaskRepository

        self.i18n = i18n

        self._connection = self._get_mock_connection() # Add a mock connection


    def _get_mock_connection(self):
        # A minimal mock for discord.Client._connection
        class MockConnection:
            def __init__(self, client):
                self.user = client.user

        return MockConnection(self)

    async def setup_hook(self):
        await self.db_manager.initialize()
        logger.info("MockBot: Database initialized.")

    async def get_user_info(self, discord_user_id):
        # Simulate fetching user info from DB or creating if not exists
        async with self.db_manager.get_session() as session:
            user = await self.user_repo.get_user_by_discord_id(session, discord_user_id)
        if not user:
            async with self.db_manager.get_session() as session:
                user = await self.user_repo.create_user(session,
                discord_user_id=discord_user_id,
                discord_username=f"test_user_{discord_user_id}",
                discord_discriminator="0000"
            )
        return user

    async def get_api_key(self, user_id):
        # Simulate fetching API key
        async with self.db_manager.get_session() as session:
            api_key_obj = await self.api_key_repo.get_active_api_key(session, user_id)
        if api_key_obj:
            return self.encryption_manager.decrypt(api_key_obj.encrypted_key)
        # For testing, we assume the API key is already set in the environment
        return os.getenv("OPENROUTER_API_KEY")

    async def get_session_by_channel(self, guild_id, channel_id):
        async with self.db_manager.get_session() as session:
            return await self.session_repo.get_active_session_by_channel(session, guild_id, channel_id)

    async def get_session_by_user(self, user_id):
        async with self.db_manager.get_session() as session:
            return await self.session_repo.get_active_session_by_user(session, user_id)

    async def get_session_by_uuid(self, session_uuid):
        async with self.db_manager.get_session() as session:
            return await self.session_repo.get_session_by_uuid(session, session_uuid)

    async def get_requirement_by_id(self, requirement_id):
        async with self.db_manager.get_session() as session:
            return await self.requirement_repo.get_requirement(session, requirement_id)

    async def get_tasks_by_requirement(self, requirement_id):
        async with self.db_manager.get_session() as session:
            return await self.task_repo.get_tasks_by_requirement(session, requirement_id)

async def run_test_flow():
    # Validate configuration
    if not Config.validate():
        logger.error("Configuration validation failed. Exiting.")
        return

    bot = MockBot()
    await bot.setup_hook()

    # Clean up any lingering active sessions from previous runs
    async with bot.db_manager.get_session() as session:
        await bot.session_repo.deactivate_all_sessions(session)

    test_user = MockUser(id=12345, name="testuser")

    # Create a dummy API key for the test user
    async with bot.db_manager.get_session() as session:
        user_db = await bot.user_repo.get_or_create_user(session, str(test_user.id), test_user.name)
        await bot.api_key_repo.set_api_key(session, user_db.id, bot.encryption_manager.encrypt(os.getenv("OPENROUTER_API_KEY")), "OpenRouter")
    test_guild = MockGuild(id=67890)
    test_channel = MockTextChannel(id=112233)

    # Simulate /coding start command
    logger.info("\n--- Simulating /coding start ---")
    interaction_start = MockInteraction(bot, test_user, test_channel, test_guild, command_name="coding")
    interaction_start.data["options"] = [
        {"name": "start", "type": 1, "options": [
            {"name": "project_name", "value": "Test Project"}
        ]}
    ]

    # Manually call the _handle_start method from cogs/coding.py
    # This requires importing the cog directly and calling its method
    
    from cogs.coding import CodingPanelView
    coding_panel_view = CodingPanelView(bot) # Pass the mock bot
    
    # Mock the interaction.response.send_message for the initial response
    async def mock_send_message(content, ephemeral=False, view=None):
        logger.info(f"[Mocked send_message] {content}")
        if view:
            logger.info(f"[Mocked send_message] View attached: {view.__class__.__name__}")
            if isinstance(view, RequirementApprovalView):
                # Simulate user approving the requirement
                logger.info("Simulating user approval of requirement...")
                mock_approval_interaction = MockInteraction(bot, test_user, test_channel, test_guild)
                mock_approval_interaction.message = MockMessage("", test_user, test_channel, test_guild) # Needed for view callbacks
                mock_approval_interaction.response = MockInteractionResponse()
                await view.approve.callback(view, mock_approval_interaction) # Call the approve button callback

    interaction_start.response.send_message = mock_send_message.__get__(interaction_start.response, MockInteractionResponse)

    await coding_panel_view._handle_start(interaction_start, "en-US") # Pass a dummy language for testing

    # After the flow, check database for created entries
    logger.info("\n--- Verifying Database Entries ---")

    try:
        async with bot.db_manager.get_session() as session:
            user = await bot.user_repo.get_user_by_discord_id(session, test_user.id)
        if user:
            logger.info(f"Found User: {user.discord_username} (ID: {user.id})")
            async with bot.db_manager.get_session() as session:
                session = await bot.session_repo.get_active_session(session, user.id)
            if session:
                logger.info(f"Found Session: {session.session_uuid} (Project: {session.project_name})")
                async with bot.db_manager.get_session() as db_session_for_verification:
                    # Retrieve the actual Session object to get its ID
                    session_obj = await bot.session_repo.get_session_by_uuid(db_session_for_verification, session.session_uuid)
                    if session_obj:
                        requirements = await bot.requirement_repo.get_requirements_by_session(db_session_for_verification, session_obj.id)
                        if requirements:
                            logger.info(f"Found {len(requirements)} Requirements for session {session_obj.id}")
                            for req in requirements:
                                logger.info(f"  Requirement {req.id} (Status: {req.status}): {req.json_data}")
                                async with bot.db_manager.get_session() as session:
                                    tasks = await bot.task_repo.get_tasks_by_requirement(session, req.id)
                                if tasks:
                                    logger.info(f"    Found {len(tasks)} Tasks for requirement {req.id}")
                                    for task in tasks:
                                        logger.info(f"      Task {task.task_id} (Type: {task.type}, Role: {task.role}, Status: {task.status})")
                                else:
                                    logger.warning(f"    No Tasks found for requirement {req.id}")
                    else:
                        logger.warning(f"No Requirements found for session {session_obj.id}")
            else:
                logger.warning("No active Session found for test user.")
        else:
            logger.warning("No User found for test_user.")
    finally:
        pass # Sessions are managed by async with blocks

    logger.info("\n--- Test Flow Completed ---")

if __name__ == "__main__":
    asyncio.run(run_test_flow())
