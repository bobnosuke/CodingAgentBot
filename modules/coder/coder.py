from typing import Optional, List, Dict, Any
from logger import setup_logger
from modules.ai.openrouter import AIService
from modules.ai.prompts_coder import CODER_PROMPT
import json
import re

logger = setup_logger(__name__)

class CoderAgent:
    """Agent responsible for executing coding tasks and proposing file changes."""

    def __init__(self, ai_service: AIService):
        self.ai_service = ai_service
        self.ai_service.set_model("gpt-4o") # Default model for CoderAgent

    async def execute_coding_task(self, task: Dict[str, Any], current_files: Dict[str, str]) -> Dict[str, Any]:
        """Executes a coding task and returns proposed file changes."""
        logger.info(f"Executing coding task: {task.get("description", "No description")}")

        prompt = CODER_PROMPT.format(
            task_type=task.get("type"),
            task_role=task.get("role"),
            task_description=task.get("description"),
            current_files=json.dumps(current_files, indent=2)
        )

        try:
            response = await self.ai_service.send_request(prompt)
            parsed_response = self._parse_coder_response(response)
            return parsed_response
        except Exception as e:
            logger.error(f"Error executing coding task: {e}", exc_info=True)
            return {"error": str(e)}

    def _parse_coder_response(self, response_content: str) -> Dict[str, Any]:
        """Parses the AI's response to extract file changes and reasoning."""
        # Attempt to extract JSON first
        json_match = re.search(r"```json\n(.*?)```", response_content, re.DOTALL)
        if json_match:
            try:
                json_data = json.loads(json_match.group(1))
                return json_data
            except json.JSONDecodeError:
                logger.warning("Failed to decode JSON from coder response, attempting regex for files.")

        # Fallback to regex if JSON extraction fails or is not present
        file_changes = {}
        files_pattern = re.compile(r"^\s*```(?P<lang>\w+)?\n(?P<content>.*?)\n```\s*$", re.MULTILINE | re.DOTALL)
        
        # This regex is too broad, need a more specific one to extract file paths and content
        # For now, let's assume the AI will provide a JSON output with file changes.
        # If not, we'll need to refine this parsing or the prompt.
        
        # For demonstration, if JSON fails, we'll return a generic error.
        return {"error": "Failed to parse coder response. Expected JSON output with file changes."}

    async def _notify_progress(self, message: str, status: str = "info"):
        """Placeholder for progress notification."""
        logger.info(f"CoderAgent Progress ({status}): {message}")
