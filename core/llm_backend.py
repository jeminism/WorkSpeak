"""
LLM Backend abstraction for WorkSpeak.
Supports OpenAI-compatible API endpoints.
"""

import aiohttp
import asyncio
from typing import Optional
from dataclasses import dataclass
from .config import LLMConfig

@dataclass
class LLMCallResult:
    """Result from an LLM API call."""
    text: str
    error: Optional[str] = None
    token_usage: Optional[dict] = None
    estimated_cost: Optional[float] = None


class LLMBackend:
    """Abstract base class for LLM backends."""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session
    
    async def generate(self, prompt: str, config: LLMConfig = None) -> LLMCallResult:
        """Generate response from LLM. Must be implemented by subclasses."""
        raise NotImplementedError
    
    async def close(self):
        """Close any open connections."""
        if self._session and not self._session.closed:
            await self._session.close()


class OpenAIBackend(LLMBackend):
    """OpenAI-compatible API backend."""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.api_url = config.endpoint
    
    async def _normalize_prompt(self, original_text: str, thread_context: str = "") -> str:
        """Format prompt for the LLM."""
        system_prompt = """You are a professional message editor for a Slack workspace. Your task is to rewrite user messages to be:

1. CONCISE: No more than 90% of the original length
2. PROFESSIONAL: Business-appropriate tone, not casual slang
3. FRIENDLY: Approachable but not overly casual
4. DIRECT: Clear and specific, avoid circular statements
5. ACCURATE: Preserve the original intent and meaning exactly

What NOT to do:
- Add explanations or meta-talk
- Use markdown formatting
- Add headers or bullet points
- Change the core message
- Use overly formal or overly casual language

Return ONLY the rewritten text. Do not include:
- Any introductory text
- Explanations
- Reasoning
- Summary statements
- Markdown formatting"""
        
        user_content = f"Original message:\n{original_text}\n"
        
        if thread_context:
            user_content += f"\nThread context:\n{thread_context}\n"
        
        user_content += "\nRewritten text:"
        
        return f"{system_prompt}\n\n{user_content}"
    
    async def generate(self, prompt: str, config: LLMConfig = None) -> LLMCallResult:
        """Send request to OpenAI-compatible endpoint."""
        config = config or self.config
        
        try:
            session = await self._get_session()
            
            payload = {
                "model": config.model,
                "messages": [
                    {"role": "system", "content": prompt.split("\n\n")[0]},
                    {"role": "user", "content": "\n\n".join(prompt.split("\n\n")[1:])}
                ],
                "temperature": config.temperature,
                "max_tokens": config.max_tokens
            }
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {config.api_key}"
            }
            
            async with session.post(
                self.api_url,
                json=payload,
                headers=headers
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    return LLMCallResult(
                        text="",
                        error=f"API error: {response.status} - {error_text}"
                    )
                
                data = await response.json()
                
                # Extract response
                if 'choices' in data and len(data['choices']) > 0:
                    text = data['choices'][0]['message']['content'].strip()
                elif 'output' in data:
                    # Some alternative API formats
                    text = str(data['output']).strip()
                else:
                    return LLMCallResult(
                        text="",
                        error="Unexpected API response format"
                    )
                
                # Try to extract usage info if available
                token_usage = None
                estimated_cost = None
                if 'usage' in data:
                    token_usage = data['usage']
                
                return LLMCallResult(
                    text=text,
                    error=None,
                    token_usage=token_usage,
                    estimated_cost=estimated_cost
                )
                
        except asyncio.TimeoutError:
            return LLMCallResult(
                text="",
                error=f"Request timed out after {config.timeout}s"
            )
        except aiohttp.ClientError as e:
            return LLMCallResult(
                text="",
                error=f"Network error: {str(e)}"
            )
        except Exception as e:
            return LLMCallResult(
                text="",
                error=f"Unexpected error: {str(e)}"
            )


def get_backend(config: Optional[LLMConfig] = None) -> LLMBackend:
    """Factory function to get appropriate backend."""
    if config is None:
        from .config import load_llm_config
        config = load_llm_config()
    
    return OpenAIBackend(config)
