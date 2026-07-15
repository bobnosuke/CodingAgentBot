import discord
import json
from modules.ai.agent import CodingAgent

class RequirementApprovalView(discord.ui.View):
    """View for approving or refining requirements defined by Gemini"""
    
    def __init__(self, agent: CodingAgent, requirement_json: dict, user_id: str, lang: str):
        super().__init__(timeout=600)
        self.agent = agent
        self.requirement_json = requirement_json
        self.user_id = user_id
        self.lang = lang
        self.refine_count = 0
        
    @discord.ui.button(label="実装を開始する", style=discord.ButtonStyle.green, emoji="🚀")
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.user_id:
            return await interaction.response.send_message("この操作は実行者のみ可能です。", ephemeral=True)
            
        await interaction.response.defer()
        await interaction.edit_original_response(content="🚀 実装を開始します。少々お待ちください...", view=None)
        
        # Phase 2: Implementation
        result = await self.agent.execute_task(self.requirement_json)
        
        if "error" in result:
            await interaction.followup.send(f"❌ 実装中にエラーが発生しました: {result['error']}")
            return

        # ファイル保存ロジック（実際にはSessionManager等を通じて行う）
        # ここではシミュレーションとして結果を表示
        embed = discord.Embed(title="✅ 実装完了", color=discord.Color.green())
        embed.add_field(name="計画", value="\n".join(result.get("plan", []))[:1024], inline=False)
        embed.add_field(name="生成ファイル", value=", ".join([f["path"] for f in result.get("files", [])]), inline=False)
        await interaction.followup.send(embed=embed)

    @discord.ui.button(label="修正を依頼する", style=discord.ButtonStyle.gray, emoji="✏️")
    async def refine(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.user_id:
            return await interaction.response.send_message("この操作は実行者のみ可能です。", ephemeral=True)
            
        if self.refine_count >= 3:
            return await interaction.response.send_message("修正依頼は最大3回までです。現在の仕様で実行するか、最初からやり直してください。", ephemeral=True)

        # 修正内容を入力するためのModalを表示
        modal = RefinementModal(self)
        await interaction.response.send_modal(modal)

class RefinementModal(discord.ui.Modal, title="要件の修正依頼"):
    feedback = discord.ui.TextInput(
        label="どのような修正が必要ですか？",
        style=discord.ui.TextInputStyle.paragraph,
        placeholder="例: メールではなくDiscordに送るようにしてほしい、など",
        required=True,
        max_length=500
    )
    
    def __init__(self, parent_view: RequirementApprovalView):
        super().__init__()
        self.parent_view = parent_view
        
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        self.parent_view.refine_count += 1
        
        # Geminiに再依頼（履歴を含めるロジックが必要）
        new_req = await self.parent_view.agent.define_requirements(
            self.feedback.value, 
            history=[{"role": "assistant", "content": json.dumps(self.parent_view.requirement_json, ensure_ascii=False)}]
        )
        
        self.parent_view.requirement_json = new_req
        
        # Embedを更新して再提示
        embed = discord.Embed(title=f"📝 要件の再定義 (修正 {self.parent_view.refine_count}/3)", color=discord.Color.blue())
        embed.add_field(name="タスク概要", value=new_req.get("task_summary", "不明"), inline=False)
        embed.add_field(name="技術要件", value="\n".join(new_req.get("technical_requirements", [])), inline=False)
        
        await interaction.edit_original_response(embed=embed, view=self.parent_view)
