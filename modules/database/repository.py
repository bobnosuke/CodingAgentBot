"""
Repository layer for database operations
Provides abstraction for database access
"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from logger import setup_logger
from .models import User, APIKey, Session, Message, Project, UsageLog, SystemLog

logger = setup_logger(__name__)


class UserRepository:
    """Repository for User operations"""
    
    @staticmethod
    async def get_or_create_user(
        session: AsyncSession,
        discord_user_id: str,
        discord_username: str,
        discord_discriminator: str = None
    ) -> User:
        """Get existing user or create new one"""
        try:
            # Try to get existing user
            stmt = select(User).where(User.discord_user_id == discord_user_id)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()
            
            if user:
                return user
            
            # Create new user
            user = User(
                discord_user_id=discord_user_id,
                discord_username=discord_username,
                discord_discriminator=discord_discriminator
            )
            session.add(user)
            await session.commit()
            
            logger.info(f"Created new user: {discord_user_id}")
            return user
        
        except Exception as e:
            logger.error(f"Error in get_or_create_user: {e}")
            await session.rollback()
            raise
    
    @staticmethod
    async def get_user_by_discord_id(session: AsyncSession, discord_user_id: str) -> Optional[User]:
        """Get user by Discord ID"""
        try:
            stmt = select(User).where(User.discord_user_id == discord_user_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error in get_user_by_discord_id: {e}")
            raise
    
    @staticmethod
    async def count_users(session: AsyncSession) -> int:
        """Count total users"""
        try:
            from sqlalchemy import func
            stmt = select(func.count(User.id))
            result = await session.execute(stmt)
            return result.scalar() or 0
        except Exception as e:
            logger.error(f"Error in count_users: {e}")
            raise


class APIKeyRepository:
    """Repository for APIKey operations"""
    
    @staticmethod
    async def create_api_key(
        session: AsyncSession,
        user_id: int,
        encrypted_key: str,
        key_name: str = "Default"
    ) -> APIKey:
        """Create new API key"""
        try:
            api_key = APIKey(
                user_id=user_id,
                encrypted_key=encrypted_key,
                key_name=key_name
            )
            session.add(api_key)
            await session.commit()
            
            logger.info(f"Created API key for user {user_id}")
            return api_key
        
        except Exception as e:
            logger.error(f"Error in create_api_key: {e}")
            await session.rollback()
            raise
    
    @staticmethod
    async def get_active_api_key(session: AsyncSession, user_id: int) -> Optional[APIKey]:
        """Get active API key for user"""
        try:
            stmt = select(APIKey).where(
                (APIKey.user_id == user_id) & (APIKey.is_active == True)
            ).order_by(APIKey.created_at.desc())
            
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
        
        except Exception as e:
            logger.error(f"Error in get_active_api_key: {e}")
            raise
    
    @staticmethod
    async def update_last_used(session: AsyncSession, api_key_id: int) -> None:
        """Update last used timestamp"""
        try:
            from datetime import datetime
            stmt = update(APIKey).where(APIKey.id == api_key_id).values(
                last_used_at=datetime.utcnow()
            )
            await session.execute(stmt)
            await session.commit()
        
        except Exception as e:
            logger.error(f"Error in update_last_used: {e}")
            await session.rollback()
            raise

    @staticmethod
    async def set_api_key(
        session: AsyncSession,
        user_id: int,
        encrypted_key: str,
        key_name: str = "Default"
    ) -> APIKey:
        """Set API key for user (Update if exists, otherwise create)"""
        try:
            # Check for existing active key
            existing_key = await APIKeyRepository.get_active_api_key(session, user_id)
            
            if existing_key:
                # Update existing key
                existing_key.encrypted_key = encrypted_key
                existing_key.key_name = key_name
                existing_key.updated_at = datetime.utcnow()
                await session.commit()
                logger.info(f"Updated API key for user {user_id}")
                return existing_key
            else:
                # Create new key
                return await APIKeyRepository.create_api_key(session, user_id, encrypted_key, key_name)
        
        except Exception as e:
            logger.error(f"Error in set_api_key: {e}")
            await session.rollback()
            raise


class SessionRepository:
    """Repository for Session operations"""
    
    @staticmethod
    async def create_session(
        session: AsyncSession,
        session_uuid: str,
        user_id: int,
        guild_id: str,
        channel_id: str = None,
        project_name: str = None
    ) -> Session:
        """Create new coding session"""
        try:
            coding_session = Session(
                session_uuid=session_uuid,
                user_id=user_id,
                guild_id=guild_id,
                channel_id=channel_id,
                project_name=project_name
            )
            session.add(coding_session)
            await session.commit()
            
            logger.info(f"Created session {session_uuid} for user {user_id}")
            return coding_session
        
        except Exception as e:
            logger.error(f"Error in create_session: {e}")
            await session.rollback()
            raise
    
    @staticmethod
    async def get_active_session(session: AsyncSession, user_id: int) -> Optional[Session]:
        """Get active session for user"""
        try:
            stmt = select(Session).where(
                (Session.user_id == user_id) & (Session.is_active == True)
            ).order_by(Session.created_at.desc())
            
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
        
        except Exception as e:
            logger.error(f"Error in get_active_session: {e}")
            raise
    
    @staticmethod
    async def close_session(session: AsyncSession, session_id: int) -> None:
        """Close a session"""
        try:
            stmt = update(Session).where(Session.id == session_id).values(is_active=False)
            await session.execute(stmt)
            await session.commit()
            
            logger.info(f"Closed session {session_id}")
        
        except Exception as e:
            logger.error(f"Error in close_session: {e}")
            await session.rollback()
            raise
    
    @staticmethod
    async def count_sessions(session: AsyncSession) -> int:
        """Count total sessions"""
        try:
            from sqlalchemy import func
            stmt = select(func.count(Session.id))
            result = await session.execute(stmt)
            return result.scalar() or 0
        except Exception as e:
            logger.error(f"Error in count_sessions: {e}")
            raise
    
    @staticmethod
    async def count_active_sessions(session: AsyncSession) -> int:
        """Count active sessions"""
        try:
            from sqlalchemy import func
            stmt = select(func.count(Session.id)).where(Session.is_active == True)
            result = await session.execute(stmt)
            return result.scalar() or 0
        except Exception as e:
            logger.error(f"Error in count_active_sessions: {e}")
            raise

    @staticmethod
    async def count_user_sessions(session: AsyncSession, user_id: int) -> int:
        """Count total sessions for a specific user"""
        try:
            from sqlalchemy import func
            stmt = select(func.count(Session.id)).where(Session.user_id == user_id)
            result = await session.execute(stmt)
            return result.scalar() or 0
        except Exception as e:
            logger.error(f"Error in count_user_sessions: {e}")
            raise


class MessageRepository:
    """Repository for Message operations"""
    
    @staticmethod
    async def add_message(
        session: AsyncSession,
        session_id: int,
        role: str,
        content: str,
        token_input: int = 0,
        token_output: int = 0
    ) -> Message:
        """Add message to session"""
        try:
            message = Message(
                session_id=session_id,
                role=role,
                content=content,
                token_input=token_input,
                token_output=token_output
            )
            session.add(message)
            await session.commit()
            
            return message
        
        except Exception as e:
            logger.error(f"Error in add_message: {e}")
            await session.rollback()
            raise
    
    @staticmethod
    async def count_messages(session: AsyncSession) -> int:
        """Count total messages"""
        try:
            from sqlalchemy import func
            stmt = select(func.count(Message.id))
            result = await session.execute(stmt)
            return result.scalar() or 0
        except Exception as e:
            logger.error(f"Error in count_messages: {e}")
            raise
    
    @staticmethod
    async def get_session_messages(session: AsyncSession, session_id: int) -> List[Message]:
        """Get all messages for a session"""
        try:
            stmt = select(Message).where(Message.session_id == session_id).order_by(Message.created_at)
            result = await session.execute(stmt)
            return result.scalars().all()
        
        except Exception as e:
            logger.error(f"Error in get_session_messages: {e}")
            raise


class SystemLogRepository:
    """Repository for SystemLog operations"""
    
    @staticmethod
    async def log_event(
        session: AsyncSession,
        event_type: str,
        message: str,
        severity: str = "INFO",
        user_id: str = None,
        guild_id: str = None
    ) -> SystemLog:
        """Log system event"""
        try:
            log = SystemLog(
                event_type=event_type,
                message=message,
                severity=severity,
                user_id=user_id,
                guild_id=guild_id
            )
            session.add(log)
            await session.commit()
            
            return log
        
        except Exception as e:
            logger.error(f"Error in log_event: {e}")
            await session.rollback()
            raise


class UsageLogRepository:
    """Repository for UsageLog operations"""
    
    @staticmethod
    async def log_usage(
        session: AsyncSession,
        user_id: int,
        model: str,
        token_input: int = 0,
        token_output: int = 0,
        estimated_cost: float = 0.0
    ) -> UsageLog:
        """Log AI usage"""
        try:
            log = UsageLog(
                user_id=user_id,
                model=model,
                token_input=token_input,
                token_output=token_output,
                estimated_cost=estimated_cost
            )
            session.add(log)
            await session.commit()
            return log
        except Exception as e:
            logger.error(f"Error in log_usage: {e}")
            await session.rollback()
            raise

    @staticmethod
    async def get_daily_usage_count(session: AsyncSession, user_id: int) -> int:
        """Get message count for today for a user"""
        try:
            from datetime import datetime, time
            today_start = datetime.combine(datetime.utcnow().date(), time.min)
            
            stmt = select(UsageLog).where(
                (UsageLog.user_id == user_id) & 
                (UsageLog.created_at >= today_start)
            )
            result = await session.execute(stmt)
            return len(result.scalars().all())
        except Exception as e:
            logger.error(f"Error in get_daily_usage_count: {e}")
            raise
