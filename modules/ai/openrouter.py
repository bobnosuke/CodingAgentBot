"""
OpenRouter API integration for CoderAgent
Handles AI model communication and code generation
"""
import asyncio
import aiohttp
from typing import AsyncGenerator, Optional, List, Dict
from logger import setup_logger
from config import Config

logger = setup_logger(__name__)


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
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model to use
            temperature: Temperature for sampling
            max_tokens: Maximum tokens in response
            stream: Whether to stream the response (default: True)
        
        Yields:
            Streamed text chunks
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
                        # For non-streaming, yield the entire response as a single chunk
                        yield str(response_json)
        
        except asyncio.TimeoutError:
            logger.error("OpenRouter API timeout")
            raise Exception("API timeout")
        except Exception as e:
            logger.error(f"Error calling OpenRouter API: {e}")
            raise
    
    async def get_available_models(self) -> List[Dict]:
        """
        Get list of available models from OpenRouter
        
        Returns:
            List of model information dicts
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }
        
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(
                    f"{self.base_url}/models",
                    headers=headers
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("data", [])
                    else:
                        logger.error(f"Failed to get models: {response.status}")
                        return []
        
        except Exception as e:
            logger.error(f"Error getting models: {e}")
            return []


class AIService:
    """High-level AI service for CoderAgent"""
    
    def __init__(self, openrouter_client: OpenRouterClient):
        """
        Initialize AI service
        
        Args:
            openrouter_client: OpenRouter client instance
        """
        self.client = openrouter_client
        self.current_model = Config.DEFAULT_AI_MODEL
    
    def set_model_by_preset(self, preset: str):
        """
        Set AI model based on preset name
        
        Args:
            preset: Preset name ('high', 'balance', 'low')
        """
        presets = {
            "high": "anthropic/claude-3.5-sonnet",
            "balance": "google/gemini-pro-1.5",
            "low": "meta-llama/llama-3.1-70b-instruct"
        }
        self.current_model = presets.get(preset, Config.DEFAULT_AI_MODEL)
        logger.info(f"AI model set to {self.current_model} via preset {preset}")

    async def generate_code(
        self,
        user_prompt: str,
        conversation_history: List[Dict[str, str]] = None,
        model: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        Generate code based on user prompt
        
        Args:
            user_prompt: User's code generation request
            conversation_history: Previous messages in conversation
            model: Model to use (overrides self.current_model)
        
        Yields:
            Code chunks as they're generated
        """
        # Build system message for code generation
        system_message = {
            "role": "system",
            "content": """You are an expert AI code generation assistant. Your role is to:
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
        
        # Build messages list
        messages = [system_message]
        
        if conversation_history:
            messages.extend(conversation_history)
        
        messages.append({
            "role": "user",
            "content": user_prompt
        })
        
        # Stream response
        async for chunk in self.client.create_message(
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
        model: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        Chat with AI assistant
        
        Args:
            user_message: User's message
            conversation_history: Previous messages
            model: Model to use (overrides self.current_model)
        
        Yields:
            Response chunks
        """
        system_message = {
            "role": "system",
            "content": """You are a helpful AI coding assistant. Help users with:
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
        
        async for chunk in self.client.create_message(
            messages=messages,
            model=model or self.current_model,
            temperature=0.7,
            max_tokens=2000,
            stream=True
        ):
            yield chunk
