"""
Database connection and session management for CoderAgent
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import event
from config import Config
from logger import setup_logger
from .models import Base

logger = setup_logger(__name__)


class DatabaseManager:
    """Manages database connections and sessions"""
    
    def __init__(self, database_url: str = None):
        """
        Initialize database manager
        
        Args:
            database_url: Database URL (defaults to config)
        """
        self.database_url = database_url or Config.DATABASE_URL
        self.engine = None
        self.async_session_maker = None
    
    async def initialize(self) -> None:
        """Initialize database engine and create tables"""
        try:
            # Create async engine
            self.engine = create_async_engine(
                self.database_url,
                echo=False,
                future=True
            )
            
            # Create session factory
            self.async_session_maker = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            # Create all tables
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            
            logger.info(f"✅ Database initialized: {self.database_url}")
        
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            raise
    
    async def close(self) -> None:
        """Close database connections"""
        if self.engine:
            await self.engine.dispose()
            logger.info("Database connections closed")
    
    def get_session(self) -> AsyncSession:
        """
        Get a new database session
        
        Returns:
            AsyncSession instance
        """
        if not self.async_session_maker:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        
        return self.async_session_maker()
    
    async def health_check(self) -> bool:
        """
        Check database health
        
        Returns:
            True if database is accessible, False otherwise
        """
        try:
            async with self.get_session() as session:
                await session.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False


# Global database manager instance
_db_manager = None


async def get_db_manager(database_url: str = None) -> DatabaseManager:
    """
    Get or create global database manager instance
    
    Args:
        database_url: Database URL (optional)
    
    Returns:
        DatabaseManager instance
    """
    global _db_manager
    
    if _db_manager is None:
        _db_manager = DatabaseManager(database_url)
        await _db_manager.initialize()
    
    return _db_manager
