import discord
import json
from modules.ai.agent import CodingAgent
from modules.coder.coder import CoderAgent
from modules.debugger.debugger import DebuggerAgent
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
        self.db_session = interaction.client.db_manager.get_session() # Initialize db_session for RefinementModal
        
    @discord.ui.button(label="開発を開始", style=discord.ButtonStyle.green, emoji="🚀")
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
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
            await interaction.edit_original_response(
                content=None,
                embed=embed,
                view=None
            )

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
        
            # Instead of directly executing the task, we now assume tasks are already planned and stored in the DB
            # The actual execution will be handled by an orchestrator or a separate task processing mechanism.
            # For now, we just mark the requirement as approved and log the action.
            logger.info(f"Requirement {self.requirement_id} approved. Tasks should be processed by orchestrator.")
        
            # Get the session_id from the interaction channel
            session_id = None
            active_sessions = interaction.client.session_manager.active_sessions
            for uuid, info in active_sessions.items():
                if info["channel_id"] == str(interaction.channel_id):
                    session_id = info["db_session_id"]
                    break

            if not session_id:
                logger.error(f"Could not find session_id for channel {interaction.channel_id}")
                return await interaction.followup.send(
                    i18n.translate(self.lang, "COMMON.ERROR", error="Session not found."),
                    ephemeral=True
                )

            # Start processing tasks
            await self._process_tasks(db, session_id, self.requirement_id, interaction)
        
        finally:
            await db.close()

        # ファイル保存ロジック（実際にはSessionManager等を通じて行う）
        embed = discord.Embed(title=i18n.translate(self.lang, "CODING.IMPLEMENTATION_SUCCESS"), color=discord.Color.green())
        embed.add_field(name=i18n.translate(self.lang, "CODING.REQUIREMENT_PLAN"), value=i18n.translate(self.lang, "CODING.REQUIREMENT_PLAN_GENERATED"), inline=False)
        embed.add_field(name=i18n.translate(self.lang, "CODING.TASK_PROCESSING_STARTED"), value=i18n.translate(self.lang, "CODING.TASK_PROCESSING_DESC"), inline=False)
        await interaction.followup.send(embed=embed)

    async def _process_tasks(self, db_session, session_id: int, requirement_id: int, interaction: discord.Interaction):
        """Processes tasks generated by the PlannerAgent using the CoderAgent."""
        from modules.utils.i18n import i18n
        try:
            tasks = await TaskRepository.get_tasks_by_requirement(db_session, requirement_id)
            if not tasks:
                logger.warning(f"No tasks found for requirement {requirement_id}")
                return

            for task in tasks:
                await self.update_progress(i18n.translate(self.lang, "CODING.PROCESSING_TASK", task_id=task.task_id, description=task.description), "generating")
                
                # Get current project files
                project_info = await interaction.client.session_manager.get_session_project_info(session_id)
                if not project_info:
                    logger.error(f"Project info not found for session {session_id}")
                    await self.update_progress(i18n.translate(self.lang, "COMMON.ERROR", error="Project not found."), "error")
                    return
                
                current_files = await self.workspace_manager.get_project_files_content(project_info["files_dir"])

                # Execute coding task
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        coder_response = await self.coder_agent.execute_coding_task(task.to_dict(), current_files)

                        if "error" in coder_response:
                            raise Exception(coder_response["error"])

                        # If successful, break the retry loop
                        break
                    except Exception as e:
                        logger.error(f"CoderAgent error for task {task.id} (attempt {attempt + 1}/{max_retries}): {e}", exc_info=True)
                        await self.update_progress(i18n.translate(self.lang, "CODING.TASK_FAILED_RETRY", task_id=task.task_id, error=str(e), attempt=attempt+1, max_retries=max_retries), "retrying")

                        if attempt < max_retries - 1:
                            # Attempt to debug
                            debug_response = await self.debugger_agent.debug_code(str(e), current_files, task.to_dict())
                            if "error" in debug_response:
                                logger.error(f"DebuggerAgent error for task {task.id}: {debug_response["error"]}")
                                await self.update_progress(i18n.translate(self.lang, "CODING.DEBUG_FAILED", task_id=task.task_id, error=debug_response["error"]), "error")
                                # If debugger fails, just retry with the same code
                            else:
                                # Apply debugger's suggested changes
                                for change in debug_response.get("changes", []):
                                    file_path = change["file_path"]
                                    action = change["action"]
                                    content = change.get("content", "")
                                    full_path = f"{project_info["files_dir"]}/{file_path}"

                                    if action == "create":
                                        await self.workspace_manager.create_file(full_path, content)
                                    elif action == "modify":
                                        await self.workspace_manager.write_file(full_path, content)
                                    elif action == "delete":
                                        await self.workspace_manager.delete_file(full_path)
                                logger.info(f"Debugger applied fixes for task {task.id}")
                                await self.update_progress(i18n.translate(self.lang, "CODING.DEBUG_APPLIED", task_id=task.task_id), "verifying")
                        else:
                            # All retries failed
                            await self.update_progress(i18n.translate(self.lang, "CODING.TASK_FAILED_FINAL", task_id=task.task_id, error=str(e)), "error")
                            await TaskRepository.update_task_status(db_session, task.id, "failed", {"error": str(e), "final_coder_response": coder_response})
                            return

                # If we reached here, the task was successfully completed or debugged within retries
                if "error" in coder_response:
                    # This case should ideally not be reached if the loop breaks on success
                    logger.error(f"Unexpected error state after retry loop for task {task.id}")
                    await self.update_progress(i18n.translate(self.lang, "CODING.TASK_FAILED_FINAL", task_id=task.task_id, error="Unknown error after retries."), "error")
                    await TaskRepository.update_task_status(db_session, task.id, "failed", {"error": "Unknown error after retries.", "final_coder_response": coder_response})
                    return

                # Apply changes to workspace
                for change in coder_response.get("changes", []):
                    file_path = change["file_path"]
                    action = change["action"]
                    content = change.get("content", "")

                    full_path = f"{project_info["files_dir"]}/{file_path}"

                    if action == "create":
                        await self.workspace_manager.create_file(full_path, content)
                        logger.info(f"Created file: {full_path}")
                    elif action == "modify":
                        await self.workspace_manager.write_file(full_path, content)
                        logger.info(f"Modified file: {full_path}")
                    elif action == "delete":
                        await self.workspace_manager.delete_file(full_path)
                        logger.info(f"Deleted file: {full_path}")
                
                await TaskRepository.update_task_status(db_session, task.id, "completed", coder_response)
                await self.update_progress(i18n.translate(self.lang, "CODING.TASK_COMPLETED", task_id=task.task_id), "success")

            await RequirementRepository.update_requirement(db_session, requirement_id, status="completed")
            await self.update_progress(i18n.translate(self.lang, "CODING.ALL_TASKS_COMPLETED"), "success")

        except Exception as e:
            logger.error(f"Error processing tasks for requirement {requirement_id}: {e}", exc_info=True)
            await self.update_progress(i18n.translate(self.lang, "COMMON.ERROR", error=str(e)), "error")

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
                db, 
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