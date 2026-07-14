"""
Help and information commands for CoderAgent
"""
import discord
from discord.ext import commands
from discord import app_commands
from logger import setup_logger

logger = setup_logger(__name__)


class HelpCog(commands.Cog):
    """Cog for help and information commands"""
    
    def __init__(self, bot: commands.Bot):
        """
        Initialize help cog
        
        Args:
            bot: Discord bot instance
        """
        self.bot = bot
    
    @app_commands.command(name="guide", description="Show help guide")
    async def guide_command(self, interaction: discord.Interaction, topic: str = None):
        """
        Display help information
        
        Args:
            interaction: Discord interaction
            topic: Optional help topic
        """
        if topic is None:
            # Main help menu
            embed = discord.Embed(
                title="🤖 CoderAgent - Help Menu",
                description="Discord AI Coding Assistant",
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="🔑 API Key Management",
                value="• `/api-key register` - Register your OpenRouter API key\n"
                      "• `/api-key remove` - Remove your API key",
                inline=False
            )
            
            embed.add_field(
                name="💻 Coding Commands",
                value="• `/coding start` - Start a new coding session\n"
                      "• `/coding chat` - Chat with AI in your session\n"
                      "• `/coding end` - End your current session",
                inline=False
            )
            
            embed.add_field(
                name="📁 File Management",
                value="• `/save` - Save a file\n"
                      "• `/list` - List all files in session\n"
                      "• `/get` - Get file content\n"
                      "• `/download` - Download all files as ZIP",
                inline=False
            )
            
            embed.add_field(
                name="ℹ️ Information",
                value="• `/guide` - Show this help menu\n"
                      "• `/status` - Show bot status\n"
                      "• `/about` - About CoderAgent",
                inline=False
            )
            
            embed.set_footer(text="Use /guide <topic> for more details on a specific topic")
            
            await interaction.response.send_message(embed=embed)
        
        elif topic.lower() == "api-key":
            embed = discord.Embed(
                title="🔑 API Key Management",
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="Register API Key",
                value="Use `/api-key register <your_openrouter_api_key>`\n"
                      "Your API key is securely encrypted and stored.",
                inline=False
            )
            
            embed.add_field(
                name="How to get an API key?",
                value="1. Visit https://openrouter.ai/\n"
                      "2. Sign up or log in\n"
                      "3. Go to API Keys section\n"
                      "4. Create a new API key\n"
                      "5. Copy and register it with the bot",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed)
        
        elif topic.lower() == "coding":
            embed = discord.Embed(
                title="💻 Coding Commands",
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="Start Session",
                value="Use `/coding start [project_name]`\n"
                      "Creates a private coding room for you.",
                inline=False
            )
            
            embed.add_field(
                name="Chat with AI",
                value="Use `/coding chat <your_message>`\n"
                      "Ask the AI to generate code, explain concepts, or debug.",
                inline=False
            )
            
            embed.add_field(
                name="End Session",
                value="Use `/coding end`\n"
                      "Closes your session and deletes the coding room.",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed)
        
        elif topic.lower() == "files":
            embed = discord.Embed(
                title="📁 File Management",
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="Save File",
                value="Use `/save <filename> <content>`\n"
                      "Save code or text to a file in your session.",
                inline=False
            )
            
            embed.add_field(
                name="List Files",
                value="Use `/list`\n"
                      "See all files in your current session.",
                inline=False
            )
            
            embed.add_field(
                name="Download Files",
                value="Use `/download`\n"
                      "Download all session files as a ZIP archive.",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed)
        
        else:
            await interaction.response.send_message(
                f"❓ Unknown help topic: `{topic}`\nUse `/guide` for the main menu.",
                ephemeral=True
            )
    
    @app_commands.command(name="about", description="About CoderAgent")
    async def about_command(self, interaction: discord.Interaction):
        """
        Display information about CoderAgent
        
        Args:
            interaction: Discord interaction
        """
        embed = discord.Embed(
            title="🤖 About CoderAgent",
            description="Discord AI Coding Assistant",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="What is CoderAgent?",
            value="CoderAgent is an AI-powered Discord bot that helps you write code. "
                  "It provides an experience similar to Claude Code, but directly in Discord.",
            inline=False
        )
        
        embed.add_field(
            name="Features",
            value="✨ AI Code Generation\n"
                  "✨ Private Coding Rooms\n"
                  "✨ Session Management\n"
                  "✨ Secure API Key Storage\n"
                  "✨ File Management",
            inline=False
        )
        
        embed.add_field(
            name="Technology",
            value="Built with discord.py and OpenRouter API",
            inline=False
        )
        
        embed.add_field(
            name="Getting Started",
            value="1. Register your OpenRouter API key: `/api-key register <key>`\n"
                  "2. Start a coding session: `/coding start`\n"
                  "3. Chat with AI: `/coding chat <message>`",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="status", description="Show bot status")
    async def status_command(self, interaction: discord.Interaction):
        """
        Display bot status
        
        Args:
            interaction: Discord interaction
        """
        embed = discord.Embed(
            title="📊 Bot Status",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="Bot Name",
            value=self.bot.user.name,
            inline=True
        )
        
        embed.add_field(
            name="Bot ID",
            value=self.bot.user.id,
            inline=True
        )
        
        embed.add_field(
            name="Guilds",
            value=len(self.bot.guilds),
            inline=True
        )
        
        embed.add_field(
            name="Latency",
            value=f"{self.bot.latency * 1000:.0f}ms",
            inline=True
        )
        
        embed.add_field(
            name="Status",
            value="✅ Online",
            inline=True
        )
        
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    """Setup function for loading cog"""
    await bot.add_cog(HelpCog(bot))
