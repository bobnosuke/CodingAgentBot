"""
Admin and Owner commands for CoderAgent
Handles /config, /health, /stats, /shutdown commands with Panel UI
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
from modules.database.repository import UserRepository, SessionRepository, SystemLogRepository, GuildRepository
from config import Config

logger = setup_logger(__name__)


# ---------------------------------------------------------------------------
# UI Components for /config
# ---------------------------------------------------------------------------

class ConfigSelect(discord.ui.Select):
    """Select menu for /config"""
    
    def __init__(self, bot):
        options = [
            discord.SelectOption(
                label="📁 カテゴリ設定",
                value="set_category",
                description="CodingRoomを作成するカテゴリを指定します"
            ),
            discord.SelectOption(
                label="👥 同時利用数制限",
                value="user_limit",
                description="サーバー全体の同時利用ユーザー数を設定します"
            ),
            discord.SelectOption(
                label="📺 チャンネル数制限",
                value="channel_limit",
                description="1ユーザーあたりの作成上限を設定します"
            ),
            discord.SelectOption(
                label="🔄 設定リセット",
                value="reset",
                description="サーバー設定をデフォルトに戻します"
            ),
        ]
        super().__init__(
            placeholder="変更したい設定項目を選択してください...",
            min_values=1,
            max_values=1,
            options=options
        )
        self.bot = bot

    async def callback(self, interaction: discord.Interaction):
        value = self.values[0]
        
        if value == "set_category":
            # For category, we use a separate view with a channel select
            view = discord.ui.View()
            view.add_item(CategorySelect(self.bot))
            await interaction.response.send_message(
                "📁 コーディングルームを作成するカテゴリを選択してください：",
                view=view,
                ephemeral=True
            )
            
        elif value == "user_limit":
            await interaction.response.send_modal(LimitModal(self.bot, "user_limit", "同時利用ユーザー数制限"))
            
        elif value == "channel_limit":
            await interaction.response.send_modal(LimitModal(self.bot, "channel_limit", "1ユーザーあたりのチャンネル数制限"))
            
        elif value == "reset":
            await self._handle_reset(interaction)

    async def _handle_reset(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        db_session = self.bot.db_manager.get_session()
        try:
            await GuildRepository.update_config(
                db_session, 
                str(interaction.guild.id),
                coding_category_id=None,
                user_limit=10,
                channel_limit=3
            )
            await interaction.followup.send("✅ サーバー設定をデフォルトにリセットしました。", ephemeral=True)
            
            cog = self.bot.get_cog("AdminCog")
            if cog:
                await cog.update_config_message(interaction)
        finally:
            await db_session.close()


class CategorySelect(discord.ui.ChannelSelect):
    """Channel select for setting coding category"""
    
    def __init__(self, bot):
        super().__init__(
            placeholder="カテゴリを選択...",
            channel_types=[discord.ChannelType.category]
        )
        self.bot = bot

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        category = self.values[0]
        
        db_session = self.bot.db_manager.get_session()
        try:
            await GuildRepository.update_config(
                db_session,
                str(interaction.guild.id),
                coding_category_id=str(category.id)
            )
            await interaction.followup.send(f"✅ カテゴリを {category.name} に設定しました。", ephemeral=True)
            
            cog = self.bot.get_cog("AdminCog")
            if cog:
                await cog.update_config_message(interaction)
        finally:
            await db_session.close()


class LimitModal(discord.ui.Modal):
    """Modal for entering numeric limits"""
    
    limit_value = discord.ui.TextInput(
        label="設定値 (数値)",
        placeholder="例: 5",
        min_length=1,
        max_length=3,
        required=True
    )

    def __init__(self, bot, field_name, title):
        super().__init__(title=title)
        self.bot = bot
        self.field_name = field_name

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        try:
            val = int(str(self.limit_value))
            if val < 1:
                raise ValueError("1以上の数値を入力してください。")
        except ValueError:
            await interaction.followup.send("❌ 有効な数値を入力してください。", ephemeral=True)
            return

        db_session = self.bot.db_manager.get_session()
        try:
            update_data = {self.field_name: val}
            await GuildRepository.update_config(db_session, str(interaction.guild.id), **update_data)
            await interaction.followup.send(f"✅ 設定を {val} に更新しました。", ephemeral=True)
            
            cog = self.bot.get_cog("AdminCog")
            if cog:
                await cog.update_config_message(interaction)
        finally:
            await db_session.close()


class ConfigView(discord.ui.View):
    """View for /config panel"""
    
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.add_item(ConfigSelect(bot))


# ---------------------------------------------------------------------------
# Cog
# ---------------------------------------------------------------------------

class AdminCog(commands.Cog):
    """Cog for administrative and owner-only commands"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.start_time = time.time()

    @app_commands.command(name="config", description="サーバー設定を管理します（管理者用）")
    async def config(self, interaction: discord.Interaction):
        """Display the server config panel"""
        if not PermissionManager.has_permission(interaction.user, PermissionLevel.ADMIN, interaction.guild):
            await interaction.response.send_message("❌ 管理者権限が必要です。", ephemeral=True)
            return

        embed = await self._create_config_embed(interaction.guild)
        await interaction.response.send_message(
            embed=embed,
            view=ConfigView(self.bot),
            ephemeral=True
        )

    async def _create_config_embed(self, guild: discord.Guild) -> discord.Embed:
        """Create the server config status embed"""
        db_session = self.bot.db_manager.get_session()
        category_name = "未設定 (デフォルト)"
        user_limit = 10
        channel_limit = 3
        
        try:
            db_guild = await GuildRepository.get_or_create_guild(
                db_session, 
                str(guild.id), 
                str(guild.owner_id)
            )
            
            if db_guild.coding_category_id:
                category = guild.get_channel(int(db_guild.coding_category_id))
                if category:
                    category_name = category.name
                else:
                    category_name = "⚠️ カテゴリが見つかりません"
            
            user_limit = db_guild.user_limit
            channel_limit = db_guild.channel_limit
        finally:
            await db_session.close()

        embed = discord.Embed(
            title="🛠️ サーバー設定パネル",
            description=f"**{guild.name}** の現在の設定状況です。",
            color=discord.Color.gold()
        )
        embed.add_field(name="📁 作成先カテゴリ", value=category_name, inline=False)
        embed.add_field(name="👥 同時利用ユーザー上限", value=f"{user_limit} 人", inline=True)
        embed.add_field(name="📺 チャンネル作成上限", value=f"{channel_limit} / ユーザー", inline=True)
        embed.set_footer(text="下のメニューから設定を変更できます。")
        return embed

    async def update_config_message(self, interaction: discord.Interaction):
        """Update the existing config message embed"""
        embed = await self._create_config_embed(interaction.guild)
        try:
            if interaction.response.is_done():
                await interaction.edit_original_response(embed=embed, view=ConfigView(self.bot))
            else:
                await interaction.response.edit_message(embed=embed, view=ConfigView(self.bot))
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Health, Stats, Shutdown (Keeping existing logic)
    # ------------------------------------------------------------------

    @app_commands.command(name="health", description="Botの状態を確認します")
    async def health_check(self, interaction: discord.Interaction):
        """Check bot health status"""
        await interaction.response.defer(ephemeral=True)
        db_status = "🔴 Error"
        try:
            if await self.bot.db_manager.health_check():
                db_status = "🟢 Healthy"
        except Exception as e:
            db_status = f"🔴 Error: {str(e)}"

        process = psutil.Process(os.getpid())
        memory_usage = process.memory_info().rss / 1024 / 1024  # MB
        uptime_seconds = int(time.time() - self.start_time)
        hours, rem = divmod(uptime_seconds, 3600)
        minutes, seconds = divmod(rem, 60)
        
        embed = discord.Embed(title="🏥 CoderAgent Health Status", color=discord.Color.green())
        embed.add_field(name="Database", value=db_status, inline=True)
        embed.add_field(name="Uptime", value=f"{hours}h {minutes}m {seconds}s", inline=True)
        embed.add_field(name="Memory", value=f"{memory_usage:.1f} MB", inline=True)
        embed.add_field(name="Latency", value=f"{round(self.bot.latency * 1000)}ms", inline=True)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="stats", description="Botの利用統計を表示します")
    async def stats(self, interaction: discord.Interaction):
        """Show bot usage statistics"""
        if not PermissionManager.has_permission(interaction.user, PermissionLevel.ADMIN, interaction.guild):
            await interaction.response.send_message("❌ 権限がありません。", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        db_session = self.bot.db_manager.get_session()
        try:
            from sqlalchemy import select, func
            from modules.database.models import User, Session, Message, UsageLog
            
            user_count = await db_session.scalar(select(func.count(User.id)))
            session_count = await db_session.scalar(select(func.count(Session.id)))
            active_sessions = await db_session.scalar(select(func.count(Session.id)).where(Session.is_active == True))
            message_count = await db_session.scalar(select(func.count(Message.id)))
            
            # API Usage (Tokens/Cost)
            total_tokens = await db_session.execute(select(func.sum(UsageLog.token_input + UsageLog.token_output)))
            total_tokens = total_tokens.scalar() or 0
            total_cost = await db_session.execute(select(func.sum(UsageLog.estimated_cost)))
            total_cost = total_cost.scalar() or 0.0

            embed = discord.Embed(title="📊 CoderAgent Statistics", color=discord.Color.blue())
            embed.add_field(name="Total Servers", value=str(len(self.bot.guilds)), inline=True)
            embed.add_field(name="Total Users", value=str(user_count), inline=True)
            embed.add_field(name="Sessions (Active/Total)", value=f"{active_sessions} / {session_count}", inline=True)
            embed.add_field(name="Total Messages", value=str(message_count), inline=True)
            embed.add_field(name="API Usage", value=f"Tokens: {total_tokens:,}\nCost: ${total_cost:.4f}", inline=True)
            embed.add_field(name="System", value=f"CPU: {psutil.cpu_percent()}%\nRAM: {psutil.virtual_memory().percent}%", inline=True)
            await interaction.followup.send(embed=embed, ephemeral=True)
        finally:
            await db_session.close()

    @app_commands.command(name="shutdown", description="Botを安全に停止します（オーナー専用）")
    async def shutdown(self, interaction: discord.Interaction):
        """Safely shut down the bot"""
        if not PermissionManager.has_permission(interaction.user, PermissionLevel.BOT_OWNER):
            await interaction.response.send_message("❌ オーナー専用です。", ephemeral=True)
            return

        await interaction.response.send_message("👋 シャットダウン中...", ephemeral=True)
        db_session = self.bot.db_manager.get_session()
        try:
            await SystemLogRepository.log_event(db_session, "bot_shutdown", f"Shutdown by {interaction.user}", "WARNING")
        finally:
            await db_session.close()
        await self.bot.close()


async def setup(bot: commands.Bot):
    """Setup function for loading cog"""
    await bot.add_cog(AdminCog(bot))
