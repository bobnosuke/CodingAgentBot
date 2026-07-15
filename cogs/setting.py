"""
User settings cog for CoderAgent
Handles model selection, API key management, and language settings
"""
import discord
from discord.ext import commands
from discord import app_commands
from logger import setup_logger
from modules.database.repository import UserRepository, APIKeyRepository, MessageRepository, UsageLogRepository
from modules.utils.i18n import i18n
import asyncio

logger = setup_logger(__name__)


class SettingView(discord.ui.View):
    """Persistent View for /setting (Public Panel)"""
    
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.bot = bot
    
    async def _get_user_lang(self, interaction: discord.Interaction):
        db_session = self.bot.db_manager.get_session()
        try:
            user = await UserRepository.get_or_create_user(
                db_session, 
                str(interaction.user.id), 
                interaction.user.name, 
                interaction.user.discriminator
            )
            return user.language or "en-US"
        finally:
            await db_session.close()

    @discord.ui.select(
        placeholder="🎯 Select an option",
        options=[
            discord.SelectOption(label="Change AI Model", value="model", emoji="🤖", description="Select AI model for coding"),
            discord.SelectOption(label="Usage Stats", value="usage", emoji="📊", description="Check your API usage"),
            discord.SelectOption(label="API Key Management", value="apikey", emoji="🔑", description="Register or delete API key"),
            discord.SelectOption(label="Language Settings", value="lang", emoji="🌐", description="Change bot language"),
        ],
        custom_id="persistent:setting_select"
    )
    async def setting_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        """Handle selection from Public Panel"""
        lang = await self._get_user_lang(interaction)
        action = select.values[0]
        
        if action == "model":
            await self._show_model_selection(interaction, lang)
        elif action == "usage":
            await self._show_usage_stats(interaction, lang)
        elif action == "apikey":
            await self._show_apikey_mgmt(interaction, lang)
        elif action == "lang":
            await self._show_lang_setting(interaction, lang)

    async def _show_model_selection(self, interaction: discord.Interaction, lang: str):
        embed = discord.Embed(
            title=i18n.translate(lang, "SETTING.MODEL_SELECT_TITLE"),
            description=i18n.translate(lang, "SETTING.MODEL_SELECT_DESC"),
            color=discord.Color.blue()
        )
        embed.add_field(name=f"🚀 {i18n.translate(lang, 'SETTING.MODEL_HIGH')}", value="Claude 3.5 Sonnet", inline=False)
        embed.add_field(name=f"⚖️ {i18n.translate(lang, 'SETTING.MODEL_BALANCE')}", value="Gemini 1.5 Pro", inline=False)
        embed.add_field(name=f"💰 {i18n.translate(lang, 'SETTING.MODEL_LOW')}", value="Llama 3.1 70B", inline=False)
        embed.set_footer(text="Made by RovaexTeam")
        
        view = ModelSelectionView(self.bot, lang)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    async def _show_usage_stats(self, interaction: discord.Interaction, lang: str):
        await interaction.response.defer(ephemeral=True)
        db_session = self.bot.db_manager.get_session()
        try:
            user = await UserRepository.get_user_by_discord_id(db_session, str(interaction.user.id))
            total_messages = await MessageRepository.count_user_messages(db_session, user.id)
            daily_count = await UsageLogRepository.get_daily_usage_count(db_session, user.id)
            
            embed = discord.Embed(
                title=i18n.translate(lang, "SETTING.USAGE_TITLE"),
                color=discord.Color.gold()
            )
            embed.add_field(name=i18n.translate(lang, "SETTING.USAGE_TOTAL_MESSAGES"), value=str(total_messages), inline=True)
            embed.add_field(name=i18n.translate(lang, "SETTING.USAGE_DAILY_MESSAGES"), value=str(daily_count), inline=True)
            embed.add_field(name=i18n.translate(lang, "SETTING.USAGE_CURRENT_MODEL"), value=user.model_preset.capitalize(), inline=True)
            embed.set_footer(text="Made by RovaexTeam")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
        finally:
            await db_session.close()

    async def _show_apikey_mgmt(self, interaction: discord.Interaction, lang: str):
        db_session = self.bot.db_manager.get_session()
        try:
            user = await UserRepository.get_user_by_discord_id(db_session, str(interaction.user.id))
            api_key = await APIKeyRepository.get_active_api_key(db_session, user.id)
            
            if api_key:
                embed = discord.Embed(
                    title=i18n.translate(lang, "SETTING.API_KEY_MGMT"),
                    description=i18n.translate(lang, "SETTING.API_KEY_DELETE_CONFIRM"),
                    color=discord.Color.red()
                )
                embed.set_footer(text="Made by RovaexTeam")
                view = APIKeyDeleteConfirmView(self.bot, lang)
                await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            else:
                modal = APIKeyModal(self.bot, lang)
                await interaction.response.send_modal(modal)
        finally:
            await db_session.close()

    async def _show_lang_setting(self, interaction: discord.Interaction, lang: str):
        embed = discord.Embed(
            title=i18n.translate(lang, "SETTING.LANG_SETTING"),
            description=i18n.translate(lang, "SETTING.LANG_SETTING_DESC"),
            color=discord.Color.purple()
        )
        embed.set_footer(text="Made by RovaexTeam")
        view = LanguageSelectionView(self.bot, lang)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


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


