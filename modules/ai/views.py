import discord
import json
from modules.ai.agent import CodingAgent
from modules.coder.coder import CoderAgent
from modules.debugger.debugger import DebuggerAgent
from modules.orchestrator.orchestrator import Orchestrator
from modules.database.repository import RequirementRepository
from modules.workspace.manager import WorkspaceManager

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
        self.coder_agent = CoderAgent(agent.ai_service) # Reuse the same AI service
        self.workspace_manager = WorkspaceManager()
        self.debugger_agent = DebuggerAgent(agent.ai_service) # Reuse the same AI service
        self.requirement_id = requirement_id
        self.user_id = user_id
        self.lang = lang
        self.refine_count = 0
        self.db_manager = agent.db_manager
        self.bot = agent.bot # Pass bot instance for session_manager access
        self.orchestrator = Orchestrator(agent.ai_service, self.db_manager.get_session, self._update_progress_callback)
        
    @discord.ui.button(label="開発を開始", style=discord.ButtonStyle.green, emoji="🚀")
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        from modules.utils.i18n import i18n
        if str(interaction.user.id) != self.user_id:
            return await interaction.response.send_message(i18n.translate(self.lang, "COMMON.PERMISSION_DENIED"), ephemeral=True)
            
        await interaction.response.defer()
        self.interaction = interaction # Store interaction for progress updates

        db_session = self.db_manager.get_session()
        try:
            requirement = await RequirementRepository.get_requirement(
                db_session,
                self.requirement_id
            )

            if not requirement:
                return await self.interaction.followup.send(
                    "❌ 要件データが見つかりませんでした。",
                    ephemeral=True
                )

            await RequirementRepository.update_requirement(
                db_session,
                self.requirement_id,
                status="approved"
            )

            session_id = None
            active_sessions = self.bot.session_manager.active_sessions
            for uuid, info in active_sessions.items():
                if info["channel_id"] == str(interaction.channel_id):
                    session_id = info["db_session_id"]
                    break

            if not session_id:
                return await self.interaction.followup.send(
                    "❌ セッションが見つかりませんでした。",
                    ephemeral=True
                )

            await self.orchestrator.execute_development_cycle(session_id, self.requirement_id, self.interaction)

            embed = discord.Embed(title="🚀 開発プロセス開始", description="Orchestratorが開発サイクルを開始しました。", color=discord.Color.blue())
            await self.interaction.followup.send(embed=embed)

        except Exception as e:
            await self.interaction.followup.send(f"エラーが発生しました: {e}", ephemeral=True)
        finally:
            await db_session.close()

    async def _update_progress_callback(self, msg: str, status: str):
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
        await self.interaction.edit_original_response(
            content=None,
            embed=embed,
            view=self # Keep the view for further interactions if needed
        )



    @discord.ui.button(label="要件を修正", style=discord.ButtonStyle.gray, emoji="✏️")
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
        db_session = interaction.client.db_manager.get_session()
        try:
            current_req = await RequirementRepository.get_requirement(
                db_session,
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
                db_session, 
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
            await db_session.close()