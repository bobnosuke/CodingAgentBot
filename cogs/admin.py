import discord
from discord.ext import commands
from discord import app_commands
from logger import setup_logger
from modules.security.permissions import PermissionLevel, PermissionManager
from modules.database.database import DatabaseManager
from modules.database.repository import UserRepository, SessionRepository, MessageRepository

logger = setup_logger(__name__)

class AdminCog(commands.Cog):
    """Cog for administrator and owner commands"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    admin_group = app_commands.Group(name="admin", description="Administrator commands")

    @admin_group.command(name="health", description="Check bot health and database connection")
    @PermissionManager.has_permission(PermissionLevel.ADMIN)
    async def health_check(self, interaction: discord.Interaction):
        """Check bot health and database connection"""
        await interaction.response.defer(ephemeral=True)

        db_status = "❌ Disconnected"
        if self.bot.db_manager:
            try:
                if await self.bot.db_manager.health_check():
                    db_status = "✅ Connected"
                else:
                    db_status = "⚠️ Error"
            except Exception as e:
                db_status = f"❌ Error: {e}"

        embed = discord.Embed(
            title="🩺 Bot Health Check",
            color=discord.Color.blue()
        )
        embed.add_field(name="Bot Latency", value=f"{self.bot.latency * 1000:.2f} ms", inline=False)
        embed.add_field(name="Database Status", value=db_status, inline=False)
        embed.set_footer(text="Made by RovaexTeam")

        await interaction.followup.send(embed=embed, ephemeral=True)

    @admin_group.command(name="stats", description="Display bot usage statistics")
    @PermissionManager.has_permission(PermissionLevel.ADMIN)
    async def stats(self, interaction: discord.Interaction):
        """Display bot usage statistics"""
        await interaction.response.defer(ephemeral=True)

        async with self.bot.db_manager.get_session() as session:
            total_users = await UserRepository.count_users(session)
            total_sessions = await SessionRepository.count_sessions(session)
            total_ai_calls = await MessageRepository.count_messages(session)

            embed = discord.Embed(
                title="📊 Bot Usage Statistics",
                description="現在のボットの利用状況です。",
                color=discord.Color.gold()
            )
            embed.add_field(name="総ユーザー数", value=str(total_users), inline=False)
            embed.add_field(name="総セッション数", value=str(total_sessions), inline=False)
            embed.add_field(name="総AI呼び出し回数", value=str(total_ai_calls), inline=False)
        embed.set_footer(text="Made by RovaexTeam")

        await interaction.followup.send(embed=embed, ephemeral=True)

    @admin_group.command(name="shutdown", description="Shutdown the bot (Owner only)")
    @PermissionManager.has_permission(PermissionLevel.BOT_OWNER)
    async def shutdown(self, interaction: discord.Interaction):
        """Shutdown the bot (Owner only)"""
        await interaction.response.defer(ephemeral=True)

        embed = discord.Embed(
            title="🔴 Shutting Down",
            description="CoderAgent is now shutting down... Goodbye!",
            color=discord.Color.red()
        )
        embed.set_footer(text="Made by RovaexTeam")
        await interaction.followup.send(embed=embed, ephemeral=True)

        logger.info(f"Bot shutdown initiated by {interaction.user.name} ({interaction.user.id})")
        await self.bot.close()

async def setup(bot: commands.Bot):
    cog = AdminCog(bot)
    await bot.add_cog(cog)
    if cog.admin_group not in bot.tree.get_commands():
        bot.tree.add_command(cog.admin_group)
