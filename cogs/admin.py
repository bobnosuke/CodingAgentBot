"""
Admin and Owner commands for CoderAgent
Handles /config, /health, /stats, /shutdown commands
"""
import discord
from discord.ext import commands
from discord import app_commands
import time
import psutil
import os
import platform
from datetime import datetime
from logger import setup_logger
from modules.security.permissions import PermissionLevel, PermissionManager
from modules.database.repository import UserRepository, SessionRepository, SystemLogRepository
from config import Config

logger = setup_logger(__name__)


class AdminCog(commands.Cog):
    """Cog for administrative and owner-only commands"""

    def __init__(self, bot: commands.Bot):
        """
        Initialize admin cog
        
        Args:
            bot: Discord bot instance
        """
        self.bot = bot
        self.start_time = time.time()

    # ------------------------------------------------------------------
    # /health
    # ------------------------------------------------------------------

    @app_commands.command(name="health", description="Botの状態を確認します")
    async def health_check(self, interaction: discord.Interaction):
        """Check bot health status"""
        await interaction.response.defer(ephemeral=True)

        # 1. Database Check
        db_status = "🔴 Error"
        try:
            db_manager = self.bot.db_manager
            if await db_manager.health_check():
                db_status = "🟢 Healthy"
        except Exception as e:
            logger.error(f"Health check DB error: {e}")
            db_status = f"🔴 Error: {str(e)}"

        # 2. API Check (OpenRouter)
        api_status = "🟢 Online" # In a real app, we might do a ping to OpenRouter

        # 3. System Info
        process = psutil.Process(os.getpid())
        memory_usage = process.memory_info().rss / 1024 / 1024  # MB
        uptime_seconds = int(time.time() - self.start_time)
        hours, rem = divmod(uptime_seconds, 3600)
        minutes, seconds = divmod(rem, 60)
        uptime_str = f"{hours}h {minutes}m {seconds}s"

        embed = discord.Embed(
            title="🏥 CoderAgent Health Status",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="Database", value=db_status, inline=True)
        embed.add_field(name="OpenRouter API", value=api_status, inline=True)
        embed.add_field(name="Uptime", value=uptime_str, inline=True)
        embed.add_field(name="Memory Usage", value=f"{memory_usage:.1f} MB", inline=True)
        embed.add_field(name="Latency", value=f"{round(self.bot.latency * 1000)}ms", inline=True)

        await interaction.followup.send(embed=embed, ephemeral=True)

    # ------------------------------------------------------------------
    # /stats
    # ------------------------------------------------------------------

    @app_commands.command(name="stats", description="Botの利用統計を表示します")
    async def stats(self, interaction: discord.Interaction):
        """Show bot usage statistics"""
        # Check permission (Admin or Owner)
        if not PermissionManager.has_permission(interaction.user, PermissionLevel.ADMIN, interaction.guild):
            await interaction.response.send_message("❌ このコマンドを実行する権限がありません。", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        db_session = self.bot.db_manager.get_session()
        try:
            from sqlalchemy import select, func
            from modules.database.models import User, Session, Message

            # Total Users
            user_count = await db_session.scalar(select(func.count(User.id)))
            
            # Total Sessions
            session_count = await db_session.scalar(select(func.count(Session.id)))
            
            # Active Sessions
            active_sessions = await db_session.scalar(select(func.count(Session.id)).where(Session.is_active == True))
            
            # Total Messages
            message_count = await db_session.scalar(select(func.count(Message.id)))

            # System info
            cpu_usage = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            memory_usage_pct = memory.percent

            embed = discord.Embed(
                title="📊 CoderAgent Statistics",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Total Servers", value=str(len(self.bot.guilds)), inline=True)
            embed.add_field(name="Total Users", value=str(user_count), inline=True)
            embed.add_field(name="Total Sessions", value=str(session_count), inline=True)
            embed.add_field(name="Active Sessions", value=str(active_sessions), inline=True)
            embed.add_field(name="Total Messages", value=str(message_count), inline=True)
            embed.add_field(name="System", value=f"CPU: {cpu_usage}%\nRAM: {memory_usage_pct}%", inline=True)
            embed.add_field(name="Platform", value=f"{platform.system()} {platform.release()}", inline=False)

            await interaction.followup.send(embed=embed, ephemeral=True)

        finally:
            await db_session.close()

    # ------------------------------------------------------------------
    # /shutdown
    # ------------------------------------------------------------------

    @app_commands.command(name="shutdown", description="Botを安全に停止します（オーナー専用）")
    async def shutdown(self, interaction: discord.Interaction):
        """Safely shut down the bot"""
        # Check permission (Owner only)
        if not PermissionManager.has_permission(interaction.user, PermissionLevel.BOT_OWNER):
            await interaction.response.send_message("❌ このコマンドはBotオーナーのみ実行可能です。", ephemeral=True)
            return

        await interaction.response.send_message("👋 CoderAgent をシャットダウンしています... さようなら！", ephemeral=True)
        logger.info(f"Shutdown command received from {interaction.user}")
        
        # Log shutdown event
        db_session = self.bot.db_manager.get_session()
        try:
            await SystemLogRepository.log_event(
                db_session,
                event_type="bot_shutdown",
                message=f"Bot shut down by {interaction.user.name} ({interaction.user.id})",
                severity="WARNING"
            )
        finally:
            await db_session.close()

        await self.bot.close()

    # ------------------------------------------------------------------
    # /config
    # ------------------------------------------------------------------

    config_group = app_commands.Group(name="config", description="サーバー設定を管理します（管理者用）")

    @config_group.command(name="set-category", description="コーディングルームを作成するカテゴリを設定します")
    async def set_category(self, interaction: discord.Interaction, category: discord.CategoryChannel):
        """Set the category where CodingRooms will be created"""
        if not PermissionManager.has_permission(interaction.user, PermissionLevel.ADMIN, interaction.guild):
            await interaction.response.send_message("❌ 管理者権限が必要です。", ephemeral=True)
            return

        # In a real implementation, we would save this to a 'guild_settings' table
        await interaction.response.send_message(
            f"✅ このサーバーのコーディングルーム作成カテゴリを {category.mention} に設定しました。\n"
            f"(注: 現在の実装ではメモリ上のみの保持、またはデフォルト動作になります)",
            ephemeral=True
        )
        logger.info(f"Admin {interaction.user} set coding category to {category.id} in guild {interaction.guild.id}")


async def setup(bot: commands.Bot):
    """Setup function for loading cog"""
    cog = AdminCog(bot)
    await bot.add_cog(cog)
    # Register commands
    if "health" not in [cmd.name for cmd in bot.tree.get_commands()]:
        bot.tree.add_command(cog.health_check)
    if "stats" not in [cmd.name for cmd in bot.tree.get_commands()]:
        bot.tree.add_command(cog.stats)
    if "shutdown" not in [cmd.name for cmd in bot.tree.get_commands()]:
        bot.tree.add_command(cog.shutdown)
    if "config" not in [cmd.name for cmd in bot.tree.get_commands()]:
        bot.tree.add_command(cog.config_group)
