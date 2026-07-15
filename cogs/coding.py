"""
Coding commands for CoderAgent
Handles /coding start, /coding end commands and AI chat in CodingRooms
"""
import discord
from discord.ext import commands
from discord import app_commands
from logger import setup_logger
from modules.security.permissions import PermissionLevel, PermissionManager
from modules.database.repository import UserRepository, APIKeyRepository, MessageRepository, SessionRepository
from modules.session.manager import SessionManager
from modules.ai.openrouter import OpenRouterClient, AIService

logger = setup_logger(__name__)


class CodingPanelView(discord.ui.View):
    """Persistent View for /coding panel (Public Panel)"""
    
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.bot = bot
        self.session_manager = SessionManager(bot)
    
    @discord.ui.select(
        placeholder="🎯 操作を選択してください",
        options=[
            discord.SelectOption(label="開発開始", value="start", emoji="🚀", description="新しいコーディングセッションを開始します"),
            discord.SelectOption(label="プロジェクト一覧", value="list", emoji="📋", description="あなたのプロジェクト一覧を表示します"),
            discord.SelectOption(label="プロジェクト詳細", value="info", emoji="ℹ️", description="プロジェクトの詳細情報を確認します"),
            discord.SelectOption(label="プロジェクト名変更", value="rename", emoji="✏️", description="プロジェクト名を変更します"),
        ],
        custom_id="persistent:coding_panel_select"
    )
    async def panel_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        """Handle selection from Public Panel"""
        await interaction.response.defer(ephemeral=True)
        
        action = select.values[0]
        if action == "start":
            await self._handle_start(interaction)
        elif action == "list":
            await self._handle_list(interaction)
        elif action == "info":
            await self._handle_info(interaction)
        elif action == "rename":
            await self._handle_rename(interaction)
    
    async def _handle_start(self, interaction: discord.Interaction):
        """Handle start (New Ephemeral)"""
        user_id = str(interaction.user.id)
        active_session = self.session_manager.get_user_active_session(user_id)
        
        if active_session:
            await interaction.followup.send(
                f"❌ すでにアクティブなセッションがあります: `{active_session[:8]}`\n"
                f"新しく開始する前に `/coding end` で終了してください。",
                ephemeral=True
            )
            return
        
        db_session = self.bot.db_manager.get_session()
        try:
            user = await UserRepository.get_or_create_user(db_session, user_id, interaction.user.name, interaction.user.discriminator)
            api_key = await APIKeyRepository.get_active_api_key(db_session, user.id)
            
            if not api_key:
                await interaction.followup.send(
                    "❌ OpenRouterのAPIキーが見つかりません！\n先に `/setting` からAPIキーを登録してください。",
                    ephemeral=True
                )
                return
            
            decrypted_key = self.bot.encryption_manager.decrypt(api_key.encrypted_key)
            
            # セッションIDを生成（manager側でも生成されるが、チャンネル名指定のためにここで取得）
            import uuid
            short_uuid = str(uuid.uuid4())[:8]
            channel_name = f"session-{short_uuid}"
            
            session_uuid, coding_room = await self.session_manager.create_session(
                db_session, 
                interaction.user, 
                interaction.guild, 
                channel_name # チャンネル名としてセッションID（の一部）を渡す
            )
            
            model_preset = getattr(user, "model_preset", "balance")
            openrouter_client = OpenRouterClient(decrypted_key)
            ai_service = AIService(openrouter_client)
            ai_service.set_model_by_preset(model_preset)
            
            embed = discord.Embed(
                title="✅ コーディングセッション開始",
                description=f"あなた専用のコーディングルームを作成しました！",
                color=discord.Color.green()
            )
            embed.add_field(name="セッションID", value=f"`{session_uuid[:8]}`", inline=False)
            embed.add_field(name="チャンネル", value=coding_room.mention, inline=False)
            embed.set_footer(text="Made by RovaexTeam")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            # Coding Room welcome
            welcome_embed = discord.Embed(
                title="🤖 コーディングセッションへようこそ",
                description="私はあなたのAIコーディングアシスタントです。何を作りたいか教えてください！",
                color=discord.Color.blue()
            )
            welcome_embed.add_field(name="ヒント", value="・作りたい機能や修正したいコードをチャットしてください。\n・`!download` で作成したファイルをダウンロードできます。\n・`/coding end` でセッションを終了できます。", inline=False)
            welcome_embed.set_footer(text="Made by RovaexTeam")
            await coding_room.send(embed=welcome_embed)
        except Exception as e:
            logger.error(f"Error in _handle_start: {e}", exc_info=True)
            await interaction.followup.send(f"❌ セッション開始中にエラーが発生しました: {str(e)}", ephemeral=True)
        finally:
            await db_session.close()
    
    async def _handle_list(self, interaction: discord.Interaction):
        await interaction.followup.send("📋 **プロジェクト一覧機能は準備中です。**", ephemeral=True)
    
    async def _handle_info(self, interaction: discord.Interaction):
        await interaction.followup.send("ℹ️ **プロジェクト詳細機能は準備中です。**", ephemeral=True)
    
    async def _handle_rename(self, interaction: discord.Interaction):
        await interaction.followup.send("✏️ **プロジェクト名変更機能は準備中です。**", ephemeral=True)


