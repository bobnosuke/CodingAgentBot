import unittest
import asyncio
import os
import sys
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from modules.database.models import Base, User
from modules.database.repository import UserRepository

class TestRepository(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Use in-memory SQLite for testing
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        self.async_session = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def test_user_creation(self):
        async with self.async_session() as session:
            user = await UserRepository.get_or_create_user(
                session, "123456789", "testuser", "0001"
            )
            self.assertEqual(user.discord_username, "testuser")
            
            # Get same user
            user2 = await UserRepository.get_or_create_user(
                session, "123456789", "testuser", "0001"
            )
            self.assertEqual(user.id, user2.id)

    async def test_get_user_by_discord_id(self):
        async with self.async_session() as session:
            await UserRepository.get_or_create_user(
                session, "987654321", "anotheruser"
            )
            
            user = await UserRepository.get_user_by_discord_id(session, "987654321")
            self.assertIsNotNone(user)
            self.assertEqual(user.discord_username, "anotheruser")

if __name__ == '__main__':
    unittest.main()
