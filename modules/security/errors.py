import discord
from discord.ext import commands
import logging
import traceback
from datetime import datetime
from typing import Optional, Any

logger = logging.getLogger("CoderAgent")

class ErrorHandler:
    """Centralized error handling for CoderAgent"""
    
    @staticmethod
    async def handle_error(ctx: Any, error: Exception):
        """Handle errors and notify user with an Embed"""
        
        # Handle cases where ctx is already an Interaction (app commands)
        if isinstance(ctx, discord.Interaction):
            interaction = ctx
        else:
            # Get interaction if it exists in Context (prefix commands)
            interaction = getattr(ctx, "interaction", None)
        
        user = getattr(ctx, "author", getattr(ctx, "user", None))
        
        # Determine error type and message
        title = "❌ エラーが発生しました"
        description = "予期せぬエラーが発生しました。管理者にお問い合わせください。"
        color = discord.Color.red()
        
        if isinstance(error, commands.CommandNotFound):
            return  # Ignore unknown commands
            
        elif isinstance(error, commands.MissingPermissions):
            title = "🚫 権限エラー"
            description = "このコマンドを実行する権限がありません。"
            
        elif isinstance(error, commands.NotOwner):
            title = "🚫 権限エラー"
            description = "このコマンドはBotオーナーのみ実行可能です。"
            
        elif isinstance(error, commands.CheckFailure):
            title = "🚫 権限エラー"
            description = "コマンドの実行条件を満たしていません。"
            
        elif isinstance(error, commands.MissingRequiredArgument):
            title = "📝 引数不足"
            description = f"必要な引数が不足しています: `{error.param.name}`"
            
        elif isinstance(error, commands.BadArgument):
            title = "⚠️ 無効な引数"
            description = "引数の形式が正しくありません。"
            
        elif "OpenRouter" in str(error):
            title = "🤖 AI APIエラー"
            description = "AIサービス（OpenRouter）との通信中にエラーが発生しました。APIキーを確認してください。"
            
        # Log the error
        logger.error(f"Error in command {getattr(ctx, 'command', 'unknown')}: {error}")
        logger.error(traceback.format_exc())
        
        # Create Embed
        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text="CoderAgent Error System")
        
        # Send notification
        try:
            if interaction:
                if interaction.response.is_done():
                    await interaction.followup.send(embed=embed, ephemeral=True)
                else:
                    await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await ctx.send(embed=embed)
        except Exception as e:
            logger.error(f"Failed to send error message: {e}")

async def setup_error_handler(bot: commands.Bot):
    """Register the global error handler"""
    @bot.event
    async def on_command_error(ctx, error):
        await ErrorHandler.handle_error(ctx, error)
    
    # Also handle app command errors
    bot.tree.on_error = ErrorHandler.handle_error
