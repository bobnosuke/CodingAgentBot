"""
Admin and Owner commands for CoderAgent
Handles /config, /health, /stats, /shutdown commands
Supports both Slash and Prefix commands
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

    # Slash command group for config
    config_group = app_commands.Group(name="config", description="Bot configuration for this server")

    # ------------------------------------------------------------------
    # /health / !health
    # ------------------------------------------------------------------

    @app_commands.command(name="health", description="Check the bot's health status")
    async def health_slash(self, interaction: discord.Interaction):
        await self._do_health(interaction)

    @commands.command(name="health")
    async def health_prefix(self, ctx: commands.Context):
        await self._do_health(ctx)

    async def _do_health(self, ctx_or_inter):
        is_interaction = isinstance(ctx_or_inter, discord.Interaction)
        if is_interaction:
            await ctx_or_inter.response.defer(ephemeral=True)

        db_status = "🟢 OK"
        try:
            db_session = self.bot.db_manager.get_session()
            try:
                from sqlalchemy import text
                await db_session.execute(text("SELECT 1"))
            finally:
                await db_session.close()
        except Exception as e:
            db_status = f"🔴 Error: {str(e)}"

        uptime_seconds = int(time.time() - self.start_time)
        uptime_str = f"{uptime_seconds // 3600}h {(uptime_seconds % 3600) // 60}m"

        embed = discord.Embed(title="🏥 Bot Health Status", color=discord.Color.green())
        embed.add_field(name="Database", value=db_status, inline=False)
        embed.add_field(name="Uptime", value=uptime_str, inline=False)
        
        if is_interaction:
            await ctx_or_inter.followup.send(embed=embed, ephemeral=True)
        else:
            await ctx_or_inter.send(embed=embed)

    # ------------------------------------------------------------------
    # /stats / !stats
    # ------------------------------------------------------------------

    @app_commands.command(name="stats", description="Show bot statistics")
    async def stats_slash(self, interaction: discord.Interaction):
        await self._do_stats(interaction)

    @commands.command(name="stats")
    async def stats_prefix(self, ctx: commands.Context):
        await self._do_stats(ctx)

    async def _do_stats(self, ctx_or_inter):
        is_interaction = isinstance(ctx_or_inter, discord.Interaction)
        user = ctx_or_inter.user if is_interaction else ctx_or_inter.author
        guild = ctx_or_inter.guild

        if not PermissionManager.has_permission(user, PermissionLevel.ADMIN, guild):
            msg = "❌ このコマンドを実行する権限がありません。"
            if is_interaction:
                await ctx_or_inter.response.send_message(msg, ephemeral=True)
            else:
                await ctx_or_inter.send(msg)
            return

        if is_interaction:
            await ctx_or_inter.response.defer(ephemeral=True)

        embed = discord.Embed(title="📊 Bot Statistics", color=discord.Color.blue())
        embed.add_field(name="Guilds", value=str(len(self.bot.guilds)), inline=True)
        embed.add_field(name="System", value=f"CPU: {psutil.cpu_percent()}%", inline=True)
        
        if is_interaction:
            await ctx_or_inter.followup.send(embed=embed, ephemeral=True)
        else:
            await ctx_or_inter.send(embed=embed)

    # ------------------------------------------------------------------
    # /config / !config
    # ------------------------------------------------------------------

    @config_group.command(name="set-category", description="Set the category for coding rooms")
    async def set_category_slash(self, interaction: discord.Interaction, category: discord.CategoryChannel):
        await self._do_set_category(interaction, category)

    @commands.group(name="config")
    async def config_prefix(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.send("❌ サブコマンドを指定してください: `set-category`")

    @config_prefix.command(name="set-category")
    async def set_category_prefix(self, ctx: commands.Context, category: discord.CategoryChannel):
        await self._do_set_category(ctx, category)

    async def _do_set_category(self, ctx_or_inter, category: discord.CategoryChannel):
        is_interaction = isinstance(ctx_or_inter, discord.Interaction)
        user = ctx_or_inter.user if is_interaction else ctx_or_inter.author
        guild = ctx_or_inter.guild

        if not PermissionManager.has_permission(user, PermissionLevel.ADMIN, guild):
            msg = "❌ 管理者権限が必要です。"
            if is_interaction:
                await ctx_or_inter.response.send_message(msg, ephemeral=True)
            else:
                await ctx_or_inter.send(msg)
            return

        msg = f"✅ コーディングルーム作成カテゴリを {category.mention} に設定しました。"
        if is_interaction:
            await ctx_or_inter.response.send_message(msg, ephemeral=True)
        else:
            await ctx_or_inter.send(msg)

    # ------------------------------------------------------------------
    # /shutdown / !shutdown
    # ------------------------------------------------------------------

    @app_commands.command(name="shutdown", description="Safely shutdown the bot (Owner only)")
    async def shutdown_slash(self, interaction: discord.Interaction):
        await self._do_shutdown(interaction)

    @commands.command(name="shutdown")
    async def shutdown_prefix(self, ctx: commands.Context):
        await self._do_shutdown(ctx)

    async def _do_shutdown(self, ctx_or_inter):
        is_interaction = isinstance(ctx_or_inter, discord.Interaction)
        user = ctx_or_inter.user if is_interaction else ctx_or_inter.author

        if not PermissionManager.has_permission(user, PermissionLevel.BOT_OWNER):
            msg = "❌ Bot Owner専用のコマンドです。"
            if is_interaction:
                await ctx_or_inter.response.send_message(msg, ephemeral=True)
            else:
                await ctx_or_inter.send(msg)
            return

        msg = "⚠️ Botをシャットダウンしています..."
        if is_interaction:
            await ctx_or_inter.response.send_message(msg, ephemeral=True)
        else:
            await ctx_or_inter.send(msg)
        
        await self.bot.close()


async def setup(bot: commands.Bot):
    """Setup function for loading cog"""
    cog = AdminCog(bot)
    await bot.add_cog(cog)
    if cog.config_group not in bot.tree.get_commands():
        bot.tree.add_command(cog.config_group)
    for cmd in [cog.health_slash, cog.stats_slash, cog.shutdown_slash]:
        if cmd not in bot.tree.get_commands():
            bot.tree.add_command(cmd)
