import discord
from discord import app_commands
from discord.ext import commands
import logging
from typing import Optional

from modules.database.repository import UserRepository, APIKeyRepository
from modules.database.database import get_db_session
from modules.security.encryption import EncryptionManager
from modules.security.permissions import PermissionLevel, has_permission

logger = logging.getLogger("CoderAgent")

class SettingView(discord.ui.View):
    """View for /setting command with select menu"""
    def __init__(self, user_id: int, user_repo: UserRepository, api_repo: APIKeyRepository):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.user_repo = user_repo
        self.api_repo = api_repo

    @discord.ui.select(
        placeholder="設定項目を選択してください",
        options=[
            discord.SelectOption(label="API Key設定", value="api_key", description="OpenRouter APIキーを登録・更新します", emoji="🔑"),
            discord.SelectOption(label="使用モデル変更", value="model", description="AIモデル設定を変更します", emoji="🤖"),
            discord.SelectOption(label="利用状況確認", value="status", description="本日の利用回数や使用モデルを確認します", emoji="📊"),
            discord.SelectOption(label="API Key削除", value="delete_key", description="登録済みAPIキーを削除します", emoji="🗑️"),
        ]
    )
    async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("この操作は実行者本人のみ可能です。", ephemeral=True)
            return

        value = select.values[0]
        
        if value == "api_key":
            await interaction.response.send_modal(APIKeyModal(self.api_repo))
        elif value == "model":
            await self.show_model_selection(interaction)
        elif value == "status":
            await self.show_status(interaction)
        elif value == "delete_key":
            await self.confirm_delete_key(interaction)

    async def show_model_selection(self, interaction: discord.Interaction):
        view = ModelSelectionView(self.user_id, self.user_repo)
        embed = discord.Embed(
            title="🤖 使用モデル変更",
            description="利用するAIモデルのプリセットを選択してください。",
            color=discord.Color.blue()
        )
        embed.add_field(name="🚀 高品質", value="大規模開発、複雑な設計に最適", inline=False)
        embed.add_field(name="⚖️ バランス（推奨）", value="通常開発、コード修正に最適", inline=False)
        embed.add_field(name="💰 節約", value="簡単な質問、軽量コード生成に最適", inline=False)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    async def show_status(self, interaction: discord.Interaction):
        async with get_db_session() as session:
            from modules.database.repository import UsageLogRepository
            user_repo = UserRepository(session)
            usage_repo = UsageLogRepository()
            
            db_user = await user_repo.get_user_by_discord_id(session, str(interaction.user.id))
            
            if not db_user:
                await interaction.response.send_message("ユーザー情報が見つかりません。まずはコマンドを実行してください。", ephemeral=True)
                return

            # 本日の利用回数を取得
            daily_count = await usage_repo.get_daily_usage_count(session, db_user.id)
            limit = 50  # 要件定義書の制限
            remaining = max(0, limit - daily_count)
            
            embed = discord.Embed(
                title="📊 利用状況確認",
                color=discord.Color.green()
            )
            embed.add_field(name="使用モデル", value=db_user.model_preset.capitalize(), inline=True)
            embed.add_field(name="本日の利用回数", value=f"{daily_count} / {limit}", inline=True)
            embed.add_field(name="残り利用回数", value=str(remaining), inline=True)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)

    async def confirm_delete_key(self, interaction: discord.Interaction):
        view = DeleteConfirmView(self.user_id, self.api_repo)
        await interaction.response.send_message(
            "⚠️ **警告**: 登録済みのAPIキーを削除しますか？削除後はコーディング機能が利用できなくなります。",
            view=view,
            ephemeral=True
        )

class APIKeyModal(discord.ui.Modal, title="OpenRouter API Key 設定"):
    api_key = discord.ui.TextInput(
        label="API Key",
        placeholder="sk-or-v1-...",
        min_length=10,
        required=True,
        style=discord.TextStyle.short
    )

    def __init__(self, api_repo: APIKeyRepository):
        super().__init__()
        self.api_repo = api_repo

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        try:
            # メッセージ削除（Prefixコマンド時のセキュリティ対策）
            if interaction.message and not interaction.is_interaction():
                try:
                    await interaction.message.delete()
                except:
                    pass

            async with get_db_session() as session:
                user_repo = UserRepository(session)
                api_repo = APIKeyRepository(session)
                
                db_user = await user_repo.get_or_create(
                    str(interaction.user.id),
                    interaction.user.name
                )
                
                # 暗号化して保存
                encryption = EncryptionManager()
                encrypted_key = encryption.encrypt(self.api_key.value)
                
                await api_repo.set_key(db_user.id, encrypted_key)
                await session.commit()

            await interaction.followup.send("✅ APIキーを暗号化して保存しました。これよりコーディング機能が利用可能です。", ephemeral=True)
        except Exception as e:
            logger.error(f"Error saving API key: {e}")
            await interaction.followup.send("❌ APIキーの保存中にエラーが発生しました。", ephemeral=True)

class ModelSelectionView(discord.ui.View):
    def __init__(self, user_id: int, user_repo: UserRepository):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.user_repo = user_repo

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
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("この操作は実行者本人のみ可能です。", ephemeral=True)
            return

        async with get_db_session() as session:
            user_repo = UserRepository(session)
            db_user = await user_repo.get_by_discord_id(str(interaction.user.id))
            if db_user:
                db_user.model_preset = model_preset
                await session.commit()
                await interaction.response.send_message(f"✅ 使用モデルを **{model_preset.capitalize()}** に変更しました。", ephemeral=True)
            else:
                await interaction.response.send_message("ユーザー情報が見つかりません。", ephemeral=True)

class DeleteConfirmView(discord.ui.View):
    def __init__(self, user_id: int, api_repo: APIKeyRepository):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.api_repo = api_repo

    @discord.ui.button(label="削除する", style=discord.ButtonStyle.danger)
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("この操作は実行者本人のみ可能です。", ephemeral=True)
            return

        async with get_db_session() as session:
            user_repo = UserRepository(session)
            api_repo = APIKeyRepository(session)
            db_user = await user_repo.get_by_discord_id(str(interaction.user.id))
            if db_user:
                await api_repo.delete_key(db_user.id)
                await session.commit()
                await interaction.response.send_message("✅ 登録済みのAPIキーを削除しました。", ephemeral=True)
            else:
                await interaction.response.send_message("ユーザー情報が見つかりません。", ephemeral=True)

    @discord.ui.button(label="キャンセル", style=discord.ButtonStyle.secondary)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("削除をキャンセルしました。", ephemeral=True)

class SettingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="setting", description="ユーザー設定（APIキー・モデル等）を管理します")
    @has_permission(PermissionLevel.USER)
    async def setting(self, ctx: commands.Context):
        """Show the setting menu"""
        async with get_db_session() as session:
            user_repo = UserRepository(session)
            api_repo = APIKeyRepository(session)
            
            # Ensure user exists
            await user_repo.get_or_create(str(ctx.author.id), ctx.author.name)
            await session.commit()
            
            embed = discord.Embed(
                title="⚙️ CoderAgent ユーザー設定",
                description="以下のメニューから設定項目を選択してください。",
                color=discord.Color.blue()
            )
            
            view = SettingView(ctx.author.id, user_repo, api_repo)
            
            if ctx.interaction:
                await ctx.interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            else:
                await ctx.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(SettingCog(bot))
