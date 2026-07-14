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

logger = setup_logger(__name__)


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
    
    def _check_coding_room(self, interaction: discord.Interaction, session_uuid: str) -> bool:
        """
        Check if command is being used in the correct CodingRoom
        
        Args:
            interaction: Discord interaction
            session_uuid: Session UUID
        
        Returns:
            True if in correct room, False otherwise
        """
        session_info = self.session_manager.get_session(session_uuid)
        if session_info and str(interaction.channel.id) != session_info["channel_id"]:
            return False
        return True
    
    @app_commands.command(name="save", description="Save a file in your coding session")
    async def save_file(self, interaction: discord.Interaction, filename: str, content: str):
        """
        Save a file in the current session
        
        Args:
            interaction: Discord interaction
            filename: Name of the file to save
            content: File content
        """
        try:
            user_id = str(interaction.user.id)
            
            # Check if user has active session
            session_uuid = self.session_manager.get_user_active_session(user_id)
            
            if not session_uuid:
                await interaction.response.send_message(
                    "❌ You don't have an active coding session.",
                    ephemeral=True
                )
                return
            
            # Check if this command is being used in the correct CodingRoom
            if not self._check_coding_room(interaction, session_uuid):
                await interaction.response.send_message(
                    "❌ This command can only be used in your coding room!",
                    ephemeral=True
                )
                return
            
            # Save file
            file_path = self.file_manager.save_file(session_uuid, filename, content)
            
            # Get file size
            file_size = file_path.stat().st_size
            
            embed = discord.Embed(
                title="✅ File Saved",
                description=f"File `{filename}` has been saved.",
                color=discord.Color.green()
            )
            embed.add_field(name="Filename", value=f"`{filename}`", inline=False)
            embed.add_field(name="Size", value=f"{file_size} bytes", inline=False)
            
            await interaction.response.send_message(embed=embed)
            
            logger.info(f"User {user_id} saved file {filename} in session {session_uuid}")
        
        except Exception as e:
            logger.error(f"Error in save_file: {e}", exc_info=True)
            await interaction.response.send_message(
                f"❌ Error saving file: {str(e)}",
                ephemeral=True
            )
    
    @app_commands.command(name="list", description="List all files in your coding session")
    async def list_files(self, interaction: discord.Interaction):
        """
        List all files in the current session
        
        Args:
            interaction: Discord interaction
        """
        try:
            user_id = str(interaction.user.id)
            
            # Check if user has active session
            session_uuid = self.session_manager.get_user_active_session(user_id)
            
            if not session_uuid:
                await interaction.response.send_message(
                    "❌ You don't have an active coding session.",
                    ephemeral=True
                )
                return
            
            # Check if this command is being used in the correct CodingRoom
            if not self._check_coding_room(interaction, session_uuid):
                await interaction.response.send_message(
                    "❌ This command can only be used in your coding room!",
                    ephemeral=True
                )
                return
            
            # List files
            files = self.file_manager.list_files(session_uuid)
            
            if not files:
                await interaction.response.send_message("📁 No files in this session yet.")
                return
            
            # Get session size
            session_size = self.file_manager.get_session_size(session_uuid)
            
            file_list = "\n".join([f"• `{f}`" for f in files])
            
            embed = discord.Embed(
                title="📁 Session Files",
                description=file_list,
                color=discord.Color.blue()
            )
            embed.add_field(name="File Count", value=str(len(files)), inline=True)
            embed.add_field(name="Total Size", value=f"{session_size} bytes", inline=True)
            
            await interaction.response.send_message(embed=embed)
        
        except Exception as e:
            logger.error(f"Error in list_files: {e}", exc_info=True)
            await interaction.response.send_message(
                f"❌ Error listing files: {str(e)}",
                ephemeral=True
            )
    
    @app_commands.command(name="download", description="Download all session files as ZIP")
    async def download_files(self, interaction: discord.Interaction):
        """
        Download all session files as ZIP
        
        Args:
            interaction: Discord interaction
        """
        try:
            user_id = str(interaction.user.id)
            
            # Check if user has active session
            session_uuid = self.session_manager.get_user_active_session(user_id)
            
            if not session_uuid:
                await interaction.response.send_message(
                    "❌ You don't have an active coding session.",
                    ephemeral=True
                )
                return
            
            # Check if this command is being used in the correct CodingRoom
            if not self._check_coding_room(interaction, session_uuid):
                await interaction.response.send_message(
                    "❌ This command can only be used in your coding room!",
                    ephemeral=True
                )
                return
            
            # Check if there are any files
            files = self.file_manager.list_files(session_uuid)
            
            if not files:
                await interaction.response.send_message(
                    "❌ No files to download in this session.",
                    ephemeral=True
                )
                return
            
            # Defer response
            await interaction.response.defer()
            
            zip_path = self.file_manager.create_zip(session_uuid)
            
            # Check file size (Discord limit is 25MB)
            zip_size = zip_path.stat().st_size
            
            if zip_size > 25 * 1024 * 1024:
                await interaction.followup.send(
                    f"❌ ZIP file is too large ({zip_size / 1024 / 1024:.1f}MB). "
                    f"Discord limit is 25MB."
                )
                return
            
            # Send file
            file = discord.File(zip_path, filename=f"{session_uuid}.zip")
            
            embed = discord.Embed(
                title="✅ Files Ready for Download",
                description=f"Your session files are ready to download.",
                color=discord.Color.green()
            )
            embed.add_field(name="File Count", value=str(len(files)), inline=True)
            embed.add_field(name="ZIP Size", value=f"{zip_size / 1024:.1f}KB", inline=True)
            
            await interaction.followup.send(embed=embed, file=file)
            
            logger.info(f"User {user_id} downloaded files from session {session_uuid}")
        
        except Exception as e:
            logger.error(f"Error in download_files: {e}", exc_info=True)
            await interaction.followup.send(f"❌ Error downloading files: {str(e)}")
    
    @app_commands.command(name="get", description="Get content of a specific file")
    async def get_file(self, interaction: discord.Interaction, filename: str):
        """
        Get content of a specific file
        
        Args:
            interaction: Discord interaction
            filename: Name of the file
        """
        try:
            user_id = str(interaction.user.id)
            
            # Check if user has active session
            session_uuid = self.session_manager.get_user_active_session(user_id)
            
            if not session_uuid:
                await interaction.response.send_message(
                    "❌ You don't have an active coding session.",
                    ephemeral=True
                )
                return
            
            # Check if this command is being used in the correct CodingRoom
            if not self._check_coding_room(interaction, session_uuid):
                await interaction.response.send_message(
                    "❌ This command can only be used in your coding room!",
                    ephemeral=True
                )
                return
            
            # Get file
            content = self.file_manager.get_file(session_uuid, filename)
            
            if content is None:
                await interaction.response.send_message(
                    f"❌ File not found: `{filename}`",
                    ephemeral=True
                )
                return
            
            # Send file content (split if too long)
            if len(content) > 2000:
                # Send as code blocks
                chunks = [content[i:i+1990] for i in range(0, len(content), 1990)]
                
                await interaction.response.send_message(
                    f"📄 File: `{filename}` (Part 1/{len(chunks)})"
                )
                
                for i, chunk in enumerate(chunks, 1):
                    await interaction.followup.send(f"```\n{chunk}\n```")
                    
                    if i < len(chunks):
                        await interaction.followup.send(f"(Part {i+1}/{len(chunks)})")
            else:
                await interaction.response.send_message(
                    f"📄 File: `{filename}`\n```\n{content}\n```"
                )
        
        except Exception as e:
            logger.error(f"Error in get_file: {e}", exc_info=True)
            await interaction.response.send_message(
                f"❌ Error retrieving file: {str(e)}",
                ephemeral=True
            )


async def setup(bot: commands.Bot):
    """Setup function for loading cog"""
    await bot.add_cog(FileCog(bot))
