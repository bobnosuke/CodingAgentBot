import json
import re
from typing import List, Dict, Any
from logger import setup_logger
from modules.ai.openrouter import AIService
from modules.ai.prompts_planner import PLANNER_PROMPT

logger = setup_logger(__name__)

class PlannerAgent:
    def __init__(self, ai_service: AIService):
        self.ai_service = ai_service

    async def plan_task(self, user_request: str, history: List[Dict[str, str]] = []) -> List[Dict[str, Any]]:
        logger.info(f"Planning task for: {user_request[:50]}...")

        response_text = ""
        try:
            async for chunk in self.ai_service.chat(
                user_message=user_request,
                conversation_history=history,
                system_override=PLANNER_PROMPT,
                language="ja",
                use_cerebras=True # Assuming Cerebras is used for planning
            ):
                response_text += chunk
            
            # Attempt to extract and parse JSON
            json_match = re.search(r"```json\n(.*?)```", response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                return json.loads(json_str)
            else:
                logger.error(f"Failed to extract JSON from planner response: {response_text}")
                return [{"error": "Failed to parse planner JSON", "raw_response": response_text}]
        except Exception as e:
            logger.error(f"Error in PlannerAgent.plan_task: {e}", exc_info=True)
            return [{"error": str(e)}]
