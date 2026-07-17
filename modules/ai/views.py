import discord
import json
from modules.ai.agent import CodingAgent
from modules.database.repository import RequirementRepository

class RequirementApprovalView(discord.ui.View):
    """View for approving or refining requirements defined by Gemini"""
    
    def __init__(
        self,
        agent: CodingAgent,
        requirement_id: int,
        user_id: str,
        lang: str
    ):
        super().__init__(timeout=600)
    
        self.agent = agent
        self.requirement_id = requirement_id
        self.user_id = user_id
        self.lang = lang
        self.refine_count = 0
        
    @discord.ui.button(label="Start Implementation", style=discord.ButtonStyle.green, emoji="🚀")
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        logger.info(
            f"Start Implementation clicked by {interaction.user} "
            f"(requirement_id={self.requirement_id})"
        )
        from modules.utils.i18n import i18n
        if str(interaction.user.id) != self.user_id:
            return await interaction.response.send_message(i18n.translate(self.lang, "COMMON.PERMISSION_DENIED"), ephemeral=True)
            
        await interaction.response.defer()
        
        # Progress notification callback
        async def update_progress(msg, status):
            emoji = "⚙️"
            if status == "setup": emoji = "🏗️"
            elif status == "generating": emoji = "🧠"
            elif status == "verifying": emoji = "🧪"
            elif status == "retrying": emoji = "🩹"
            elif status == "success": emoji = "✨"
            elif status == "error": emoji = "❌"
            
            embed = discord.Embed(
                title="🚀 自律実装プロセス",
                description=f"{emoji} **{msg}**",
                color=discord.Color.blue()
            )
            await interaction.edit_original_response(content=None, embed=embed, view=None)

        self.agent.on_progress = update_progress
        
        db = interaction.client.db_manager.get_session()

        try:
            requirement = await RequirementRepository.get_requirement(
                db,
                self.requirement_id
            )
        
            if not requirement:
                return await interaction.followup.send(
                    "❌ 要件データが見つかりませんでした。",
                    ephemeral=True
                )
        
            await RequirementRepository.approve_requirement(
                db,
                self.requirement_id
            )
        
            requirement_json = requirement.json_data
        
            if isinstance(requirement_json, str):
                requirement_json = json.loads(requirement_json)
        
            session_id = f"session_{interaction.channel_id}"
        
            result = await self.agent.execute_task(
                requirement_json,
                session_id=session_id
            )
        
            if "error" in result:
                return await interaction.followup.send(
                    i18n.translate(
                        self.lang,
                        "CODING.IMPLEMENTATION_ERROR",
                        error=result["error"]
                    )
                )
        
            await RequirementRepository.update_requirement(
                db,
                self.requirement_id,
                status="completed"
            )
        
        finally:
            await db.close()

        # ファイル保存ロジック（実際にはSessionManager等を通じて行う）
        embed = discord.Embed(title=i18n.translate(self.lang, "CODING.IMPLEMENTATION_SUCCESS"), color=discord.Color.green())
        embed.add_field(name=i18n.translate(self.lang, "CODING.REQUIREMENT_PLAN"), value="\n".join(result.get("plan", []))[:1024], inline=False)
        embed.add_field(name="Files", value=", ".join([f["path"] for f in result.get("files", [])]), inline=False)
        await interaction.followup.send(embed=embed)

    @discord.ui.button(label="Refine Requirements", style=discord.ButtonStyle.gray, emoji="✏️")
    async def refine(self, interaction: discord.Interaction, button: discord.ui.Button):
        from modules.utils.i18n import i18n
        if str(interaction.user.id) != self.user_id:
            return await interaction.response.send_message(i18n.translate(self.lang, "COMMON.PERMISSION_DENIED"), ephemeral=True)
            
        if self.refine_count >= 3:
            return await interaction.response.send_message("Maximum 3 refinements allowed.", ephemeral=True)

        # 修正内容を入力するためのModalを表示
        modal = RefinementModal(self)
        await interaction.response.send_modal(modal)

class RefinementModal(discord.ui.Modal, title="Refine Requirements"):
    feedback = discord.ui.TextInput(
        label="Feedback",
        style=discord.TextStyle.paragraph,
        placeholder="Example: Change the output to Discord instead of email.",
        required=True,
        max_length=500
    )
    
    def __init__(self, parent_view: RequirementApprovalView):
        super().__init__()
        self.parent_view = parent_view
        
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        self.parent_view.refine_count += 1
        
        # Get current requirement from DB
        db = interaction.client.db_manager.get_session()
        try:
            current_req = await RequirementRepository.get_requirement(
                db,
                self.parent_view.requirement_id
            )
            if not current_req:
                return await interaction.followup.send("❌ 要件データが見つかりませんでした。", ephemeral=True)
    
            # Geminiに再依頼
            requirement_json = current_req.json_data
            if isinstance(requirement_json, str):
                requirement_json = json.loads(requirement_json)
            new_req = await self.parent_view.agent.define_requirements(
                self.feedback.value,
                history=[
                    {
                        "role": "assistant",
                        "content": json.dumps(
                            requirement_json,
                            ensure_ascii=False
                        )
                    }
                ]
            )
            
            # Update requirement in DB
            await RequirementRepository.update_requirement(
                self.parent_view.db_session, 
                self.parent_view.requirement_id, 
                json_data=new_req
            )
            
            from modules.utils.i18n import i18n
            # Embedを更新して再提示
            embed = discord.Embed(title=f"{i18n.translate(self.parent_view.lang, 'CODING.REQUIREMENT_TITLE')} ({self.parent_view.refine_count}/3)", color=discord.Color.blue())
            embed.add_field(name=i18n.translate(self.parent_view.lang, 'CODING.REQUIREMENT_SUMMARY'), value=new_req.get("task_summary", "Unknown"), inline=False)
            embed.add_field(name=i18n.translate(self.parent_view.lang, 'CODING.REQUIREMENT_TECH'), value="\n".join(new_req.get("technical_requirements", [])), inline=False)
            
            await interaction.edit_original_response(embed=embed, view=self.parent_view)
        finally:
            await db.close()