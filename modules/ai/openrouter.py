"""
OpenRouter API integration for CoderAgent
Handles AI model communication and code generation
"""
import asyncio
import aiohttp
from typing import AsyncGenerator, Optional, List, Dict
import google.generativeai as genai
from logger import setup_logger
from config import Config

logger = setup_logger(__name__)


class GeminiClient:
    """Client for Gemini API communication"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        genai.configure(api_key=self.api_key)

    async def generate_content(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000
    ):
        model = genai.GenerativeModel("gemini-pro")
        try:
            response = await model.generate_content_async(
                messages,
                generation_config={
                    "temperature": temperature,
                    "max_output_tokens": max_tokens
                }
            )
            yield response.text
        except Exception as e:
            logger.error(f"Error calling Gemini API: {e}")
            raise


class OpenRouterClient:
    """Client for OpenRouter API communication"""
    
    def __init__(self, api_key: str):
        """
        Initialize OpenRouter client
        
        Args:
            api_key: OpenRouter API key
        """
        self.api_key = api_key
        self.base_url = Config.OPENROUTER_BASE_URL
        self.timeout = aiohttp.ClientTimeout(total=Config.AI_TIMEOUT_SECONDS)
    
    async def create_message(
        self,
        messages: List[Dict[str, str]],
        model: str = Config.DEFAULT_AI_MODEL,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        stream: bool = True
    ):
        """
        Create a message using OpenRouter API
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream
        }
        
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=headers
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"OpenRouter API error: {response.status} - {error_text}")
                        raise Exception(f"API error: {response.status}")
                    
                    if stream:
                        async for line in response.content:
                            if line:
                                line_str = line.decode().strip()
                                if line_str.startswith("data: "):
                                    data_str = line_str[6:]
                                    if data_str == "[DONE]":
                                        break
                                    
                                    try:
                                        import json
                                        data = json.loads(data_str)
                                        
                                        if "choices" in data and len(data["choices"]) > 0:
                                            delta = data["choices"][0].get("delta", {})
                                            if "content" in delta:
                                                yield delta["content"]
                                    
                                    except json.JSONDecodeError:
                                        continue
                    else:
                        response_json = await response.json()
                        yield str(response_json)
        
        except asyncio.TimeoutError:
            logger.error("OpenRouter API timeout")
            raise Exception("API timeout")
        except Exception as e:
            logger.error(f"Error calling OpenRouter API: {e}")
            raise


class AIService:
    """High-level AI service for CoderAgent"""
    
    def __init__(self, openrouter_client: OpenRouterClient, gemini_client: Optional[GeminiClient] = None):
        """
        Initialize AI service
        """
        self.openrouter_client = openrouter_client
        self.gemini_client = gemini_client
        self.current_model = "meta-llama/llama-3.3-70b-instruct:free"
    
    def set_model_by_preset(self, preset: str):
        """
        Set AI model based on preset name (All Free Models)
        
        Args:
            preset: Preset name ('high', 'balance', 'low')
        """
        presets = {
            "high": "nousresearch/hermes-3-llama-3.1-405b:free",
            "balance": "meta-llama/llama-3.3-70b-instruct:free",
            "low": "qwen/qwen3-coder:free"
        }
        self.current_model = presets.get(preset, "meta-llama/llama-3.3-70b-instruct:free")
        logger.info(f"AI model set to {self.current_model} via preset {preset}")

    async def generate_code(
        self,
        user_prompt: str,
        conversation_history: List[Dict[str, str]] = None,
        model: Optional[str] = None,
        language: str = "en-US",
        use_gemini: bool = False
    ) -> AsyncGenerator[str, None]:
        """
        Generate code based on user prompt
        """
        lang_instruction = "Respond in Japanese." if language == "ja" else "Respond in English."
        
        system_message = {
            "role": "system",
            "content": f"""You are an expert AI code generation assistant. {lang_instruction} Your role is to:
1. Generate clean, well-structured, production-ready code
2. Follow best practices and design patterns
3. Include comments and documentation
4. Handle error cases appropriately
5. Provide explanations for your code

When generating code:
- Use the latest stable versions of libraries
- Include proper type hints (for Python)
- Write modular, reusable code
- Optimize for readability and maintainability"""
        }
        
        messages = [system_message]
        if conversation_history:
            messages.extend(conversation_history)
        
        messages.append({
            "role": "user",
            "content": user_prompt
        })
        
        if use_gemini and self.gemini_client:
            async for chunk in self.gemini_client.generate_content(
                messages=messages,
                temperature=0.7,
                max_tokens=2000
            ):
                yield chunk
        else:
            async for chunk in self.openrouter_client.create_message(
                messages=messages,
                model=model or self.current_model,
                temperature=0.7,
                max_tokens=4000,
                stream=True
            ):
                yield chunk
    
    async def chat(
        self,
        user_message: str,
        conversation_history: List[Dict[str, str]] = None,
        model: Optional[str] = None,
        language: str = "en-US",
        system_override: Optional[str] = None,
        use_gemini: bool = False
    ) -> AsyncGenerator[str, None]:
        """
        Chat with AI assistant
        """
        lang_instruction = "Respond in Japanese." if language == "ja" else "Respond in English."
        
        system_message = {
            "role": "system",
            "content": system_override or f"""You are a helpful AI coding assistant. {lang_instruction} Help users with:
1. Code generation and debugging
2. Architecture and design questions
3. Best practices and optimization
4. Explanation of concepts
5. Project planning and structure

Be concise, clear, and practical in your responses."""
        }
        
        messages = [system_message]
        if conversation_history:
            messages.extend(conversation_history)
        
        messages.append({
            "role": "user",
            "content": user_message
        })
        
        if use_gemini and self.gemini_client:
            async for chunk in self.gemini_client.generate_content(
                messages=messages,
                temperature=0.7,
                max_tokens=2000
            ):
                yield chunk
        else:
            async for chunk in self.openrouter_client.create_message(
                messages=messages,
                model=model or self.current_model,
                temperature=0.7,
                max_tokens=2000,
                stream=True
            ):
                yield chunk
