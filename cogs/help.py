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
    
    @app_commands.command(name="guide", description="ヘルプガイドを表示します")
    async def guide_command(self, interaction: discord.Interaction, topic: str = None):
        """
        ヘルプ情報を表示します
        
        Args:
            interaction: Discord interaction
            topic: オプションのヘルプトピック
        """
        if topic is None:
            # Main help menu
            embed = discord.Embed(
                title="🤖 CoderAgent - ヘルプメニュー",
                description="Discord AI コーディングアシスタント",
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="⚙️ 設定",
                value="• `/setting` - APIキーやAIモデルの設定を行います",
                inline=False
            )
            
            embed.add_field(
                name="💻 コーディングコマンド",
                value="• `/coding start` - 新しいコーディングセッションを開始します\n"
                      "• `/coding chat` - AIとチャットします（CodingRoom内では不要）\n"
                      "• `/coding end` - セッションを終了します",
                inline=False
            )
            
            embed.add_field(
                name="📁 ファイル管理",
                value="• `!save` - ファイルを保存します\n"
                      "• `!list` - セッション内のファイル一覧を表示します\n"
                      "• `!get` - ファイルの内容を取得します\n"
                      "• `!download` - ファイルをZIPでダウンロードします",
                inline=False
            )
            
            embed.add_field(
                name="ℹ️ 情報",
                value="• `/guide` - このヘルプメニューを表示します\n"
                      "• `/status` - Botのステータスを表示します\n"
                      "• `/about` - CoderAgentについて",
                inline=False
            )
            
            embed.set_footer(text="特定のトピックについて詳しく知るには /guide <topic> を使用してください")
            
            await interaction.response.send_message(embed=embed)
        
        elif topic.lower() == "setting":
            embed = discord.Embed(
                title="⚙️ 設定",
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="APIキーの登録",
                value="`/setting` コマンドを実行し、表示される「API Key登録」ボタンから登録してください。\n"
                      "APIキーは安全に暗号化されて保存されます。",
                inline=False
            )
            
            embed.add_field(
                name="APIキーの取得方法",
                value="1. https://openrouter.ai/ にアクセス\n"
                      "2. サインアップまたはログイン\n"
                      "3. API Keys セクションへ移動\n"
                      "4. 新しいAPIキーを作成してコピー",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed)
        
        elif topic.lower() == "coding":
            embed = discord.Embed(
                title="💻 コーディングコマンド",
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="セッション開始",
                value="`/coding start [project_name]` を使用します。\n"
                      "あなた専用のプライベートな CodingRoom が作成されます。",
                inline=False
            )
            
            embed.add_field(
                name="AIとチャット",
                value="CodingRoom内では、メッセージを送信するだけでAIと対話できます。\n"
                      "コード生成、解説、デバッグなどを依頼してください。",
                inline=False
            )
            
            embed.add_field(
                name="セッション終了",
                value="`/coding end` を使用します。\n"
                      "セッションを終了し、CodingRoomを削除します。",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed)
        
        elif topic.lower() == "files":
            embed = discord.Embed(
                title="📁 ファイル管理",
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="ファイルを保存",
                value="`!save <ファイル名> <内容>` を使用します。\n"
                      "セッション内にコードやテキストを保存できます。",
                inline=False
            )
            
            embed.add_field(
                name="ファイル一覧",
                value="`!list` を使用します。\n"
                      "現在のセッション内の全ファイルを確認できます。",
                inline=False
            )
            
            embed.add_field(
                name="ダウンロード",
                value="`!download` を使用します。\n"
                      "セッション内のファイルをZIP形式で取得できます。",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed)
        
        else:
            await interaction.response.send_message(
                f"❓ 不明なトピックです: `{topic}`\n`/guide` でメインメニューを表示してください。",
                ephemeral=True
            )
    
    @app_commands.command(name="about", description="CoderAgentについて表示します")
    async def about_command(self, interaction: discord.Interaction):
        """
        CoderAgentに関する情報を表示します
        
        Args:
            interaction: Discord interaction
        """
        try:
            embed = discord.Embed(
                title="🤖 CoderAgent について",
                description="Discord AI コーディングアシスタント",
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="CoderAgentとは？",
                value="CoderAgentは、コード作成を支援するAI搭載のDiscord Botです。"
                      "Claude Codeのような体験を、Discord上で直接提供します。",
                inline=False
            )
            
            embed.add_field(
                name="主な機能",
                value="✨ AIによるコード生成\n"
                      "✨ プライベートなコーディングルーム\n"
                      "✨ セッション管理\n"
                      "✨ 安全なAPIキーの暗号化保存\n"
                      "✨ ファイル管理機能",
                inline=False
            )
            
            embed.add_field(
                name="使用テクノロジー",
                value="Built with discord.py and OpenRouter API",
                inline=False
            )
            
            embed.add_field(
                name="始め方",
                value="1. APIキーを登録: `/setting` から登録\n"
                      "2. セッションを開始: `/coding start`を実行\n"
                      "3. AIと対話: CodingRoom内でメッセージを送信",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            logger.error(f"Error in about command: {e}", exc_info=True)
            if not interaction.response.is_done():
                await interaction.response.send_message(f"❌ エラーが発生しました: {str(e)}", ephemeral=True)
            else:
                await interaction.followup.send(f"❌ エラーが発生しました: {str(e)}", ephemeral=True)
    
    @app_commands.command(name="status", description="Botのステータスを表示します")
    async def status_command(self, interaction: discord.Interaction):
        """
        Botのステータスを表示します
        
        Args:
            interaction: Discord interaction
        """
        embed = discord.Embed(
            title="📊 Bot ステータス",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="Bot名",
            value=self.bot.user.name,
            inline=True
        )
        
        embed.add_field(
            name="Bot ID",
            value=self.bot.user.id,
            inline=True
        )
        
        embed.add_field(
            name="サーバー数",
            value=len(self.bot.guilds),
            inline=True
        )
        
        embed.add_field(
            name="レイテンシ",
            value=f"{self.bot.latency * 1000:.0f}ms",
            inline=True
        )
        
        embed.add_field(
            name="状態",
            value="✅ オンライン",
            inline=True
        )
        
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    """Setup function for loading cog"""
    await bot.add_cog(HelpCog(bot))
