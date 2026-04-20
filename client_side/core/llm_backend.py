"""
LLM Backend for client-side rewriting

Reuses the same LLM infrastructure as the Slack bot for consistency.
"""

import requests
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class LLMCallResult:
    """Result from LLM call"""
    text: str
    token_usage: int = None
    error: str = None


class LLMBackend(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    def generate(self, prompt: str, config) -> LLMCallResult:
        """Generate rewritten text"""
        pass


class OpenAIBackend(LLMBackend):
    """OpenAI-compatible endpoint backend."""
    
    def generate(self, prompt: str, config) -> LLMCallResult:
        try:
            response = requests.post(
                config.endpoint,
                headers={
                    "Authorization": f"Bearer {config.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": config.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": 500
                },
                timeout=config.timeout
            )
            response.raise_for_status()
            data = response.json()
            text = data['choices'][0]['message']['content']
            token_count = data.get('usage', {}).get('total_tokens', 0)
            return LLMCallResult(text=text, token_usage=token_count)
        except Exception as e:
            return LLMCallResult(text="", error=str(e))


def get_backend() -> OpenAIBackend:
    """Get default LLM backend"""
    return OpenAIBackend()
