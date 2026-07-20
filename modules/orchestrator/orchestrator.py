from typing import Optional, List, Dict, Any
from logger import setup_logger
from modules.ai.openrouter import AIService
from modules.planner.planner import PlannerAgent
from modules.coder.coder import CoderAgent
from modules.debugger.debugger import DebuggerAgent
from modules.workspace.manager import WorkspaceManager
from modules.database.repository import TaskRepository, RequirementRepository, SessionRepository
import asyncio

logger = setup_logger(__name__)

class Orchestrator:
    """Orchestrates the Planner, Coder, and Debugger agents to achieve a development goal."""

    def __init__(self, ai_service: AIService, db_session_factory, update_progress_callback):
        self.ai_service = ai_service
        self.db_session_factory = db_session_factory
        self.update_progress = update_progress_callback
        self.planner_agent = PlannerAgent(ai_service)
        self.coder_agent = CoderAgent(ai_service)
        self.debugger_agent = DebuggerAgent(ai_service)
        self.workspace_manager = WorkspaceManager()

    async def execute_development_cycle(self, session_id: int, requirement_id: int, interaction: Any):
        """Executes the full development cycle for a given requirement."""
        from modules.utils.i18n import i18n
        db_session = self.db_session_factory()
        try:
            await self.update_progress(i18n.translate(interaction.locale, "CODING.ORCHESTRATOR_START"), "setup")

            # 1. Fetch tasks
            tasks = await TaskRepository.get_tasks_by_requirement(db_session, requirement_id)
            if not tasks:
                logger.warning(f"No tasks found for requirement {requirement_id}")
                await self.update_progress(i18n.translate(interaction.locale, "CODING.NO_TASKS_FOUND"), "error")
                return

            # 2. Process each task
            for task in tasks:
                await self.update_progress(i18n.translate(interaction.locale, "CODING.PROCESSING_TASK", task_id=task.task_id, description=task.description), "generating")
                
                db_session_obj = await SessionRepository.get_session_by_id(db_session, session_id)
                if not db_session_obj:
                    logger.error(f"Session not found in DB for session_id: {session_id}")
                    await self.update_progress(i18n.translate(interaction.locale, "COMMON.ERROR", error="Session not found."), "error")
                    await TaskRepository.update_task_status(db_session, task.id, "failed", {"error": "Session not found"})
                    continue
                
                # project_id is stored in the Session object itself
                # Ensure project_name is available for workspace_manager
                if not db_session_obj.project_name:
                    logger.error(f"Project name not found for session_id: {session_id}")
                    await self.update_progress(i18n.translate(interaction.locale, "COMMON.ERROR", error="Project name not found."), "error")
                    await TaskRepository.update_task_status(db_session, task.id, "failed", {"error": "Project name not found"})
                    continue
                
                project_files_dir = self.workspace_manager.get_project_path(db_session_obj.user_id, db_session_obj.project_name)
                if not project_files_dir:
                    logger.error(f"Project files directory not found for session {session_id}")
                    await self.update_progress(i18n.translate(interaction.locale, "COMMON.ERROR", error="Project files directory not found."), "error")
                    await TaskRepository.update_task_status(db_session, task.id, "failed", {"error": "Project files directory not found"})
                    continue
                project_info = {"files_dir": project_files_dir}
                current_files = await self.workspace_manager.get_project_files_content(project_info["files_dir"])

                max_retries = 3
                coder_response = None
                for attempt in range(max_retries):
                    try:
                        coder_response = await self.coder_agent.execute_coding_task(task.to_dict(), current_files)

                        if "error" in coder_response:
                            raise Exception(coder_response["error"])

                        # If successful, break the retry loop
                        break
                    except Exception as e:
                        logger.error(f"CoderAgent error for task {task.id} (attempt {attempt + 1}/{max_retries}): {e}", exc_info=True)
                        await self.update_progress(i18n.translate(interaction.locale, "CODING.TASK_FAILED_RETRY", task_id=task.task_id, error=str(e), attempt=attempt+1, max_retries=max_retries), "retrying")

                        if attempt < max_retries - 1:
                            # Attempt to debug
                            debug_response = await self.debugger_agent.debug_code(str(e), current_files, task.to_dict())
                            if "error" in debug_response:
                                logger.error(f"DebuggerAgent error for task {task.id}: {debug_response["error"]}")
                                await self.update_progress(i18n.translate(interaction.locale, "CODING.DEBUG_FAILED", task_id=task.task_id, error=debug_response["error"]), "error")
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
                                await self.update_progress(i18n.translate(interaction.locale, "CODING.DEBUG_APPLIED", task_id=task.task_id), "verifying")
                        else:
                            # All retries failed
                            await self.update_progress(i18n.translate(interaction.locale, "CODING.TASK_FAILED_FINAL", task_id=task.task_id, error=str(e)), "error")
                            await TaskRepository.update_task_status(db_session, task.id, "failed", {"error": str(e), "final_coder_response": coder_response})
                            break # Exit retry loop

                if coder_response and "error" not in coder_response:
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
                    await self.update_progress(i18n.translate(interaction.locale, "CODING.TASK_COMPLETED", task_id=task.task_id), "success")
                else:
                    # Task failed after all retries
                    await TaskRepository.update_task_status(db_session, task.id, "failed", coder_response)
                    await self.update_progress(i18n.translate(interaction.locale, "CODING.TASK_FAILED_FINAL", task_id=task.task_id, error="All attempts to complete task failed."), "error")

            await RequirementRepository.update_requirement(db_session, requirement_id, status="completed")
            await self.update_progress(i18n.translate(interaction.locale, "CODING.ALL_TASKS_COMPLETED"), "success")

        except Exception as e:
            logger.error(f"Error in orchestrator development cycle for requirement {requirement_id}: {e}", exc_info=True)
            await self.update_progress(i18n.translate(interaction.locale, "COMMON.ERROR", error=str(e)), "error")
        finally:
            await db_session.close()
