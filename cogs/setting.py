"""
User setting commands for CoderAgent
Handles /setting command with Embed + Select Menu + Modal UI
"""
import discord
from discord.ext import commands
from discord import app_commands
from logger import setup_logger
from modules.database.repository import UserRepository, APIKeyRepository, UsageLogRepository
from modules.security.permissions import user_command

logger = setup_logger(__name__)


# ---------------------------------------------------------------------------
# UI Components
# ---------------------------------------------------------------------------

class APIKeyModal(discord.ui.Modal, title="OpenRouter APIキーの登録"):
    """Modal for entering OpenRouter API key"""
    
    api_key = discord.ui.TextInput(
        label="APIキー",
        placeholder="sk-or-v1-...",
        min_length=10,
        max_length=200,
        required=True,
        style=discord.TextStyle.short
    )

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        db_session = self.bot.db_manager.get_session()
        try:
            user_id = str(interaction.user.id)
            user = await UserRepository.get_or_create_user(
                db_session,
                user_id,
                interaction.user.name,
                interaction.user.discriminator
            )
            
            # Encrypt API key
            encrypted_key = self.bot.encryption_manager.encrypt(str(self.api_key))
            
            # Deactivate old keys and add new one
            await APIKeyRepository.delete_user_keys(db_session, user.id)
            await APIKeyRepository.create_api_key(
                db_session,
                user.id,
                encrypted_key,
                "OpenRouter"
            )
            
            await interaction.followup.send("✅ APIキーを登録しました。", ephemeral=True)
            
            # Update the setting embed
            cog = self.bot.get_cog("SettingCog")
            if cog:
                await cog.update_setting_message(interaction)
                
        except Exception as e:
            logger.error(f"Error saving API key: {e}", exc_info=True)
            await interaction.followup.send(f"❌ エラー: {str(e)}", ephemeral=True)
        finally:
            await db_session.close()