class ModelSelectionView(discord.ui.View):
    def __init__(self, bot, lang):
        super().__init__(timeout=60)
        self.bot = bot
        self.lang = lang

    @discord.ui.button(label="High Performance", style=discord.ButtonStyle.secondary, emoji="🚀")
    async def high_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._set_model(interaction, "high")

    @discord.ui.button(label="Balanced", style=discord.ButtonStyle.secondary, emoji="⚖️")
    async def balance_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._set_model(interaction, "balance")

    @discord.ui.button(label="Cost Efficient", style=discord.ButtonStyle.secondary, emoji="💰")
    async def low_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._set_model(interaction, "low")

    async def _set_model(self, interaction: discord.Interaction, preset: str):
        db_session = self.bot.db_manager.get_session()
        try:
            user = await UserRepository.get_user_by_discord_id(db_session, str(interaction.user.id))
            user.model_preset = preset
            await db_session.commit()
            
            model_name = i18n.translate(self.lang, f"SETTING.MODEL_{preset.upper()}")
            msg = i18n.translate(self.lang, "SETTING.MODEL_SET_SUCCESS", model=model_name)
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

    @discord.ui.button(label="Delete", style=discord.ButtonStyle.danger, emoji="🗑️")
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

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content=i18n.translate(self.lang, "COMMON.CANCEL"), embed=None, view=None)


class SettingCog(commands.Cog):
    """Cog for user settings"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @app_commands.command(name="setting", description="Configure bot settings (AI model, API key, language)")
    async def setting(self, interaction: discord.Interaction):
        """Show User Settings Panel"""
        db_session = self.bot.db_manager.get_session()
        try:
            user = await UserRepository.get_or_create_user(
                db_session, 
                str(interaction.user.id), 
                interaction.user.name, 
                interaction.user.discriminator
            )
            lang = user.language or "en-US"
            
            embed = discord.Embed(
                title=i18n.translate(lang, "SETTING.PANEL_TITLE"),
                description=i18n.translate(lang, "SETTING.PANEL_DESC"),
                color=discord.Color.blue()
            )
            embed.set_footer(text="Made by RovaexTeam")
            
            view = SettingView(self.bot)
            # Update select menu labels based on language
            for item in view.children:
                if isinstance(item, discord.ui.Select) and item.custom_id == "persistent:setting_select":
                    item.placeholder = i18n.translate(lang, "SETTING.SELECT_PLACEHOLDER")
                    item.options = [
                        discord.SelectOption(label=i18n.translate(lang, "SETTING.MODEL_CHANGE"), value="model", emoji="🤖", description=i18n.translate(lang, "SETTING.MODEL_CHANGE_DESC")),
                        discord.SelectOption(label=i18n.translate(lang, "SETTING.USAGE_STATS"), value="usage", emoji="📊", description=i18n.translate(lang, "SETTING.USAGE_STATS_DESC")),
                        discord.SelectOption(label=i18n.translate(lang, "SETTING.API_KEY_MGMT"), value="apikey", emoji="🔑", description=i18n.translate(lang, "SETTING.API_KEY_MGMT_DESC")),
                        discord.SelectOption(label=i18n.translate(lang, "SETTING.LANG_SETTING"), value="lang", emoji="🌐", description=i18n.translate(lang, "SETTING.LANG_SETTING_DESC")),
                    ]
            
            await interaction.response.send_message(embed=embed, view=view, ephemeral=False)
        finally:
            await db_session.close()


async def setup(bot: commands.Bot):
    """Setup the cog"""
    await bot.add_cog(SettingCog(bot))
