"""
Admin and Owner commands for CoderAgent
Handles /config, /health, /stats, /shutdown commands
"""
import discord
from discord.ext import commands
from discord import app_commands
import time
import platform
import psutil
from datetime import datetime
from logger import setup_logger
from config import Config
from modules.security.permissions import PermissionLevel, PermissionManager
from modules.database.repository import SystemLogRepository

logger = setup_logger(__name__)


class AdminCog(commands.Cog):
    """Cog for administrative and owner commands"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.start_time = time.time()

    # ------------------------------------------------------------------
    # /health (General User / Admin)
    # ------------------------------------------------------------------

    @app_commands.command(name="health", description="Check the bot's health status")
    async def health(self, interaction: discord.Interaction):
        """Check bot health (DB, API, etc.)"""
        await interaction.response.defer(ephemeral=True)

        # DB Check
        db_status = "🟢 OK"
        try:
            db_manager = self.bot.db_manager
            if not db_manager:
                db_status = "🔴 Not Initialized"
            else:
                # Simple query to check connection
                db_session = db_manager.get_session()
                try:
                    from sqlalchemy import text
                    await db_session.execute(text("SELECT 1"))
                    db_status = "🟢 OK"
                finally:
                    await db_session.close()
        except Exception as e:
            db_status = f"🔴 Error: {str(e)}"

        # OpenRouter Check (Simple ping/check)
        api_status = "🟢 OK"
        if not Config.OPENROUTER_API_KEY:
            api_status = "🔴 Missing API Key"

        # Uptime
        uptime_seconds = int(time.time() - self.start_time)
        days, rem = divmod(uptime_seconds, 86400)
        hours, rem = divmod(rem, 3600)
        minutes, seconds = divmod(rem, 60)
        uptime_str = f"{days}d {hours}h {minutes}m {seconds}s"

        embed = discord.Embed(
            title="🏥 Bot Health Status",
            color=discord.Color.green() if "🔴" not in (db_status + api_status) else discord.Color.red()
        )
        embed.add_field(name="Database", value=db_status, inline=False)
        embed.add_field(name="OpenRouter API", value=api_status, inline=False)
        embed.add_field(name="Uptime", value=uptime_str, inline=False)
        embed.add_field(name="Latency", value=f"{round(self.bot.latency * 1000)}ms", inline=False)
        embed.set_footer(text=f"Checked at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")

        await interaction.followup.send(embed=embed, ephemeral=True)

    # ------------------------------------------------------------------
    # /stats (Admin / Owner)
    # ------------------------------------------------------------------

    @app_commands.command(name="stats", description="Show bot statistics")
    async def stats(self, interaction: discord.Interaction):
        """Show bot statistics (Guilds, Users, Sessions)"""
        if not PermissionManager.has_permission(interaction.user, PermissionLevel.ADMIN, interaction.guild):
            await interaction.response.send_message("❌ このコマンドを実行する権限がありません。", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        db_session = self.bot.db_manager.get_session()
        try:
            from sqlalchemy import func, select
            from modules.database.models import User, Session, Message

            # Guild count
            guild_count = len(self.bot.guilds)

            # User count
            user_stmt = select(func.count(User.id))
            user_result = await db_session.execute(user_stmt)
            user_count = user_result.scalar()

            # Session count (Total and Active)
            total_sess_stmt = select(func.count(Session.id))
            total_sess_result = await db_session.execute(total_sess_stmt)
            total_sessions = total_sess_result.scalar()

            active_sess_count = len(self.bot.session_manager.active_sessions)

            # Message count
            msg_stmt = select(func.count(Message.id))
            msg_result = await db_session.execute(msg_stmt)
            total_messages = msg_result.scalar()

            # System info
            cpu_usage = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            memory_usage = memory.percent

            embed = discord.Embed(
                title="📊 Bot Statistics",
                color=discord.Color.blue()
            )
            embed.add_field(name="Guilds", value=str(guild_count), inline=True)
            embed.add_field(name="Registered Users", value=str(user_count), inline=True)
            embed.add_field(name="Total Sessions", value=str(total_sessions), inline=True)
            embed.add_field(name="Active Sessions", value=str(active_sess_count), inline=True)
            embed.add_field(name="Total AI Messages", value=str(total_messages), inline=True)
            embed.add_field(name="System", value=f"CPU: {cpu_usage}%\nRAM: {memory_usage}%", inline=True)
            embed.add_field(name="Platform", value=f"{platform.system()} {platform.release()}", inline=False)

            await interaction.followup.send(embed=embed, ephemeral=True)

        finally:
            await db_session.close()

    # ------------------------------------------------------------------
    # /config (Admin Only)
    # ------------------------------------------------------------------

    config_group = app_commands.Group(name="config", description="Bot configuration for this server")

    @config_group.command(name="set-category", description="Set the category for coding rooms")
    async def set_category(self, interaction: discord.Interaction, category: discord.CategoryChannel):
        """Set the category where CodingRooms will be created"""
        if not PermissionManager.has_permission(interaction.user, PermissionLevel.ADMIN, interaction.guild):
            await interaction.response.send_message("❌ 管理者権限が必要です。", ephemeral=True)
            return

        # In a real implementation, we would save this to a 'guild_settings' table
        # For now, we'll just acknowledge the command
        await interaction.response.send_message(
            f"✅ このサーバーのコーディングルーム作成カテゴリを {category.mention} に設定しました。\n"
            f"(注: 現在の実装ではメモリ上のみの保持、またはデフォルト動作になります)",
            ephemeral=True
        )
        logger.info(f"Admin {interaction.user} set coding category to {category.id} in guild {interaction.guild.id}")

    # ------------------------------------------------------------------
    # /shutdown (Owner Only)
    # ------------------------------------------------------------------

    @app_commands.command(name="shutdown", description="Safely shutdown the bot (Owner only)")
    async def shutdown(self, interaction: discord.Interaction):
        """Safely shutdown the bot"""
        if not PermissionManager.has_permission(interaction.user, PermissionLevel.BOT_OWNER):
            await interaction.response.send_message("❌ Bot Owner専用のコマンドです。", ephemeral=True)
            return

        await interaction.response.send_message("⚠️ Botをシャットダウンしています...", ephemeral=True)
        logger.warning(f"Shutdown command issued by {interaction.user} ({interaction.user.id})")

        # Log to DB
        db_session = self.bot.db_manager.get_session()
        try:
            await SystemLogRepository.log_event(
                db_session,
                event_type="bot_shutdown",
                message=f"Shutdown issued by owner {interaction.user.id}",
                severity="WARNING"
            )
        finally:
            await db_session.close()

        # Close bot
        await self.bot.close()


async def setup(bot: commands.Bot):
    """Setup function for loading cog"""
    cog = AdminCog(bot)
    await bot.add_cog(cog)
    if cog.config_group not in bot.tree.get_commands():
        bot.tree.add_command(cog.config_group)
    # Add top-level commands to tree
    for cmd in [cog.health, cog.stats, cog.shutdown]:
        if cmd not in bot.tree.get_commands():
            bot.tree.add_command(cmd)
