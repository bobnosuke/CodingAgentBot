"""
File management commands for CoderAgent
Handles file operations in coding sessions
"""
import discord
from discord.ext import commands
from logger import setup_logger
from modules.security.permissions import user_command
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
    
    @commands.command(name="save")
    @user_command
    async def save_file(self, ctx: commands.Context, filename: str, *, content: str):
        """
        Save a file in the current session
        
        Args:
            ctx: Command context
            filename: Name of the file to save
            content: File content
        """
        try:
            user_id = str(ctx.author.id)
            
            # Check if user has active session
            session_uuid = self.session_manager.get_user_active_session(user_id)
            
            if not session_uuid:
                await ctx.send("❌ You don't have an active coding session.")
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
            
            await ctx.send(embed=embed)
            
            logger.info(f"User {user_id} saved file {filename} in session {session_uuid}")
        
        except Exception as e:
            logger.error(f"Error in save_file: {e}", exc_info=True)
            await ctx.send(f"❌ Error saving file: {str(e)}")
    
    @commands.command(name="list")
    @user_command
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
            
            # List files
            files = self.file_manager.list_files(session_uuid)
            
            if not files:
                await ctx.send("📁 No files in this session yet.")
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
            
            await ctx.send(embed=embed)
        
        except Exception as e:
            logger.error(f"Error in list_files: {e}", exc_info=True)
            await ctx.send(f"❌ Error listing files: {str(e)}")
    
    @commands.command(name="download")
    @user_command
    async def download_files(self, ctx: commands.Context):
        """
        Download all session files as ZIP
        
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
            
            # Check if there are any files
            files = self.file_manager.list_files(session_uuid)
            
            if not files:
                await ctx.send("❌ No files to download in this session.")
                return
            
            # Create ZIP
            await ctx.defer()
            
            zip_path = self.file_manager.create_zip(session_uuid)
            
            # Check file size (Discord limit is 25MB)
            zip_size = zip_path.stat().st_size
            
            if zip_size > 25 * 1024 * 1024:
                await ctx.followup.send(
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
            
            await ctx.followup.send(embed=embed, file=file)
            
            logger.info(f"User {user_id} downloaded files from session {session_uuid}")
        
        except Exception as e:
            logger.error(f"Error in download_files: {e}", exc_info=True)
            await ctx.followup.send(f"❌ Error downloading files: {str(e)}")
    
    @commands.command(name="get")
    @user_command
    async def get_file(self, ctx: commands.Context, filename: str):
        """
        Get content of a specific file
        
        Args:
            ctx: Command context
            filename: Name of the file
        """
        try:
            user_id = str(ctx.author.id)
            
            # Check if user has active session
            session_uuid = self.session_manager.get_user_active_session(user_id)
            
            if not session_uuid:
                await ctx.send("❌ You don't have an active coding session.")
                return
            
            # Get file
            content = self.file_manager.get_file(session_uuid, filename)
            
            if content is None:
                await ctx.send(f"❌ File not found: `{filename}`")
                return
            
            # Send file content (split if too long)
            if len(content) > 2000:
                # Send as code blocks
                chunks = [content[i:i+1990] for i in range(0, len(content), 1990)]
                
                await ctx.send(f"📄 File: `{filename}` (Part 1/{len(chunks)})")
                
                for i, chunk in enumerate(chunks, 1):
                    await ctx.send(f"```\n{chunk}\n```")
                    
                    if i < len(chunks):
                        await ctx.send(f"(Part {i+1}/{len(chunks)})")
            else:
                await ctx.send(f"📄 File: `{filename}`\n```\n{content}\n```")
        
        except Exception as e:
            logger.error(f"Error in get_file: {e}", exc_info=True)
            await ctx.send(f"❌ Error retrieving file: {str(e)}")


async def setup(bot: commands.Bot):
    """Setup function for loading cog"""
    await bot.add_cog(FileCog(bot))