class CodingCog(commands.Cog):
    """Cog for coding-related commands"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.session_manager = SessionManager(bot)
        self.ai_services = {}
    
    coding_group = app_commands.Group(name="coding", description="AIコーディング関連のコマンド")
    
    @coding_group.command(name="panel", description="コーディング管理パネルを表示します")
    @PermissionManager.has_permission(PermissionLevel.ADMIN)
    async def coding_panel(self, interaction: discord.Interaction):
        """Show Public Panel"""
        embed = discord.Embed(
            title="🎮 コーディング管理パネル",
            description="以下のメニューから操作を選択してください。",
            color=discord.Color.blue()
        )
        embed.set_footer(text="Made by RovaexTeam")
        view = CodingPanelView(self.bot)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=False)
    
    @coding_group.command(name="start", description="新しいコーディングセッションを開始します")
    async def coding_start(self, interaction: discord.Interaction, project_name: str = None):
        """Start Session (New Ephemeral)"""
        user_id = str(interaction.user.id)
        active_session = self.session_manager.get_user_active_session(user_id)
        
        if active_session:
            await interaction.response.send_message(f"❌ すでにアクティブなセッションがあります: `{active_session[:8]}`", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        db_session = self.bot.db_manager.get_session()
        try:
            user = await UserRepository.get_or_create_user(db_session, user_id, interaction.user.name, interaction.user.discriminator)
            api_key = await APIKeyRepository.get_active_api_key(db_session, user.id)
            
            if not api_key:
                await interaction.followup.send("❌ OpenRouterのAPIキーが見つかりません！", ephemeral=True)
                return
            
            decrypted_key = self.bot.encryption_manager.decrypt(api_key.encrypted_key)
            
            import uuid
            short_uuid = str(uuid.uuid4())[:8]
            channel_name = project_name or f"session-{short_uuid}"
            
            session_uuid, coding_room = await self.session_manager.create_session(
                db_session, 
                interaction.user, 
                interaction.guild, 
                channel_name
            )
            
            embed = discord.Embed(
                title="✅ コーディングセッション開始",
                description=f"あなた専用のコーディングルームを作成しました！",
                color=discord.Color.green()
            )
            embed.add_field(name="チャンネル", value=coding_room.mention, inline=False)
            embed.set_footer(text="Made by RovaexTeam")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            # Coding Room welcome
            welcome_embed = discord.Embed(
                title="🤖 コーディングセッションへようこそ",
                description="私はあなたのAIコーディングアシスタントです。何を作りたいか教えてください！",
                color=discord.Color.blue()
            )
            welcome_embed.set_footer(text="Made by RovaexTeam")
            await coding_room.send(embed=welcome_embed)
        finally:
            await db_session.close()

    @coding_group.command(name="end", description="現在のコーディングセッションを終了します")
    async def coding_end(self, interaction: discord.Interaction):
        """End Session (New Ephemeral Confirmation)"""
        user_id = str(interaction.user.id)
        session_uuid = self.session_manager.get_user_active_session(user_id)
        
        if not session_uuid:
            await interaction.response.send_message("❌ アクティブなセッションが見つかりません。", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="⚠️ セッション終了確認",
            description="本当にセッションを終了しますか？\n終了するとこのチャンネルは削除されます。",
            color=discord.Color.red()
        )
        embed.set_footer(text="Made by RovaexTeam")
        
        class ConfirmView(discord.ui.View):
            def __init__(self, session_manager, session_uuid, user_id):
                super().__init__(timeout=60)
                self.session_manager = session_manager
                self.session_uuid = session_uuid
                self.user_id = user_id
            
            @discord.ui.button(label="はい", style=discord.ButtonStyle.danger, emoji="✅")
            async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                if str(interaction.user.id) != self.user_id:
                    await interaction.response.send_message("この操作は実行者本人のみ可能です。", ephemeral=True)
                    return
                
                # データベースセッションを取得して終了処理
                db_session = self.session_manager.bot.db_manager.get_session()
                try:
                    await self.session_manager.close_session(db_session, self.session_uuid)
                    await db_session.commit()
                finally:
                    await db_session.close()
                
                await interaction.response.edit_message(content="✅ セッションを終了しました。", embed=None, view=None)
            
            @discord.ui.button(label="いいえ", style=discord.ButtonStyle.secondary, emoji="❌")
            async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                if str(interaction.user.id) != self.user_id:
                    await interaction.response.send_message("この操作は実行者本人のみ可能です。", ephemeral=True)
                    return
                
                await interaction.response.edit_message(content="セッションの終了をキャンセルしました。", embed=None, view=None)
        
        view = ConfirmView(self.session_manager, session_uuid, user_id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def setup(bot: commands.Bot):
    """Setup the cog"""
    cog = CodingCog(bot)
    await bot.add_cog(cog)
