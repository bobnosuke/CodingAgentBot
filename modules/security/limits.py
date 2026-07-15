"""
Usage limits and Rate limiting for CoderAgent
Implements:
- Daily message limit (50 messages/day)
- Rate limit (1 message per 8 seconds)
"""
import time
from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from modules.database.repository import UsageLogRepository, UserRepository
from logger import setup_logger

logger = setup_logger(__name__)

# In-memory cache for Rate Limiting (Last command timestamp per user)
# {user_id: last_timestamp}
_last_usage_cache: Dict[str, float] = {}

class UsageLimitManager:
    """Manages user usage limits and rate limiting"""
    
    DAILY_LIMIT = 50
    RATE_LIMIT_SECONDS = 8.0

    @staticmethod
    async def check_limits(session: AsyncSession, discord_user_id: str) -> Tuple[bool, Optional[str]]:
        """
        Check if the user has exceeded any limits.
        Returns: (is_allowed, error_message)
        """
        # 1. Rate Limit Check (In-memory)
        now = time.time()
        if discord_user_id in _last_usage_cache:
            elapsed = now - _last_usage_cache[discord_user_id]
            if elapsed < UsageLimitManager.RATE_LIMIT_SECONDS:
                wait_time = int(UsageLimitManager.RATE_LIMIT_SECONDS - elapsed)
                return False, f"⚠️ 送信間隔が短すぎます。あと {wait_time} 秒お待ちください。"

        # 2. Daily Usage Limit Check (Database)
        try:
            user = await UserRepository.get_user_by_discord_id(session, discord_user_id)
            if not user:
                # User not found in DB yet, will be created, so allow first use
                return True, None
            
            daily_count = await UsageLogRepository.get_daily_usage_count(session, user.id)
            if daily_count >= UsageLimitManager.DAILY_LIMIT:
                return False, f"❌ 本日の利用制限（{UsageLimitManager.DAILY_LIMIT}回）に達しました。明日またご利用ください。"
            
            # Update last usage timestamp
            _last_usage_cache[discord_user_id] = now
            return True, None
            
        except Exception as e:
            logger.error(f"Error checking limits for {discord_user_id}: {e}")
            # In case of DB error, allow but log
            return True, None

    @staticmethod
    def get_remaining_wait_time(discord_user_id: str) -> float:
        """Get remaining seconds for rate limit"""
        if discord_user_id not in _last_usage_cache:
            return 0.0
        elapsed = time.time() - _last_usage_cache[discord_user_id]
        return max(0.0, UsageLimitManager.RATE_LIMIT_SECONDS - elapsed)
