"""
Permission management for CoderAgent
Handles user authorization and role-based access control
"""
import discord
from discord.ext import commands
from enum import Enum
from logger import setup_logger
from config import Config

logger = setup_logger(__name__)


class PermissionLevel(Enum):
    """Permission levels for CoderAgent"""
    USER = 1
    ADMIN = 2
    BOT_OWNER = 3


class PermissionManager:
    """Manages user permissions and authorization"""
    
    @staticmethod
    def get_permission_level(user: discord.User, guild: discord.Guild = None) -> PermissionLevel:
        """
        Get permission level for a user
        
        Args:
            user: Discord user
            guild: Discord guild (optional, for admin check)
        
        Returns:
            PermissionLevel enum value
        """
        # Check if bot owner
        if str(user.id) == Config.BOT_OWNER_ID:
            return PermissionLevel.BOT_OWNER
        
        # Check if guild admin
        if guild and isinstance(user, discord.Member):
            if user.guild_permissions.administrator:
                return PermissionLevel.ADMIN
        
        # Default to user level
        return PermissionLevel.USER
    
    @staticmethod
    def has_permission(
        user: discord.User,
        required_level: PermissionLevel,
        guild: discord.Guild = None
    ) -> bool:
        """
        Check if user has required permission level
        
        Args:
            user: Discord user
            required_level: Required permission level
            guild: Discord guild (optional)
        
        Returns:
            True if user has permission, False otherwise
        """
        user_level = PermissionManager.get_permission_level(user, guild)
        return user_level.value >= required_level.value


def require_permission(required_level: PermissionLevel):
    """
    Decorator for commands requiring specific permission level
    
    Args:
        required_level: Required permission level
    """
    async def predicate(ctx: commands.Context) -> bool:
        has_perm = PermissionManager.has_permission(
            ctx.author,
            required_level,
            ctx.guild
        )
        
        if not has_perm:
            logger.warning(
                f"Permission denied for {ctx.author} ({ctx.author.id}) "
                f"in {ctx.guild}: required {required_level.name}"
            )
            await ctx.send(
                f"❌ You don't have permission to use this command. "
                f"Required level: {required_level.name}"
            )
            return False
        
        return True
    
    return commands.check(predicate)


# Convenience decorators
def user_command(func):
    """Decorator for user-level commands"""
    return require_permission(PermissionLevel.USER)(func)


def admin_command(func):
    """Decorator for admin-level commands"""
    return require_permission(PermissionLevel.ADMIN)(func)


def owner_command(func):
    """Decorator for bot owner-level commands"""
    return require_permission(PermissionLevel.BOT_OWNER)(func)
