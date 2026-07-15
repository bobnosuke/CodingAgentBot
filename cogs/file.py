"""
File management commands for CoderAgent
Handles file operations in coding sessions
"""
import discord
from discord.ext import commands
from discord import app_commands
from logger import setup_logger
from modules.file.manager import FileManager
from modules.session.manager import SessionManager
from pathlib import Path
import zipfile
import io

logger = setup_logger(__name__)


class FileSelectView(discord.ui.View):
    """View for file selection with multi-select"""
    
    def __init__(self, files: list, session_uuid: str, file_manager: FileManager, user_id: int):
        super().__init__(timeout=300)
        self.files = files
        self.session_uuid = session_uuid
        self.file_manager = file_manager
        self.user_id = user_id
        
        # Create select menu with file options
        options = [
            discord.SelectOption(label=f, value=f, emoji="📄")
            for f in files
        ]
        
        select = discord.ui.Select(
            placeholder="ダウンロードするファイルを選択してください",
            options=options,
            max_values=len(files),
            custom_id="file_select"
        )
        select.callback = self.select_callback
        self.add_item(select)
        
        # Add "Download All" button
        download_all_btn = discord.ui.Button(label="全てダウンロード", style=discord.ButtonStyle.green, emoji="⬇️")
        download_all_btn.callback = self.download_all_callback
        self.add_item(download_all_btn)

    async def _send_zip(self, interaction: discord.Interaction, selected_files: list):
        """Helper to create and send ZIP file"""
        if not selected_files:
            # 既存のメッセージを更新してエラー通知
            await interaction.edit_original_response(content="❌ ファイルが選択されていません。", view=self)
            return

        try:
            zip_buffer = io.BytesIO()
            session_dir = self.file_manager.base_storage_dir / self.session_uuid
            
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for file in selected_files:
                    file_path = session_dir / file
                    if file_path.exists():
                        zip_file.write(file_path, arcname=file)
            
            zip_buffer.seek(0)
            # ZIPファイル送信は「新規送信」として扱う（編集ではファイルを送れないため）
            # ただし、元のメッセージを「送信完了」に更新する
            await interaction.edit_original_response(content=f"✅ {len(selected_files)}個のファイルをZIPで準備しました。以下からダウンロードしてください。", view=None)
            await interaction.followup.send(
                file=discord.File(zip_buffer, filename=f"session_{self.session_uuid[:8]}.zip"),
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error creating ZIP in FileSelectView: {e}")
            await interaction.edit_original_response(content=f"❌ ZIP作成中にエラーが発生しました: {str(e)}", view=None)

    async def select_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("この操作は実行者本人のみ可能です。", ephemeral=True)
            return
            
        selected_files = interaction.data["values"]
        await interaction.response.defer(ephemeral=True)
        await self._send_zip(interaction, selected_files)
    
    async def download_all_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("この操作は実行者本人のみ可能です。", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        await self._send_zip(interaction, self.files)


class FileCog(commands.Cog):
    """Cog for file management commands"""
    
    def __init__(self, bot: commands.Bot):
        """
        Initialize file cog
        
        Args:
            bot: Discord bot instance
        """
        self.bot = bot
        self.file_manager = FileManager()
        self.session_manager = SessionManager(bot)
    
    def _check_coding_room(self, message: discord.Message, session_uuid: str) -> bool:
        """
        Check if command is being used in the correct CodingRoom
        """
        session_info = self.session_manager.get_session(session_uuid)
        if session_info and str(message.channel.id) != session_info["channel_id"]:
            return False
        return True
    
    @commands.command(name="list", description="セッション内のファイル一覧を表示します")
    async def list_files(self, ctx: commands.Context):
        """List all files in the current session"""
        try:
            user_id = str(ctx.author.id)
            session_uuid = self.session_manager.get_user_active_session(user_id)
            
            if not session_uuid:
                await ctx.send("❌ You don't have an active coding session.")
                return
            
            if not self._check_coding_room(ctx.message, session_uuid):
                await ctx.send("❌ This command can only be used in your coding room!")
                return
            
            files = self.file_manager.list_files(session_uuid)
            
            if not files:
                await ctx.send("📭 No files in this session yet.")
                return
            
            embed = discord.Embed(
                title="📋 Files in Session",
                description=f"Total: {len(files)} file(s)",
                color=discord.Color.blue()
            )
            
            for file in files:
                file_path = Path(self.file_manager.base_storage_dir / session_uuid / file)
                if file_path.exists():
                    file_size = file_path.stat().st_size
                    embed.add_field(
                        name=f"📄 {file}",
                        value=f"Size: {file_size} bytes",
                        inline=False
                    )
            
            embed.set_footer(text="Made by RovaexTeam")
            await ctx.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in list_files: {e}", exc_info=True)
            await ctx.send(f"❌ Error listing files: {str(e)}")
    
    @commands.command(name="get", description="ファイルの内容を取得します")
    async def get_file(self, ctx: commands.Context, filename: str):
        """Get file content"""
        try:
            user_id = str(ctx.author.id)
            session_uuid = self.session_manager.get_user_active_session(user_id)
            
            if not session_uuid:
                await ctx.send("❌ You don't have an active coding session.")
                return
            
            if not self._check_coding_room(ctx.message, session_uuid):
                await ctx.send("❌ This command can only be used in your coding room!")
                return
            
            content = self.file_manager.get_file(session_uuid, filename)
            
            if not content:
                await ctx.send(f"❌ File `{filename}` not found.")
                return
            
            if len(content) > 2000:
                file_obj = io.BytesIO(content.encode('utf-8'))
                await ctx.send(file=discord.File(file_obj, filename=filename))
            else:
                embed = discord.Embed(
                    title=f"📄 {filename}",
                    description=f"```\n{content}\n```",
                    color=discord.Color.blue()
                )
                embed.set_footer(text="Made by RovaexTeam")
                await ctx.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in get_file: {e}", exc_info=True)
            await ctx.send(f"❌ Error retrieving file: {str(e)}")
    
    @commands.command(name="download", description="ファイルをZIP形式でダウンロードします")
    async def download_files(self, ctx: commands.Context):
        """Download files as ZIP"""
        try:
            user_id = str(ctx.author.id)
            session_uuid = self.session_manager.get_user_active_session(user_id)
            
            if not session_uuid:
                await ctx.send("❌ You don't have an active coding session.")
                return
            
            if not self._check_coding_room(ctx.message, session_uuid):
                await ctx.send("❌ This command can only be used in your coding room!")
                return
            
            files = self.file_manager.list_files(session_uuid)
            
            if not files:
                await ctx.send("📭 No files to download.")
                return
            
            if len(files) == 1:
                session_dir = self.file_manager.base_storage_dir / session_uuid
                file_path = session_dir / files[0]
                await ctx.send(file=discord.File(file_path))
                return
            
            embed = discord.Embed(
                title="⬇️ ファイルダウンロード",
                description="ダウンロードしたいファイルを選択するか、「全てダウンロード」ボタンを押してください。",
                color=discord.Color.green()
            )
            embed.set_footer(text="Made by RovaexTeam")
            
            view = FileSelectView(files, session_uuid, self.file_manager, ctx.author.id)
            await ctx.send(embed=embed, view=view)
        except Exception as e:
            logger.error(f"Error in download_files: {e}", exc_info=True)
            await ctx.send(f"❌ Error downloading files: {str(e)}")
    
    @commands.command(name="close", description="セッションを終了します（確認あり）")
    async def close_session(self, ctx: commands.Context):
        """Close the current coding session with confirmation"""
        try:
            user_id = str(ctx.author.id)
            session_uuid = self.session_manager.get_user_active_session(user_id)
            
            if not session_uuid:
                await ctx.send("❌ You don't have an active coding session.")
                return
            
            if not self._check_coding_room(ctx.message, session_uuid):
                await ctx.send("❌ This command can only be used in your coding room!")
                return
            
            class ConfirmView(discord.ui.View):
                def __init__(self, session_manager, session_uuid, ctx):
                    super().__init__(timeout=60)
                    self.session_manager = session_manager
                    self.session_uuid = session_uuid
                    self.ctx = ctx
                
                @discord.ui.button(label="はい", style=discord.ButtonStyle.danger, emoji="✅")
                async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                    if interaction.user.id != self.ctx.author.id:
                        await interaction.response.send_message("この操作は実行者本人のみ可能です。", ephemeral=True)
                        return
                    
                    await self.session_manager.end_session(self.session_uuid)
                    # 終了通知は既存メッセージを更新
                    await interaction.response.edit_message(content="✅ セッションを終了しました。", embed=None, view=None)
                
                @discord.ui.button(label="いいえ", style=discord.ButtonStyle.secondary, emoji="❌")
                async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                    if interaction.user.id != self.ctx.author.id:
                        await interaction.response.send_message("この操作は実行者本人のみ可能です。", ephemeral=True)
                        return
                    
                    # キャンセル通知も既存メッセージを更新
                    await interaction.response.edit_message(content="セッションの終了をキャンセルしました。", embed=None, view=None)
            
            embed = discord.Embed(
                title="⚠️ セッション終了確認",
                description="本当にセッションを終了しますか？\n終了するとこのチャンネルは削除されます。",
                color=discord.Color.red()
            )
            embed.set_footer(text="Made by RovaexTeam")
            
            view = ConfirmView(self.session_manager, session_uuid, ctx)
            await ctx.send(embed=embed, view=view)
        except Exception as e:
            logger.error(f"Error in close_session: {e}", exc_info=True)
            await ctx.send(f"❌ Error closing session: {str(e)}")


async def setup(bot: commands.Bot):
    """Setup the cog"""
    cog = FileCog(bot)
    await bot.add_cog(cog)
