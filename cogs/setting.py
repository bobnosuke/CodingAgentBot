"""
User settings commands for CoderAgent
Handles API key management and model selection
"""
import discord
from discord.ext import commands
from discord import app_commands
import logging
from typing import Any, Optional, Union

from modules.database.repository import UserRepository, APIKeyRepository, UsageLogRepository
from modules.security.permissions import PermissionLevel, PermissionManager
from modules.database.database import DatabaseManager
from modules.security.encryption import EncryptionManager
from logger import setup_logger

logger = setup_logger(__name__)


class SettingView(discord.ui.View):
    """Persistent View for /setting command (Public Panel)"""
    
    def __init__(self, db_manager: DatabaseManager, encryption_manager: EncryptionManager):
        # 永続化のためにtimeout=Noneを設定
        super().__init__(timeout=None)
        self.db_manager = db_manager
        self.encryption_manager = encryption_manager

    @discord.ui.select(
        placeholder="設定項目を選択してください",
        options=[
            discord.SelectOption(label="API Key設定", value="api_key", description="OpenRouter APIキーを登録・更新します", emoji="🔑"),
            discord.SelectOption(label="使用モデル変更", value="model", description="AIモデル設定を変更します", emoji="🤖"),
            discord.SelectOption(label="利用状況確認", value="status", description="本日の利用回数や使用モデルを確認します", emoji="📊"),
            discord.SelectOption(label="API Key削除", value="delete_key", description="登録済みAPIキーを削除します", emoji="🗑️"),
        ],
        custom_id="persistent:setting_select"  # custom_idを固定
    )
    async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        """Handle setting selection from Public Panel"""
        # 永続Viewではインスタンス変数にuser_idを持たせられないため、interaction.userを使用
        user_id = interaction.user.id
        value = select.values[0]
        
        try:
            if value == "api_key":
                await interaction.response.send_modal(APIKeyModal(self.db_manager, self.encryption_manager))
            elif value == "model":
                await self.show_model_selection(interaction)
            elif value == "status":
                await self.show_status(interaction)
            elif value == "delete_key":
                await self.confirm_delete_key(interaction)
        except Exception as e:
            logger.error(f"Error in select_callback: {e}", exc_info=True)
            await interaction.response.send_message(f"❌ エラーが発生しました: {str(e)}", ephemeral=True)

    async def show_model_selection(self, interaction: discord.Interaction):
        """Show model selection menu (New Ephemeral)"""
        view = ModelSelectionView(interaction.user.id, self.db_manager)
        embed = discord.Embed(
            title="🤖 使用モデル変更",
            description="利用するAIモデルのプリセットを選択してください。",
            color=discord.Color.blue()
        )
        embed.add_field(name="🚀 高品質", value="大規模開発、複雑な設計に最適", inline=False)
        embed.add_field(name="⚖️ バランス（推奨）", value="通常開発、コード修正に最適", inline=False)
        embed.add_field(name="💰 節約", value="簡単な質問、軽量コード生成に最適", inline=False)
        embed.set_footer(text="Made by RovaexTeam")
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    async def show_status(self, interaction: discord.Interaction):
        """Show usage status (New Ephemeral)"""
        await interaction.response.defer(ephemeral=True, thinking=True)
        
        db_session = self.db_manager.get_session()
        try:
            db_user = await UserRepository.get_user_by_discord_id(db_session, str(interaction.user.id))
            
            if not db_user:
                await interaction.followup.send("ユーザー情報が見つかりません。まずはコマンドを実行してください。", ephemeral=True)
                return

            daily_count = await UsageLogRepository.get_daily_usage_count(db_session, db_user.id)
            limit = 50
            remaining = max(0, limit - daily_count)
            
            embed = discord.Embed(
                title="📊 利用状況確認",
                color=discord.Color.green()
            )
            embed.add_field(name="使用モデル", value=getattr(db_user, "model_preset", "balance").capitalize(), inline=True)
            embed.add_field(name="本日の利用回数", value=f"{daily_count} / {limit}", inline=True)
            embed.add_field(name="残り利用回数", value=str(remaining), inline=True)
            embed.set_footer(text="Made by RovaexTeam")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
        finally:
            await db_session.close()

    async def confirm_delete_key(self, interaction: discord.Interaction):
        """Confirm API key deletion (New Ephemeral)"""
        view = DeleteConfirmView(interaction.user.id, self.db_manager, self.encryption_manager)
        embed = discord.Embed(
            title="⚠️ API Key 削除確認",
            description="登録済みのAPIキーを削除しますか？削除後はコーディング機能が利用できなくなります。",
            color=discord.Color.red()
        )
        embed.set_footer(text="Made by RovaexTeam")
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class APIKeyModal(discord.ui.Modal, title="OpenRouter API Key 設定"):
    """Modal for API key input"""
    
    api_key_input = discord.ui.TextInput(
        label="API Key",
        placeholder="sk-or-v1-...",
        min_length=10,
        required=True,
        style=discord.TextStyle.short
    )

    def __init__(self, db_manager: DatabaseManager, encryption_manager: EncryptionManager):
        super().__init__()
        self.db_manager = db_manager
        self.encryption_manager = encryption_manager

    async def on_submit(self, interaction: discord.Interaction):
        """Handle API key submission"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            db_session = self.db_manager.get_session()
            try:
                db_user = await UserRepository.get_or_create_user(
                    db_session,
                    str(interaction.user.id),
                    interaction.user.name,
                    interaction.user.discriminator
                )
                
                encrypted_key = self.encryption_manager.encrypt(self.api_key_input.value)
                await APIKeyRepository.set_api_key(db_session, db_user.id, encrypted_key, "Default")
                
                embed = discord.Embed(
                    title="✅ API Key 保存完了",
                    description="APIキーを暗号化して保存しました。これよりコーディング機能が利用可能です。",
                    color=discord.Color.green()
                )
                embed.set_footer(text="Made by RovaexTeam")
                
                await interaction.followup.send(embed=embed, ephemeral=True)
            finally:
                await db_session.close()
        except Exception as e:
            logger.error(f"Error saving API key: {e}", exc_info=True)
            await interaction.followup.send(f"❌ エラーが発生しました: {str(e)}", ephemeral=True)


class ModelSelectionView(discord.ui.View):
    """View for model selection (Ephemeral Panel - No need to persist)"""
    
    def __init__(self, user_id: int, db_manager: DatabaseManager):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.db_manager = db_manager

    @discord.ui.button(label="高品質", style=discord.ButtonStyle.primary, emoji="🚀")
    async def high_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.update_model(interaction, "high")

    @discord.ui.button(label="バランス", style=discord.ButtonStyle.success, emoji="⚖️")
    async def balance_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.update_model(interaction, "balance")

    @discord.ui.button(label="節約", style=discord.ButtonStyle.secondary, emoji="💰")
    async def low_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.update_model(interaction, "low")

    async def update_model(self, interaction: discord.Interaction, model_preset: str):
        """Update model (Edit Ephemeral)"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("この操作は実行者本人のみ可能です。", ephemeral=True)
            return

        try:
            await interaction.response.defer(ephemeral=True)
            
            db_session = self.db_manager.get_session()
            try:
                db_user = await UserRepository.get_user_by_discord_id(db_session, str(interaction.user.id))
                if db_user:
                    db_user.model_preset = model_preset
                    await db_session.commit()
                    
                    embed = discord.Embed(
                        title="✅ モデル変更完了",
                        description=f"使用モデルを **{model_preset.capitalize()}** に変更しました。",
                        color=discord.Color.green()
                    )
                    embed.set_footer(text="Made by RovaexTeam")
                    
                    await interaction.edit_original_response(embed=embed, view=None)
                else:
                    await interaction.followup.send("ユーザー情報が見つかりません。", ephemeral=True)
            finally:
                await db_session.close()
        except Exception as e:
            logger.error(f"Error in update_model: {e}", exc_info=True)
            await interaction.edit_original_response(content=f"❌ エラーが発生しました: {str(e)}", view=None)


