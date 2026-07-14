"""
Session management for CoderAgent
Handles coding session lifecycle and room management
"""
import uuid
import discord
from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from logger import setup_logger
from ..database.repository import SessionRepository, UserRepository

logger = setup_logger(__name__)


class SessionManager:
    """Manages coding sessions and CodingRoom creation"""
    
    def __init__(self, bot: discord.ext.commands.Bot):
        """
        Initialize session manager
        
        Args:
            bot: Discord bot instance
        """
        self.bot = bot
        self.active_sessions = {}  # In-memory cache for active sessions
    
    async def create_session(
        self,
        db_session: AsyncSession,
        discord_user: discord.User,
        guild: discord.Guild,
        project_name: str = None
    ) -> tuple[str, discord.TextChannel]:
        """
        Create a new coding session with CodingRoom
        
        Args:
            db_session: Database session
            discord_user: Discord user
            guild: Discord guild
            project_name: Optional project name
        
        Returns:
            Tuple of (session_uuid, coding_room_channel)
        """
        try:
            # Generate session UUID
            session_uuid = str(uuid.uuid4())
            
            # Get or create user in database
            user = await UserRepository.get_or_create_user(
                db_session,
                str(discord_user.id),
                discord_user.name,
                discord_user.discriminator
            )
            
            # Create CodingRoom channel
            coding_room = await self._create_coding_room(
                guild,
                discord_user,
                project_name or f"Session-{session_uuid[:8]}"
            )
            
            # Create session in database
            db_session_obj = await SessionRepository.create_session(
                db_session,
                session_uuid,
                user.id,
                str(guild.id),
                str(coding_room.id),
                project_name
            )
            
            # Cache session
            self.active_sessions[session_uuid] = {
                "user_id": user.id,
                "discord_user_id": str(discord_user.id),
                "guild_id": str(guild.id),
                "channel_id": str(coding_room.id),
                "created_at": datetime.utcnow(),
                "db_session_id": db_session_obj.id
            }
            
            logger.info(f"Created session {session_uuid} for {discord_user.name}")
            return session_uuid, coding_room
        
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            raise
    
    async def _create_coding_room(
        self,
        guild: discord.Guild,
        user: discord.User,
        room_name: str
    ) -> discord.TextChannel:
        """
        Create a private CodingRoom channel
        
        Args:
            guild: Discord guild
            user: Discord user
            room_name: Room name
        
        Returns:
            Created text channel
        """
        try:
            # Create channel with restricted permissions
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                user: discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True
                ),
                self.bot.user: discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    manage_messages=True
                )
            }
            
            # Create category for organization
            category_name = "🤖-coding-sessions"
            category = None
            
            for cat in guild.categories:
                if cat.name == category_name:
                    category = cat
                    break
            
            if not category:
                category = await guild.create_category(category_name)
            
            # Create channel in category
            channel = await guild.create_text_channel(
                name=room_name.lower().replace(" ", "-")[:100],
                category=category,
                overwrites=overwrites,
                topic=f"Coding session for {user.name}"
            )
            
            logger.info(f"Created CodingRoom channel: {channel.name} ({channel.id})")
            return channel
        
        except Exception as e:
            logger.error(f"Failed to create coding room: {e}")
            raise
    
    async def close_session(
        self,
        db_session: AsyncSession,
        session_uuid: str,
        delete_channel: bool = True
    ) -> None:
        """
        Close a coding session
        
        Args:
            db_session: Database session
            session_uuid: Session UUID
            delete_channel: Whether to delete the CodingRoom channel
        """
        try:
            if session_uuid not in self.active_sessions:
                logger.warning(f"Session {session_uuid} not found in cache")
                return
            
            session_info = self.active_sessions[session_uuid]
            
            # Close session in database
            await SessionRepository.close_session(db_session, session_info["db_session_id"])
            
            # Delete CodingRoom channel if requested
            if delete_channel:
                try:
                    channel = self.bot.get_channel(int(session_info["channel_id"]))
                    if channel:
                        await channel.delete()
                        logger.info(f"Deleted CodingRoom channel: {channel.name}")
                except Exception as e:
                    logger.error(f"Failed to delete channel: {e}")
            
            # Remove from cache
            del self.active_sessions[session_uuid]
            
            logger.info(f"Closed session {session_uuid}")
        
        except Exception as e:
            logger.error(f"Failed to close session: {e}")
            raise
    
    def get_session(self, session_uuid: str) -> Optional[dict]:
        """
        Get session information from cache
        
        Args:
            session_uuid: Session UUID
        
        Returns:
            Session info dict or None
        """
        return self.active_sessions.get(session_uuid)
    
    def get_user_active_session(self, discord_user_id: str) -> Optional[str]:
        """
        Get active session UUID for a user
        
        Args:
            discord_user_id: Discord user ID
        
        Returns:
            Session UUID or None
        """
        for session_uuid, info in self.active_sessions.items():
            if info["discord_user_id"] == discord_user_id:
                return session_uuid
        
        return None
