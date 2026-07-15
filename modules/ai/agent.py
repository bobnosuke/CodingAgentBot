"""
Autonomous Agent logic for CoderAgent
Handles multi-step planning and code generation in a single request
"""
import json
import re
from typing import List, Dict, Any, Optional, AsyncGenerator
from logger import setup_logger
from .openrouter import AIService

logger = setup_logger(__name__)

class CodingAgent:
    """
    Autonomous agent that handles planning, implementation, and verification
    optimized for single-request execution.
    """
    
    def __init__(self, ai_service: AIService):
        self.ai_service = ai_service
        self.system_prompt = """You are an autonomous AI coding agent. Your goal is to complete the user's request in a single, comprehensive response.
You must think step-by-step and provide:
1. **Plan**: A detailed breakdown of the implementation steps.
2. **Files**: All necessary code files with full content.
3. **Verification**: How to verify the implementation.

Your response must be in the following JSON format:
{
  "plan": ["step 1", "step 2", ...],
  "files": [
    {
      "path": "filename.py",
      "content": "full code here",
      "description": "what this file does"
    }
  ],
  "verification": "instructions to test",
  "notes": "any important considerations"
}

Ensure all code is production-ready, includes comments, and handles errors.
Respond ONLY with the JSON object."""

    async def execute_task(
        self, 
        user_request: str, 
        context: Dict[str, Any],
        language: str = "ja"
    ) -> Dict[str, Any]:
        """
        Execute a coding task autonomously in a single request.
        """
        logger.info(f"Executing autonomous task: {user_request[:50]}...")
        
        # Construct context string
        context_str = self._format_context(context)
        
        full_prompt = f"""User Request: {user_request}

Current Project Context:
{context_str}

Please provide the complete implementation plan and code in the specified JSON format.
Respond in {'Japanese' if language == 'ja' else 'English'} for the descriptions, but keep the JSON structure intact."""

        # Call AI service
        response_text = ""
        async for chunk in self.ai_service.chat(
            user_message=full_prompt,
            model=self.ai_service.current_model,
            language=language,
            system_override=self.system_prompt
        ):
            response_text += chunk
        
        # Parse JSON response
        try:
            # Extract JSON if there's surrounding text
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return result
            else:
                logger.error("No JSON found in AI response")
                return {"error": "Failed to parse AI response", "raw": response_text}
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            return {"error": "Invalid JSON format", "raw": response_text}

    def _format_context(self, context: Dict[str, Any]) -> str:
        """Format project context for the prompt"""
        files = context.get("files", [])
        file_list = "\n".join([f"- {f}" for f in files])
        
        history = context.get("history", [])
        history_str = "\n".join([f"{h['role']}: {h['content'][:100]}..." for h in history[-3:]])
        
        return f"""
Files in project:
{file_list}

Recent history:
{history_str}
"""