class DeleteConfirmView(discord.ui.View):
    """View for API key deletion confirmation (Ephemeral Panel - No need to persist)"""
    
    def __init__(self, user_id: int, db_manager: DatabaseManager, encryption_manager: EncryptionManager):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.db_manager = db_manager
        self.encryption_manager = encryption_manager

    @discord.ui.button(label="削除する", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Confirm deletion (Edit Ephemeral)"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("この操作は実行者本人のみ可能です。", ephemeral=True)
            return

        try:
            await interaction.response.defer(ephemeral=True)
            
            db_session = self.db_manager.get_session()
            try:
                db_user = await UserRepository.get_user_by_discord_id(db_session, str(interaction.user.id))
                if db_user:
                    from sqlalchemy import delete
                    from modules.database.models import APIKey
                    stmt = delete(APIKey).where(APIKey.user_id == db_user.id)
                    await db_session.execute(stmt)
                    await db_session.commit()
                    
                    embed = discord.Embed(
                        title="✅ API Key 削除完了",
                        description="登録済みのAPIキーを削除しました。",
                        color=discord.Color.green()
                    )
                    embed.set_footer(text="Made by RovaexTeam")
                    
                    await interaction.edit_original_response(embed=embed, view=None)
                else:
                    await interaction.followup.send("ユーザー情報が見つかりません。", ephemeral=True)
            finally:
                await db_session.close()
        except Exception as e:
            logger.error(f"Error in confirm_button: {e}", exc_info=True)
            await interaction.edit_original_response(content=f"❌ エラーが発生しました: {str(e)}", view=None)

    @discord.ui.button(label="キャンセル", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Cancel deletion (Edit Ephemeral)"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("この操作は実行者本人のみ可能です。", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="✅ キャンセル",
            description="削除をキャンセルしました。",
            color=discord.Color.blue()
        )
        embed.set_footer(text="Made by RovaexTeam")
        
        await interaction.response.edit_message(embed=embed, view=None)


class SettingCog(commands.Cog):
    """Cog for user settings"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _send_setting_panel(self, target: Any, user: discord.User, ephemeral: bool = False):
        """Send setting panel (Initial Public/Ephemeral)"""
        try:
            db_session = self.bot.db_manager.get_session()
            try:
                await UserRepository.get_or_create_user(db_session, str(user.id), user.name, user.discriminator)
                await db_session.commit()
                
                embed = discord.Embed(
                    title="⚙️ CoderAgent ユーザー設定",
                    description="以下のメニューから設定項目を選択してください。",
                    color=discord.Color.blue()
                )
                embed.set_footer(text="Made by RovaexTeam")
                
                # 永続Viewを使用
                view = SettingView(self.bot.db_manager, self.bot.encryption_manager)
                
                if isinstance(target, discord.Interaction):
                    if target.response.is_done():
                        await target.followup.send(embed=embed, view=view, ephemeral=ephemeral)
                    else:
                        await target.response.send_message(embed=embed, view=view, ephemeral=ephemeral)
                else:
                    await target.send(embed=embed, view=view)
            finally:
                await db_session.close()
        except Exception as e:
            logger.error(f"Error in setting panel: {e}", exc_info=True)
            if isinstance(target, discord.Interaction):
                await target.followup.send(f"❌ エラーが発生しました: {str(e)}", ephemeral=True)
            else:
                await target.send(f"❌ エラーが発生しました: {str(e)}")

    @app_commands.command(name="setting", description="ユーザー設定（APIキー・モデル等）を管理します")
    @PermissionManager.has_permission(PermissionLevel.USER)
    async def setting_slash(self, interaction: discord.Interaction):
        """Show the setting menu (Public)"""
        await interaction.response.defer(ephemeral=False)
        await self._send_setting_panel(interaction, interaction.user, ephemeral=False)

    @commands.command(name="setting", description="設定画面を直接表示します")
    async def setting_prefix(self, ctx: commands.Context):
        """Show the setting menu (Public)"""
        await self._send_setting_panel(ctx, ctx.author, ephemeral=False)


async def setup(bot: commands.Bot):
    """Setup the cog"""
    cog = SettingCog(bot)
    await bot.add_cog(cog)
