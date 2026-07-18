"""
Autonomous Agent logic for CoderAgent
Handles requirement definition and implementation in separate phases to optimize API usage.
"""
import json
import re
from typing import List, Dict, Any, Optional, AsyncGenerator
from logger import setup_logger
from .openrouter import AIService
from modules.executor.docker_executor import DockerExecutor

logger = setup_logger(__name__)


class CodingAgent:
    """
    Autonomous agent that handles:
    Phase 1: Requirement Definition (Optimized for Gemini/Low-cost models)
    Phase 2: One-shot Implementation (Optimized for High-performance models)
    """
    
    def __init__(self, ai_service: AIService, executor: Optional[DockerExecutor] = None, on_progress: Optional[callable] = None):
        self.ai_service = ai_service
        self.executor = executor or DockerExecutor()
        self.max_retries = 3
        self.on_progress = on_progress

    async def _notify_progress(self, message, status):
        print("_notify_progress開始")
    
        if self.on_progress:
            print("callbackあり")
    
            try:
                await self.on_progress(message, status)
    
                print("callback完了")
    
            except Exception as e:
                print("callback error:", repr(e))

    async def define_requirements(self, user_request: str, history: list = []) -> dict:
        """
        Phase 1: Define requirements.
        Translates vague user requests into a structured JSON for implementation.
        """
        from modules.ai.prompts_cerebras import CEREBRAS_REQUIREMENT_PROMPT
        
        logger.info(f"Defining requirements for: {user_request[:50]}...")
        
        response_text = ""
        try:
            async for chunk in self.ai_service.chat(
                user_message=user_request,
                conversation_history=history,
                system_override=CEREBRAS_REQUIREMENT_PROMPT,
                language="ja",
                use_cerebras=True
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

    async def execute_task(self, requirement_json: dict, context: dict = None, session_id: str = "default_session") -> dict:
        """
        Phase 2: Execute implementation with self-correction loop.
        """
        print("execute_task開始")
        await self._notify_progress("環境のセットアップを開始します...", "setup")
        print("notify_progress完了")
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
  "entrypoint": "実行するメインファイルのパス",
  "verification": "テスト方法の説明",
  "notes": "補足情報"
}

余計な解説は不要です。JSONのみを出力してください。"""

        logger.info(f"Executing implementation for task: {requirement_json.get('task_summary', 'Unknown')}")
        
        user_msg = f"以下の仕様を実装してください: {json.dumps(requirement_json, ensure_ascii=False)}"
        history = (context.get("history", []) if context else []).copy()
        
        # Build image once for this session
        try:
            if not self.executor.image_exists():
                await self.executor.build_image()
            print("docker build完了")
            await self._notify_progress("実行環境の準備が完了しました。", "setup_complete")
        except Exception as e:
            logger.error(f"Failed to build Docker image: {e}")
            await self._notify_progress(f"環境セットアップエラー: {str(e)}", "error")
            return {"error": f"Environment setup failed: {str(e)}"}

        for attempt in range(self.max_retries):
            logger.info(f"Implementation attempt {attempt + 1}/{self.max_retries}")
            await self._notify_progress(f"実装を生成中... (試行 {attempt + 1}/{self.max_retries})", "generating")
            
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
                if not json_match:
                    error_msg = "Failed to parse implementation JSON"
                    logger.warning(error_msg)
                    user_msg = f"エラーが発生しました: JSON形式で出力してください。詳細: {error_msg}"
                    continue

                result = json.loads(json_match.group())
                files = result.get("files", [])
                entrypoint = result.get("entrypoint")

                if not files or not entrypoint:
                    error_msg = "Files or entrypoint missing in JSON"
                    logger.warning(error_msg)
                    user_msg = f"エラーが発生しました: 'files' と 'entrypoint' を含めてください。詳細: {error_msg}"
                    continue

                # Execute and verify
                logger.info(f"Verifying implementation via Docker...")
                await self._notify_progress("Dockerコンテナ内でコードを検証中...", "verifying")
                exec_result = await self.executor.execute_code(session_id, files, entrypoint)
                
                if exec_result["exit_code"] == 0:
                    logger.info("Verification successful!")
                    await self._notify_progress("検証に成功しました！", "success")
                    result["execution_result"] = exec_result
                    return result
                else:
                    logger.warning(f"Verification failed with exit code {exec_result['exit_code']}")
                    await self._notify_progress(f"検証エラーを検出しました。修正を試みます... (試行 {attempt + 1})", "retrying")
                    # Feedback to AI
                    history.append({"role": "assistant", "content": response_text})
                    user_msg = f"""実装されたコードの実行中にエラーが発生しました。
以下のログを確認し、原因を特定してコードを修正してください。

### 実行ログ:
{exec_result['logs']}

### 修正のポイント:
1. インポートミスや構文エラーがないか
2. 必要なライブラリが揃っているか
3. ロジックに矛盾がないか

再度、全ファイルのコードをJSON形式で出力してください。"""
                print("AI呼び出し終了")
                    
            except Exception as e:
                logger.error(f"Error in execute_task attempt {attempt + 1}: {e}")
                user_msg = f"システムエラーが発生しました: {str(e)}。もう一度試してください。"

        return {"error": f"Failed to generate working code after {self.max_retries} attempts.", "last_result": result if 'result' in locals() else None}
