"""
API Key management commands for CoderAgent
Handles API key registration and management
Supports both Slash and Prefix commands
"""
import discord
from discord.ext import commands
from discord import app_commands
from logger import setup_logger
from modules.database.repository import UserRepository, APIKeyRepository

logger = setup_logger(__name__)


class APIKeyCog(commands.Cog):
    """Cog for API key management"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # Slash command group
    api_key_group = app_commands.Group(name="api-key", description="API Key management commands")

    # ------------------------------------------------------------------
    # /api-key register / !api-key register
    # ------------------------------------------------------------------

    @api_key_group.command(name="register", description="Register your OpenRouter API key")
    @app_commands.describe(api_key="Your OpenRouter API key")
    async def api_key_register_slash(self, interaction: discord.Interaction, api_key: str):
        """Slash command for registering API key"""
        await self._do_api_key_register(interaction, api_key)

    @commands.group(name="api-key")
    async def api_key_prefix(self, ctx: commands.Context):
        """Prefix command group for api-key"""
        if ctx.invoked_subcommand is None:
            await ctx.send("❌ サブコマンドを指定してください: `register`, `remove`")

    @api_key_prefix.command(name="register")
    async def api_key_register_prefix(self, ctx: commands.Context, api_key: str):
        """Prefix command for registering API key"""
        await self._do_api_key_register(ctx, api_key)

    async def _do_api_key_register(self, ctx_or_inter, api_key: str):
        """Common logic for registering API key"""
        is_interaction = isinstance(ctx_or_inter, discord.Interaction)
        user = ctx_or_inter.user if is_interaction else ctx_or_inter.author

        try:
            if is_interaction:
                await ctx_or_inter.response.defer(ephemeral=True)
            else:
                # Delete message for security if possible
                try:
                    await ctx_or_inter.message.delete()
                except discord.Forbidden:
                    pass

            db_session = self.bot.db_manager.get_session()
            try:
                db_user = await UserRepository.get_or_create_user(
                    db_session,
                    str(user.id),
                    user.name,
                    user.discriminator
                )

                encrypted_key = self.bot.encryption_manager.encrypt(api_key)
                
                # Set API key (Update if exists, otherwise create)
                await APIKeyRepository.set_api_key(
                    db_session,
                    db_user.id,
                    encrypted_key,
                    "OpenRouter"
                )

                msg = "✅ APIキーが正常に登録されました！\nキーは安全に暗号化されて保存されました。"
                if is_interaction:
                    await ctx_or_inter.followup.send(msg, ephemeral=True)
                else:
                    await ctx_or_inter.send(f"{user.mention} {msg}")

                logger.info(f"API key registered for user {user.id}")

            finally:
                await db_session.close()

        except Exception as e:
            logger.error(f"Error in _do_api_key_register: {e}", exc_info=True)
            msg = f"❌ APIキー登録エラー: {str(e)}"
            if is_interaction:
                await ctx_or_inter.followup.send(msg, ephemeral=True)
            else:
                await ctx_or_inter.send(msg)

    # ------------------------------------------------------------------
    # /api-key remove / !api-key remove
    # ------------------------------------------------------------------

    @api_key_group.command(name="remove", description="Remove your OpenRouter API key")
    async def api_key_remove_slash(self, interaction: discord.Interaction):
        """Slash command for removing API key"""
        await self._do_api_key_remove(interaction)

    @api_key_prefix.command(name="remove")
    async def api_key_remove_prefix(self, ctx: commands.Context):
        """Prefix command for removing API key"""
        await self._do_api_key_remove(ctx)

    async def _do_api_key_remove(self, ctx_or_inter):
        """Common logic for removing API key"""
        is_interaction = isinstance(ctx_or_inter, discord.Interaction)
        user = ctx_or_inter.user if is_interaction else ctx_or_inter.author

        try:
            if is_interaction:
                await ctx_or_inter.response.defer(ephemeral=True)

            db_session = self.bot.db_manager.get_session()
            try:
                db_user = await UserRepository.get_user_by_discord_id(db_session, str(user.id))
                if not db_user:
                    msg = "❌ ユーザー情報が見つかりません。"
                    if is_interaction:
                        await ctx_or_inter.followup.send(msg, ephemeral=True)
                    else:
                        await ctx_or_inter.send(msg)
                    return

                api_key = await APIKeyRepository.get_active_api_key(db_session, db_user.id)
                if not api_key:
                    msg = "❌ 登録されているAPIキーがありません。"
                    if is_interaction:
                        await ctx_or_inter.followup.send(msg, ephemeral=True)
                    else:
                        await ctx_or_inter.send(msg)
                    return

                # For now, we just inform the user as per original implementation
                msg = "✅ APIキーの削除リクエストを受け付けました。\nBotを継続して利用するには新しいキーを登録してください。"
                if is_interaction:
                    await ctx_or_inter.followup.send(msg, ephemeral=True)
                else:
                    await ctx_or_inter.send(msg)

                logger.info(f"API key removal requested for user {user.id}")

            finally:
                await db_session.close()

        except Exception as e:
            logger.error(f"Error in _do_api_key_remove: {e}", exc_info=True)
            msg = f"❌ エラー: {str(e)}"
            if is_interaction:
                await ctx_or_inter.followup.send(msg, ephemeral=True)
            else:
                await ctx_or_inter.send(msg)


async def setup(bot: commands.Bot):
    """Setup function for loading cog"""
    cog = APIKeyCog(bot)
    await bot.add_cog(cog)
    if cog.api_key_group not in bot.tree.get_commands():
        bot.tree.add_command(cog.api_key_group)
