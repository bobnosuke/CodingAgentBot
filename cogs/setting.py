"""
User settings cog for CoderAgent
Handles quality selection, API key management, and language settings
"""
import discord
from discord.ext import commands
from discord import app_commands
from logger import setup_logger
from modules.database.repository import UserRepository, APIKeyRepository, UsageLogRepository
from modules.utils.i18n import i18n
from configs.ai_models import model_manager
import asyncio

logger = setup_logger(__name__)


class SettingView(discord.ui.View):
    """Persistent View for /setting (Public Panel)"""
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(
        label="設定を開始", 
        style=discord.ButtonStyle.primary, 
        emoji="⚙️",
        custom_id="persistent:setting_start_button"
    )
    async def start_setting(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle 'Start Settings' button click - Show Ephemeral Panel"""
        db_session = self.bot.db_manager.get_session()
        try:
            user = await UserRepository.get_or_create_user(
                db_session, 
                str(interaction.user.id), 
                interaction.user.name, 
                interaction.user.discriminator
            )
            lang = user.language or "en-US"
            api_key = await APIKeyRepository.get_active_api_key(db_session, user.id)
            daily_count = await UsageLogRepository.get_daily_usage_count(db_session, user.id)

            # Quality level mapping for display
            quality_labels = {
                "high_quality": "高品質",
                "standard": "標準",
                "fast": "高速"
            }
            current_quality = quality_labels.get(user.model_preset, "標準")

            # AI Model Status
            active_models = [m for m, s in model_manager.model_status.items() if s["status"] == "active"]
            cooldown_models = [m for m, s in model_manager.model_status.items() if s["status"] == "cooldown"]

            # Create Status Embed
            embed = discord.Embed(
                title=i18n.translate(lang, "SETTING.CURRENT_STATUS_TITLE"),
                color=discord.Color.blue()
            )
            embed.add_field(name="AI品質", value=current_quality, inline=True)
            embed.add_field(name=i18n.translate(lang, "SETTING.LANG_SETTING"), value="🇺🇸 English" if lang == "en-US" else "🇯🇵 日本語", inline=True)
            embed.add_field(name="API Key", value="✅ Registered" if api_key else "❌ Not Registered", inline=True)
            embed.add_field(name="今日利用回数", value=f"{daily_count} / 50", inline=True)

            if active_models:
                embed.add_field(name="現在利用AI", value=", ".join(active_models[:3]), inline=False)
            if cooldown_models:
                embed.add_field(name="現在Cooldown中AI", value=", ".join(cooldown_models[:3]), inline=False)

            embed.set_footer(text="Made by RovaexTeam")

            # Create Detail View with Select Menu
            view = SettingDetailView(self.bot, lang)
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        finally:
            await db_session.close()


class SettingDetailView(discord.ui.View):
    """Ephemeral View for detailed settings"""
    def __init__(self, bot: commands.Bot, lang: str):
        super().__init__(timeout=300)
        self.bot = bot
        self.lang = lang

        # Add select menu
        self.select = discord.ui.Select(
            placeholder=i18n.translate(lang, "SETTING.SELECT_PLACEHOLDER"),
            options=[
                discord.SelectOption(label="AI品質変更", value="quality", emoji="🚀", description="AIの回答品質レベルを変更します"),
                discord.SelectOption(label=i18n.translate(lang, "SETTING.API_KEY_MGMT"), value="apikey", emoji="🔑", description=i18n.translate(lang, "SETTING.API_KEY_MGMT_DESC")),
                discord.SelectOption(label=i18n.translate(lang, "SETTING.LANG_SETTING"), value="lang", emoji="🌐", description=i18n.translate(lang, "SETTING.LANG_SETTING_DESC")),
            ]
        )
        self.select.callback = self.select_callback
        self.add_item(self.select)

    async def select_callback(self, interaction: discord.Interaction):
        action = self.select.values[0]

        if action == "quality":
            await self._show_quality_selection(interaction)
        elif action == "apikey":
            await self._show_apikey_mgmt(interaction)
        elif action == "lang":
            await self._show_lang_setting(interaction)

    async def _show_quality_selection(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="AI品質レベル選択",
            description="用途に合わせてAIの品質レベルを選択してください。",
            color=discord.Color.blue()
        )
        embed.add_field(name="🚀 高品質", value="大規模実装・設計・デバッグ向け。高性能モデルを使用します。", inline=False)
        embed.add_field(name="⚖️ 標準", value="通常の開発・修正向け。バランスの取れたモデルを使用します。", inline=False)
        embed.add_field(name="💻 高速", value="簡単なコード・質問回答向け。軽量で高速なモデルを使用します。", inline=False)
        embed.set_footer(text="Made by RovaexTeam")
        view = QualitySelectionView(self.bot, self.lang)
        await interaction.response.edit_message(embed=embed, view=view)

    async def _show_apikey_mgmt(self, interaction: discord.Interaction):
        db_session = self.bot.db_manager.get_session()
        try:
            user = await UserRepository.get_user_by_discord_id(db_session, str(interaction.user.id))
            api_key = await APIKeyRepository.get_active_api_key(db_session, user.id)

            if api_key:
                embed = discord.Embed(
                    title=i18n.translate(self.lang, "SETTING.API_KEY_MGMT"),
                    description=i18n.translate(self.lang, "SETTING.API_KEY_DELETE_CONFIRM"),
                    color=discord.Color.red()
                )
                embed.set_footer(text="Made by RovaexTeam")
                view = APIKeyDeleteConfirmView(self.bot, self.lang)
                await interaction.response.edit_message(embed=embed, view=view)
            else:
                modal = APIKeyModal(self.bot, self.lang)
                await interaction.response.send_modal(modal)
        finally:
            await db_session.close()

    async def _show_lang_setting(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title=i18n.translate(self.lang, "SETTING.LANG_SETTING"),
            description=i18n.translate(self.lang, "SETTING.LANG_SETTING_DESC"),
            color=discord.Color.purple()
        )
        embed.set_footer(text="Made by RovaexTeam")
        view = LanguageSelectionView(self.bot, self.lang)
        await interaction.response.edit_message(embed=embed, view=view)

class QualitySelectionView(discord.ui.View):
    def __init__(self, bot, lang):
        super().__init__(timeout=300)
        self.bot = bot
        self.lang = lang

    @discord.ui.button(label="高品質", style=discord.ButtonStyle.primary, emoji="🚀")
    async def high_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._set_quality(interaction, "high_quality")

    @discord.ui.button(label="標準", style=discord.ButtonStyle.primary, emoji="⚖️")
    async def standard_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._set_quality(interaction, "standard")

    @discord.ui.button(label="高速", style=discord.ButtonStyle.primary, emoji="💻")
    async def fast_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._set_quality(interaction, "fast")

    async def _set_quality(self, interaction: discord.Interaction, quality: str):
        db_session = self.bot.db_manager.get_session()
        try:
            user = await UserRepository.get_user_by_discord_id(db_session, str(interaction.user.id))
            user.model_preset = quality
            await db_session.commit()

            quality_labels = {"high_quality": "高品質", "standard": "標準", "fast": "高速"}
            msg = f"AI品質を **{quality_labels[quality]}** に設定しました。"
            await interaction.response.edit_message(content=msg, embed=None, view=None)
        finally:
            await db_session.close()

    @discord.ui.button(label="もどる", style=discord.ButtonStyle.secondary, row=1)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = SettingDetailView(self.bot, self.lang)
        await interaction.response.edit_message(content=None, view=view)


class LanguageSelectionView(discord.ui.View):
    def __init__(self, bot, lang):
        super().__init__(timeout=60)
        self.bot = bot
        self.lang = lang

    @discord.ui.button(label="English", style=discord.ButtonStyle.primary, emoji="🇺🇸")
    async def en_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._set_language(interaction, "en-US")

    @discord.ui.button(label="日本語", style=discord.ButtonStyle.primary, emoji="🇯🇵")
    async def ja_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._set_language(interaction, "ja")

    async def _set_language(self, interaction: discord.Interaction, new_lang: str):
        db_session = self.bot.db_manager.get_session()
        try:
            user = await UserRepository.get_user_by_discord_id(db_session, str(interaction.user.id))
            user.language = new_lang
            await db_session.commit()

            msg = i18n.translate(new_lang, "SETTING.LANG_CHANGE_SUCCESS")
            await interaction.response.edit_message(content=msg, embed=None, view=None)
        finally:
            await db_session.close()


class APIKeyModal(discord.ui.Modal):
    def __init__(self, bot, lang):
        title = i18n.translate(lang, "SETTING.API_KEY_MGMT")
        super().__init__(title=title)
        self.bot = bot
        self.lang = lang

        self.key_input = discord.ui.TextInput(
            label="OpenRouter API Key",
            placeholder="sk-or-v1-...",
            required=True,
            min_length=10
        )
        self.add_item(self.key_input)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        db_session = self.bot.db_manager.get_session()
        try:
            user = await UserRepository.get_or_create_user(
                db_session, 
                str(interaction.user.id), 
                interaction.user.name, 
                interaction.user.discriminator
            )
            encrypted_key = self.bot.encryption_manager.encrypt(self.key_input.value)

            await APIKeyRepository.set_api_key(db_session, user.id, encrypted_key, "Default")
            await db_session.commit()

            await interaction.followup.send(i18n.translate(self.lang, "SETTING.API_KEY_SET_SUCCESS"), ephemeral=True)
        finally:
            await db_session.close()

class APIKeyDeleteConfirmView(discord.ui.View):
    def __init__(self, bot, lang):
        super().__init__(timeout=60)
        self.bot = bot
        self.lang = lang

    @discord.ui.button(label="削除", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def delete_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        db_session = self.bot.db_manager.get_session()
        try:
            user = await UserRepository.get_user_by_discord_id(db_session, str(interaction.user.id))
            api_key = await APIKeyRepository.get_active_api_key(db_session, user.id)
            if api_key:
                await db_session.delete(api_key)
                await db_session.commit()

                await interaction.response.edit_message(content=i18n.translate(self.lang, "SETTING.API_KEY_DELETE_SUCCESS"), embed=None, view=None)
        finally:
            await db_session.close()

    @discord.ui.button(label="キャンセル", style=discord.ButtonStyle.secondary)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content=i18n.translate(self.lang, "COMMON.CANCEL"), embed=None, view=None)

class SettingCog(commands.Cog):
    """Cog for user settings"""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="setting", 
        description="設定用パネルを表示します"
    )
    async def setting(self, interaction: discord.Interaction):
        """Show User Settings Panel (Public Start Button)"""
        db_session = self.bot.db_manager.get_session()
        try:
            user = await UserRepository.get_or_create_user(
                db_session, 
                str(interaction.user.id), 
                interaction.user.name, 
                interaction.user.discriminator
            )
            lang = user.language or "ja"

            embed = discord.Embed(
                title=i18n.translate(lang, "SETTING.PANEL_TITLE"),
                description=i18n.translate(lang, "SETTING.PANEL_DESC"),
                color=discord.Color.blue()
            )
            embed.set_footer(text="Made by RovaexTeam")

            view = SettingView(self.bot)
            # Update button label based on language
            for item in view.children:
                if isinstance(item, discord.ui.Button) and item.custom_id == "persistent:setting_start_button":
                    item.label = i18n.translate(lang, "SETTING.START_BUTTON")
            
            await interaction.response.send_message(
                embed=embed,
                view=view,
                ephemeral=False
            )
        finally:
            await db_session.close()

async def setup(bot: commands.Bot):
    """Setup the cog"""
    await bot.add_cog(SettingCog(bot))
