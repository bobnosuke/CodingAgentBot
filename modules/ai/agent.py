"""
Autonomous Agent logic for CoderAgent
Handles requirement definition and implementation in separate phases to optimize API usage.
"""
import json
import re
import asyncio
from typing import List, Dict, Any, Optional, AsyncGenerator
from logger import setup_logger
from .openrouter import AIService
from .tools import AgentTools
from modules.executor.docker_executor import DockerExecutor
from modules.verifier.verifier import Verifier

logger = setup_logger(__name__)

def extract_json(text: str) -> dict:
    text = text.replace("```json", "")
    text = text.replace("```", "")
    start = text.find("{")
    if start == -1:
        raise ValueError("JSON object not found")
    json_text = text[start:].strip()
    decoder = json.JSONDecoder()

    try:
        obj, index = decoder.raw_decode(json_text)
        return obj
    except json.JSONDecodeError:
        # JSON修復
        repaired = json_text
        # 末尾カンマ削除
        repaired = re.sub(r


class CodingAgent:
    """
    Autonomous agent that handles:
    Phase 1: Requirement Definition (Optimized for Gemini/Low-cost models)
    Phase 2: One-shot Implementation (Optimized for High-performance models)
    """
    
    def __init__(self, ai_service: AIService, executor: Optional[DockerExecutor] = None, verifier: Optional[Verifier] = None, on_progress: Optional[callable] = None, base_path: str = "./storage"):
        self.ai_service = ai_service
        self.executor = executor or DockerExecutor()
        self.verifier = verifier or Verifier()
        self.tools = AgentTools(base_path)
        self.max_retries = 3
        self.on_progress = on_progress

    async def _notify_progress(self, message, status):
        logger.debug("_notify_progress開始")
    
        if self.on_progress:
            logger.debug("callbackあり")
    
            if asyncio.iscoroutinefunction(self.on_progress):
                logger.debug("callback await前")
    
                await self.on_progress(message, status)
    
                logger.debug("callback await後")

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
            
            return extract_json(response_text)
        except Exception as e:
            logger.error(f"Error in define_requirements: {e}")
            return {"error": str(e)}

    async def execute_task(self, requirement_json: dict, context: dict = None, session_id: str = None) -> dict:
        """
        Phase 2: Execute implementation with self-correction loop.
        """
        if not session_id:
            raise ValueError("session_id is required")
        logger.debug("execute_task開始")
        await self._notify_progress("環境のセットアップを開始します...", "setup")
        logger.debug("notify_progress完了")
        system_prompt = """あなたはエキスパート自律コーディングエージェントです。
提供された技術仕様(JSON)を解析し、実際に動作するプロジェクトファイルを生成してください。
あなたの役割:
- 必要なファイル構成を設計する
- 各ファイルの完全なコードを生成する
- 実行可能なエントリーポイントを指定する
- Docker環境で実行可能な状態にする

## 実装ルール
1. 必ず必要な全ファイルを生成してください。
2. ファイル内容は省略禁止です。
   以下のような記述は禁止です。
   ❌ "ここに処理を書く"
   ❌ "省略"
   ❌ "同様のコード"
3. 外部ライブラリを使用する場合:
   - requirements.txtを作成してください。
4. Pythonプロジェクトの場合:
   - 実行可能なmain.pyを必ず作成してください。
5. 環境変数が必要な場合:
   - .env.exampleを作成してください。
6. content内コードについて
   - ファイルcontent内の改行はJSON文字列として正しくエスケープしてください。ダブルクォートは必ずエスケープしてください。

## 出力形式
必ずJSONのみを返してください。

形式:
{
  "plan": [
    "実装内容1",
    "実装内容2"
  ],
  "files": [
    {
      "path": "main.py",
      "content": "完全なコード"
    },
    {
      "path": "requirements.txt",
      "content": "ライブラリ一覧"
    }
  ],
  "entrypoint": "main.py",
  "verification": [
    "実行確認方法",
    "テスト内容"
  ],
  "notes": "補足"
}

## 重要
- Markdownは禁止
- ```コードブロックは禁止
- JSON以外の文章は禁止
- filesには実際に保存する全コードを含める
- 生成後、そのままDockerで実行されることを前提にしてください"""

        logger.info(f"Executing implementation for task: {requirement_json.get("task_summary", "Unknown")}")
        
        user_msg = f"以下の仕様を実装してください: {json.dumps(requirement_json, ensure_ascii=False)}"
        history = (context.get("history", []) if context else []).copy()
        
        # Build image once for this session
        try:
            if not self.executor.image_exists(session_id):
                await self.executor.build_image(session_id)
            logger.debug("docker build完了")
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
                
                result = extract_json(response_text)
                entrypoint = result.get("entrypoint")

                # Convert tool_calls to files for Docker execution (legacy support/internal compatibility)
                files = result.get("files", [])
                if not files:
                    error_msg = "No files generated"
                    logger.warning(error_msg)
                    user_msg = f"""
                エラー:
                ファイルが生成されていません。
                
                files配列に最低1つ以上のファイルを含めてください。
                """
                    continue

                # The original code had a 'tool_calls' check, but the new prompt focuses on 'files'.
                # Assuming 'tool_calls' is no longer relevant here based on the new prompt structure.
                # if not files and not tool_calls:
                #     error_msg = "No tool_calls or files provided"
                #     logger.warning(error_msg)
                #     user_msg = f"エラーが発生しました: 'tool_calls' を含めてください。詳細: {error_msg}"
                #     continue
                
                if not entrypoint:
                    error_msg = "Entrypoint missing in JSON"
                    logger.warning(error_msg)
                    user_msg = f"エラーが発生しました: 'entrypoint' を含めてください。詳細: {error_msg}"
                    continue

                # Execute and verify
                logger.info(f"Verifying implementation via Docker...")
                await self._notify_progress("Dockerコンテナ内でコードを検証中...", "verifying")
                exec_result = await self.executor.execute_code(session_id, files, entrypoint)
                
                verification_result = self.verifier.verify_docker_output(exec_result["exit_code"], exec_result["stdout"], exec_result["stderr"])

                if verification_result["success"]:
                    logger.info("Verification successful!")
                    await self._notify_progress("検証に成功しました！", "success")
                    result["execution_result"] = exec_result
                    return result
                else:
                    logger.warning(f"Verification failed: {verification_result.get("message", "Unknown error")}")
                    await self._notify_progress(f"検証エラーを検出しました。修正を試みます... (試行 {attempt + 1})", "retrying")
                    # Feedback to AI
                    history.append({"role": "assistant", "content": response_text})
                    error_feedback = f"""実装されたコードの実行中にエラーが発生しました。
以下のエラー情報を確認し、原因を特定してコードを修正してください。

### エラー詳細:
タイプ: {verification_result.get("error_type", "不明")}
ファイル: {verification_result.get("file", "不明")}
行: {verification_result.get("line", "不明")}
メッセージ: {verification_result.get("message", "不明")}

### 実行ログ:
{exec_result["logs"]}

### 修正のポイント:
1. インポートミスや構文エラーがないか
2. 必要なライブラリが揃っているか
3. ロジックに矛盾がないか

再度、全ファイルのコードをJSON形式で出力してください。"""
                    user_msg = error_feedback
                logger.debug("AI呼び出し終了")
                    
            except Exception as e:
                logger.error(f"Error in execute_task attempt {attempt + 1}: {e}")
                user_msg = f"システムエラーが発生しました: {str(e)}。もう一度試してください。"

        return {"error": f"Failed to generate working code after {self.max_retries} attempts.", "last_result": result if 'result' in locals() else None}
