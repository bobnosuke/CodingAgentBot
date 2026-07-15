"""
Autonomous Agent logic for CoderAgent
Handles requirement definition and implementation in separate phases to optimize API usage.
"""
import json
import re
from typing import List, Dict, Any, Optional, AsyncGenerator
from logger import setup_logger
from .openrouter import AIService

logger = setup_logger(__name__)

class CodingAgent:
    """
    Autonomous agent that handles:
    Phase 1: Requirement Definition (Optimized for Gemini/Low-cost models)
    Phase 2: One-shot Implementation (Optimized for High-performance models)
    """
    
    def __init__(self, ai_service: AIService):
        self.ai_service = ai_service

    async def define_requirements(self, user_request: str, history: list = []) -> dict:
        """
        Phase 1: Define requirements.
        Translates vague user requests into a structured JSON for implementation.
        """
        from modules.ai.prompts_gemini import GEMINI_REQUIREMENT_PROMPT
        
        logger.info(f"Defining requirements for: {user_request[:50]}...")
        
        response_text = ""
        try:
            async for chunk in self.ai_service.chat(
                user_message=user_request,
                conversation_history=history,
                system_override=GEMINI_REQUIREMENT_PROMPT,
                language="ja"
            ):
                response_text += chunk
            
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                return {"error": "Failed to parse requirements JSON", "raw_response": response_text}
        except Exception as e:
            logger.error(f"Error in define_requirements: {e}")
            return {"error": str(e)}

    async def execute_task(self, requirement_json: dict, context: dict = None) -> dict:
        """
        Phase 2: Execute implementation.
        Takes the requirement JSON and generates all necessary code files in one shot.
        """
        system_prompt = """あなたはエキスパート自律コーディングエージェントです。
提供された技術仕様（JSON）に基づき、完動するコードを実装してください。

### 出力形式:
必ず以下の構造を持つ単一のJSONオブジェクトとして出力してください:
{
  "plan": ["ステップ1: ...", "ステップ2: ..."],
  "files": [
    {
      "path": "ファイルパス",
      "content": "ファイルの内容",
      "description": "ファイルの説明"
    }
  ],
  "verification": "テスト方法の説明",
  "notes": "補足情報"
}

余計な解説は不要です。JSONのみを出力してください。"""

        logger.info(f"Executing implementation for task: {requirement_json.get('task_summary', 'Unknown')}")
        
        user_msg = f"以下の仕様を実装してください: {json.dumps(requirement_json, ensure_ascii=False)}"
        history = context.get("history", []) if context else []
        
        response_text = ""
        try:
            async for chunk in self.ai_service.chat(
                user_message=user_msg,
                conversation_history=history,
                system_override=system_prompt,
                language="ja"
            ):
                response_text += chunk
            
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                return {"error": "Failed to parse implementation JSON", "raw_response": response_text}
        except Exception as e:
            logger.error(f"Error in execute_task: {e}")
            return {"error": str(e)}
