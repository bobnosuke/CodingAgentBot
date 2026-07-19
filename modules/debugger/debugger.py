from typing import Optional, List, Dict, Any
from logger import setup_logger
from modules.ai.openrouter import AIService
from modules.ai.prompts_debugger import DEBUGGER_PROMPT
import json
import re

logger = setup_logger(__name__)

class DebuggerAgent:
    """Agent responsible for debugging and proposing fixes for errors."""

    def __init__(self, ai_service: AIService):
        self.ai_service = ai_service
        self.ai_service.set_model("gpt-4o") # Default model for DebuggerAgent

    async def debug_code(self, error_message: str, current_files: Dict[str, str], task: Dict[str, Any]) -> Dict[str, Any]:
        """Analyzes an error and proposes a patch to fix it."""
        logger.info(f"Debugging task: {task.get("description", "No description")}")

        prompt = DEBUGGER_PROMPT.format(
            error_message=error_message,
            task_type=task.get("type"),
            task_role=task.get("role"),
            task_description=task.get("description"),
            current_files=json.dumps(current_files, indent=2)
        )

        try:
            response = await self.ai_service.send_request(prompt)
            parsed_response = self._parse_debugger_response(response)
            return parsed_response
        except Exception as e:
            logger.error(f"Error debugging code: {e}", exc_info=True)
            return {"error": str(e)}

    def _parse_debugger_response(self, response_content: str) -> Dict[str, Any]:
        """Parses the AI's response to extract the proposed patch and reasoning."""
        json_match = re.search(r"```json\n(.*?)```", response_content, re.DOTALL)
        if json_match:
            try:
                json_data = json.loads(json_match.group(1))
                return json_data
            except json.JSONDecodeError:
                logger.warning("Failed to decode JSON from debugger response, attempting regex for patch.")

        return {"error": "Failed to parse debugger response. Expected JSON output with patch."}

    async def _notify_progress(self, message: str, status: str = "info"):
        """Placeholder for progress notification."""
        logger.info(f"DebuggerAgent Progress ({status}): {message}")
