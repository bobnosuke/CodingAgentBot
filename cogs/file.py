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
            await interaction.followup.send("❌ ファイルが選択されていません。", ephemeral=True)
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
            await interaction.followup.send(
                content=f"✅ {len(selected_files)}個のファイルをZIPで送信します。",
                file=discord.File(zip_buffer, filename=f"session_{self.session_uuid[:8]}.zip"),
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error creating ZIP in FileSelectView: {e}")
            await interaction.followup.send(f"❌ ZIP作成中にエラーが発生しました: {str(e)}", ephemeral=True)

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
        
        Args:
            message: Discord message
            session_uuid: Session UUID
        
        Returns:
            True if in correct room, False otherwise
        """
        session_info = self.session_manager.get_session(session_uuid)
        if session_info and str(message.channel.id) != session_info["channel_id"]:
            return False
        return True
    
    @commands.command(name="list", description="List all files in your coding session")
    async def list_files(self, ctx: commands.Context):
        """
        List all files in the current session
        
        Args:
            ctx: Command context
        """
        try:
            user_id = str(ctx.author.id)
            
            # Check if user has active session
            session_uuid = self.session_manager.get_user_active_session(user_id)
            
            if not session_uuid:
                await ctx.send("❌ You don't have an active coding session.")
                return
            
            # Check if this command is being used in the correct CodingRoom
            if not self._check_coding_room(ctx.message, session_uuid):
                await ctx.send("❌ This command can only be used in your coding room!")
                return
            
            # Get file list
            files = self.file_manager.list_files(session_uuid)
            
            if not files:
                await ctx.send("📭 No files in this session yet.")
                return
            
            embed = discord.Embed(
                title="📋 Files in Session",
                description=f"Total: {len(files)} file(s)",
                color=discord.Color.blue()
            )
            
            # Display files in hierarchical format
            for file in files:
                file_path = Path(file)
                file_size = file_path.stat().st_size
                embed.add_field(
                    name=f"📄 {file}",
                    value=f"Size: {file_size} bytes",
                    inline=False
                )
            
            embed.set_footer(text="Made by RovaexTeam")
            await ctx.send(embed=embed)
            
            logger.info(f"User {user_id} listed files in session {session_uuid}")
        
        except Exception as e:
            logger.error(f"Error in list_files: {e}", exc_info=True)
            await ctx.send(f"❌ Error listing files: {str(e)}")
    
    @commands.command(name="get", description="Get file content")
    async def get_file(self, ctx: commands.Context, filename: str):
        """
        Get file content
        
        Args:
            ctx: Command context
            filename: Name of the file to retrieve
        """
        try:
            user_id = str(ctx.author.id)
            
            # Check if user has active session
            session_uuid = self.session_manager.get_user_active_session(user_id)
            
            if not session_uuid:
                await ctx.send("❌ You don't have an active coding session.")
                return
            
            # Check if this command is being used in the correct CodingRoom
            if not self._check_coding_room(ctx.message, session_uuid):
                await ctx.send("❌ This command can only be used in your coding room!")
                return
            
            # Get file content
            content = self.file_manager.get_file(session_uuid, filename)
            
            if not content:
                await ctx.send(f"❌ File `{filename}` not found.")
                return
            
            # Send content as code block or file
            if len(content) > 2000:
                # Send as file
                file_obj = io.BytesIO(content.encode('utf-8'))
                await ctx.send(file=discord.File(file_obj, filename=filename))
            else:
                # Send as code block
                embed = discord.Embed(
                    title=f"📄 {filename}",
                    description=f"```\n{content}\n```",
                    color=discord.Color.blue()
                )
                embed.set_footer(text="Made by RovaexTeam")
                await ctx.send(embed=embed)
            
            logger.info(f"User {user_id} retrieved file {filename} in session {session_uuid}")
        
        except Exception as e:
            logger.error(f"Error in get_file: {e}", exc_info=True)
            await ctx.send(f"❌ Error retrieving file: {str(e)}")
    
    @commands.command(name="download", description="Download files as ZIP")
    async def download_files(self, ctx: commands.Context):
        """
        Download files as ZIP
        
        Args:
            ctx: Command context
        """
        try:
            user_id = str(ctx.author.id)
            
            # Check if user has active session
            session_uuid = self.session_manager.get_user_active_session(user_id)
            
            if not session_uuid:
                await ctx.send("❌ You don't have an active coding session.")
                return
            
            # Check if this command is being used in the correct CodingRoom
            if not self._check_coding_room(ctx.message, session_uuid):
                await ctx.send("❌ This command can only be used in your coding room!")
                return
            
            # Get file list
            files = self.file_manager.list_files(session_uuid)
            
            if not files:
                await ctx.send("📭 No files to download.")
                return
            
            # If only one file, send it directly
            if len(files) == 1:
                session_dir = self.file_manager.base_storage_dir / session_uuid
                file_path = session_dir / files[0]
                await ctx.send(file=discord.File(file_path))
                logger.info(f"User {user_id} downloaded single file in session {session_uuid}")
                return
            
            # Embed for file selection
            embed = discord.Embed(
                title="⬇️ ファイルダウンロード",
                description="ダウンロードしたいファイルを選択するか、「全てダウンロード」ボタンを押してください。",
                color=discord.Color.green()
            )
            embed.set_footer(text="Made by RovaexTeam")
            
            view = FileSelectView(files, session_uuid, self.file_manager, ctx.author.id)
            await ctx.send(embed=embed, view=view)
            
            logger.info(f"User {user_id} opened download view in session {session_uuid}")
        
        except Exception as e:
            logger.error(f"Error in download_files: {e}", exc_info=True)
            await ctx.send(f"❌ Error downloading files: {str(e)}")
    
    @commands.command(name="close", description="Close your coding session")
    async def close_session(self, ctx: commands.Context):
        """
        Close the current coding session with confirmation
        
        Args:
            ctx: Command context
        """
        try:
            user_id = str(ctx.author.id)
            
            # Check if user has active session
            session_uuid = self.session_manager.get_user_active_session(user_id)
            
            if not session_uuid:
                await ctx.send("❌ You don't have an active coding session.")
                return
            
            # Check if this command is being used in the correct CodingRoom
            if not self._check_coding_room(ctx.message, session_uuid):
                await ctx.send("❌ This command can only be used in your coding room!")
                return
            
            # Create confirmation view
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
                    await interaction.response.send_message("✅ セッションを終了しました。", ephemeral=True)
                
                @discord.ui.button(label="いいえ", style=discord.ButtonStyle.secondary, emoji="❌")
                async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                    if interaction.user.id != self.ctx.author.id:
                        await interaction.response.send_message("この操作は実行者本人のみ可能です。", ephemeral=True)
                        return
                    
                    await interaction.response.send_message("セッションの終了をキャンセルしました。", ephemeral=True)
            
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
    
    @commands.command(name="readme", description="Show project README")
    async def show_readme(self, ctx: commands.Context):
        """
        Show project README
        
        Args:
            ctx: Command context
        """
        try:
            user_id = str(ctx.author.id)
            
            # Check if user has active session
            session_uuid = self.session_manager.get_user_active_session(user_id)
            
            if not session_uuid:
                await ctx.send("❌ You don't have an active coding session.")
                return
            
            # Check if this command is being used in the correct CodingRoom
            if not self._check_coding_room(ctx.message, session_uuid):
                await ctx.send("❌ This command can only be used in your coding room!")
                return
            
            # Try to get README
            readme_content = self.file_manager.get_file(session_uuid, "README.md")
            
            if not readme_content:
                await ctx.send("📭 No README.md found in this session.")
                return
            
            # Send README content
            if len(readme_content) > 2000:
                file_obj = io.BytesIO(readme_content.encode('utf-8'))
                await ctx.send(file=discord.File(file_obj, filename="README.md"))
            else:
                embed = discord.Embed(
                    title="📖 README.md",
                    description=readme_content,
                    color=discord.Color.blue()
                )
                embed.set_footer(text="Made by RovaexTeam")
                await ctx.send(embed=embed)
            
            logger.info(f"User {user_id} viewed README in session {session_uuid}")
        
        except Exception as e:
            logger.error(f"Error in show_readme: {e}", exc_info=True)
            await ctx.send(f"❌ Error showing README: {str(e)}")


async def setup(bot: commands.Bot):
    cog = FileCog(bot)
    await bot.add_cog(cog)
