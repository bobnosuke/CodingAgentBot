"""
File management commands for CoderAgent
Handles file operations in coding sessions
"""
import discord
from discord.ext import commands
from logger import setup_logger
from modules.file.manager import FileManager
from modules.session.manager import SessionManager
from modules.database.repository import UserRepository
from modules.utils.i18n import i18n
import zipfile
import io

logger = setup_logger(__name__)


class FileSelectView(discord.ui.View):
    """View for file selection (Ephemeral Panel)"""
    
    def __init__(self, files: list, session_uuid: str, file_manager: FileManager, user_id: int, lang: str):
        super().__init__(timeout=300)
        self.files = files
        self.session_uuid = session_uuid
        self.file_manager = file_manager
        self.user_id = user_id
        self.lang = lang
        
        options = [discord.SelectOption(label=f, value=f, emoji="📄") for f in files[:25]]
        select = discord.ui.Select(
            placeholder=i18n.translate(lang, "FILE.SELECT_FILES"),
            options=options,
            max_values=len(options),
            custom_id="file_select"
        )
        select.callback = self.select_callback
        self.add_item(select)
        
        download_all_btn = discord.ui.Button(label="Download All", style=discord.ButtonStyle.green, emoji="⬇️")
        download_all_btn.callback = self.download_all_callback
        self.add_item(download_all_btn)

    async def _send_zip(self, interaction: discord.Interaction, selected_files: list):
        """Helper to create and send ZIP file (Edit Ephemeral)"""
        if not selected_files:
            await interaction.edit_original_response(content="❌ No files selected.", view=self)
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
            await interaction.edit_original_response(content=i18n.translate(self.lang, "FILE.ZIP_SENT"), view=None)
            await interaction.followup.send(
                file=discord.File(zip_buffer, filename=f"session_{self.session_uuid[:8]}.zip"),
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error creating ZIP: {e}")
            await interaction.edit_original_response(content=i18n.translate(self.lang, "COMMON.ERROR", error=str(e)), view=None)

    async def select_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(i18n.translate(self.lang, "COMMON.PERMISSION_DENIED"), ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        await self._send_zip(interaction, interaction.data["values"])
    
    async def download_all_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(i18n.translate(self.lang, "COMMON.PERMISSION_DENIED"), ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        await self._send_zip(interaction, self.files)


class FileCog(commands.Cog):
    """Cog for file management commands"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.file_manager = FileManager()
        self.session_manager = SessionManager(bot)
    
    async def _get_lang(self, user_id: int):
        db_session = self.bot.db_manager.get_session()
        try:
            user = await UserRepository.get_user_by_discord_id(db_session, str(user_id))
            return user.language if user else "en-US"
        finally:
            await db_session.close()

    @commands.command(name="download")
    async def download_files(self, ctx: commands.Context):
        """Download Files"""
        lang = await self._get_lang(ctx.author.id)
        session_uuid = self.session_manager.get_user_active_session(str(ctx.author.id))
        
        if not session_uuid:
            await ctx.send("❌ No active session found.")
            return
        
        files = self.file_manager.list_files(session_uuid)
        if not files:
            await ctx.send("📭 No files found.")
            return
        
        embed = discord.Embed(
            title=i18n.translate(lang, "FILE.DOWNLOAD_TITLE"),
            description=i18n.translate(lang, "FILE.DOWNLOAD_DESC"),
            color=discord.Color.green()
        )
        embed.set_footer(text="Made by RovaexTeam")
        
        view = FileSelectView(files, session_uuid, self.file_manager, ctx.author.id, lang)
        await ctx.send(embed=embed, view=view)
    
    @commands.command(name="close")
    async def close_session(self, ctx: commands.Context):
        """Close Session"""
        lang = await self._get_lang(ctx.author.id)
        session_uuid = self.session_manager.get_user_active_session(str(ctx.author.id))
        
        if not session_uuid:
            await ctx.send("❌ No active session found.")
            return
        
        embed = discord.Embed(
            title=i18n.translate(lang, "FILE.CLOSE_CONFIRM"),
            color=discord.Color.red()
        )
        embed.set_footer(text="Made by RovaexTeam")
        
        class ConfirmView(discord.ui.View):
            def __init__(self, session_manager, session_uuid, user_id, lang):
                super().__init__(timeout=60)
                self.session_manager = session_manager
                self.session_uuid = session_uuid
                self.user_id = user_id
                self.lang = lang
            
            @discord.ui.button(label=i18n.translate(lang, "COMMON.YES"), style=discord.ButtonStyle.danger, emoji="✅")
            async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                if interaction.user.id != self.user_id:
                    await interaction.response.send_message(i18n.translate(self.lang, "COMMON.PERMISSION_DENIED"), ephemeral=True)
                    return
                
                db_session = self.session_manager.bot.db_manager.get_session()
                try:
                    await self.session_manager.close_session(db_session, self.session_uuid)
                    await db_session.commit()
                finally:
                    await db_session.close()
                await interaction.response.edit_message(content=i18n.translate(self.lang, "CODING.END_SUCCESS"), embed=None, view=None)
            
            @discord.ui.button(label=i18n.translate(lang, "COMMON.NO"), style=discord.ButtonStyle.secondary, emoji="❌")
            async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                if interaction.user.id != self.user_id:
                    await interaction.response.send_message(i18n.translate(self.lang, "COMMON.PERMISSION_DENIED"), ephemeral=True)
                    return
                await interaction.response.edit_message(content=i18n.translate(self.lang, "CODING.END_CANCEL"), embed=None, view=None)
        
        view = ConfirmView(self.session_manager, session_uuid, ctx.author.id, lang)
        await ctx.send(embed=embed, view=view)


async def setup(bot: commands.Bot):
    """Setup the cog"""
    await bot.add_cog(FileCog(bot))