class SettingSelect(discord.ui.Select):
    """Select menu for /setting"""
    
    def __init__(self, bot):
        options = [
            discord.SelectOption(
                label="🔑 API Key設定",
                value="set_key",
                description="OpenRouter APIキーを登録します"
            ),
            discord.SelectOption(
                label="🗑️ API Key削除",
                value="del_key",
                description="登録済みのAPIキーを削除します"
            ),
            discord.SelectOption(
                label="🚀 モデル変更",
                value="change_model",
                description="使用するAIモデルを変更します"
            ),
            discord.SelectOption(
                label="📊 利用状況確認",
                value="usage",
                description="本日の利用状況を確認します"
            ),
        ]
        super().__init__(
            placeholder="変更したい設定を選択してください...",
            min_values=1,
            max_values=1,
            options=options
        )
        self.bot = bot

    async def callback(self, interaction: discord.Interaction):
        value = self.values[0]
        
        if value == "set_key":
            await interaction.response.send_modal(APIKeyModal(self.bot))
            
        elif value == "del_key":
            await self._handle_delete_key(interaction)
            
        elif value == "change_model":
            view = discord.ui.View()
            view.add_item(ModelSelect(self.bot))
            await interaction.response.send_message(
                "🚀 使用するモデルを選択してください：",
                view=view,
                ephemeral=True
            )
            
        elif value == "usage":
            await self._handle_usage(interaction)

    async def _handle_delete_key(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        db_session = self.bot.db_manager.get_session()
        try:
            user = await UserRepository.get_user_by_discord_id(db_session, str(interaction.user.id))
            if not user:
                await interaction.followup.send("❌ ユーザーが見つかりません。", ephemeral=True)
                return
                
            await APIKeyRepository.delete_user_keys(db_session, user.id)
            await interaction.followup.send("✅ APIキーを削除しました。", ephemeral=True)
            
            cog = self.bot.get_cog("SettingCog")
            if cog:
                await cog.update_setting_message(interaction)
        finally:
            await db_session.close()

    async def _handle_usage(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        db_session = self.bot.db_manager.get_session()
        try:
            user = await UserRepository.get_user_by_discord_id(db_session, str(interaction.user.id))
            if not user:
                await interaction.followup.send("❌ ユーザーが見つかりません。", ephemeral=True)
                return
                
            count = await UsageLogRepository.get_daily_usage_count(db_session, user.id)
            limit = 50
            
            embed = discord.Embed(title="📊 本日の利用状況", color=discord.Color.blue())
            embed.add_field(name="利用回数", value=f"{count} / {limit}", inline=True)
            embed.add_field(name="残り回数", value=f"{max(0, limit - count)}", inline=True)
            embed.set_footer(text="毎日 0:00 (UTC) にリセットされます")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
        finally:
            await db_session.close()


class ModelSelect(discord.ui.Select):
    """Select menu for changing AI model"""
    
    def __init__(self, bot):
        options = [
            discord.SelectOption(label="🚀 高品質", value="high", description="大規模開発・複雑な設計向け"),
            discord.SelectOption(label="⚖️ バランス（推奨）", value="balance", description="一般的な開発・コード修正向け"),
            discord.SelectOption(label="💰 節約", value="budget", description="簡単な質問・軽量な生成向け"),
        ]
        super().__init__(placeholder="モデルを選択...", options=options)
        self.bot = bot

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        db_session = self.bot.db_manager.get_session()
        try:
            user = await UserRepository.get_user_by_discord_id(db_session, str(interaction.user.id))
            if not user:
                await interaction.followup.send("❌ ユーザーが見つかりません。", ephemeral=True)
                return
            
            preset = self.values[0]
            await UserRepository.update_model_preset(db_session, user.id, preset)
            
            labels = {"high": "高品質", "balance": "バランス", "budget": "節約"}
            await interaction.followup.send(
                f"✅ モデルを **{labels.get(preset, preset)}** に変更しました。",
                ephemeral=True
            )
            
            cog = self.bot.get_cog("SettingCog")
            if cog:
                await cog.update_setting_message(interaction)
        finally:
            await db_session.close()


class SettingView(discord.ui.View):
    """View containing the setting select menu"""
    
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.add_item(SettingSelect(bot))


# ---------------------------------------------------------------------------
# Cog
# ---------------------------------------------------------------------------

class SettingCog(commands.Cog):
    """Cog for user settings"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="setting", description="Manage your AI settings")
    async def setting(self, interaction: discord.Interaction):
        """Display the setting embed and select menu"""
        embed = await self._create_setting_embed(interaction.user)
        await interaction.response.send_message(
            embed=embed,
            view=SettingView(self.bot),
            ephemeral=True
        )

    async def _create_setting_embed(self, user: discord.User) -> discord.Embed:
        """Create the setting status embed"""
        db_session = self.bot.db_manager.get_session()
        api_status = "❌ 未登録"
        model_preset_label = "⚖️ バランス（推奨）"
        
        try:
            db_user = await UserRepository.get_user_by_discord_id(db_session, str(user.id))
            if db_user:
                key = await APIKeyRepository.get_active_api_key(db_session, db_user.id)
                if key:
                    api_status = "✅ 登録済み"
                
                presets = {
                    "high": "🚀 高品質",
                    "balance": "⚖️ バランス（推奨）",
                    "budget": "💰 節約"
                }
                model_preset_label = presets.get(db_user.model_preset, model_preset_label)
        finally:
            await db_session.close()

        embed = discord.Embed(
            title="⚙️ ユーザー設定",
            description=f"{user.mention} さんの現在の設定状況です。",
            color=discord.Color.blue()
        )
        embed.add_field(name="OpenRouter APIキー", value=api_status, inline=True)
        embed.add_field(name="使用モデル", value=model_preset_label, inline=True)
        embed.set_footer(text="下のメニューから設定を変更できます。")
        return embed

    async def update_setting_message(self, interaction: discord.Interaction):
        """Update the existing setting message embed"""
        embed = await self._create_setting_embed(interaction.user)
        try:
            # Check if it's an interaction from a button/select or the original command
            if hasattr(interaction, "message") and interaction.message:
                await interaction.edit_original_response(embed=embed, view=SettingView(self.bot))
            else:
                # If we're calling this from somewhere else
                pass
        except Exception as e:
            logger.error(f"Error updating setting message: {e}")


async def setup(bot: commands.Bot):
    """Setup function for loading cog"""
    await bot.add_cog(SettingCog(bot))
