import requests
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class LLMCallResult:
    text: str
    token_usage: int = None
    error: str = None

class LLMBackend(ABC):
    """Abstract base class for LLM providers."""
    
    def _normalize_prompt(self, original_text: str, thread_context: str = "") -> str:
        """Build the prompt for rewriting."""
        context_section = f"\n\nThread context:\n{thread_context}\n\n" if thread_context else ""
        
        return f"""You are a professional message editor. Rewrite the following Slack message to be:
- More professional yet friendly
- Concise (no long prose or circular statements)
- Semantically equivalent to the original

Original message:
{original_text}{context_section}

Rewrite the message below. Return ONLY the rewritten text, nothing else. No explanation, no notes, no preamble. Just the rewritten message.
"""
    
    @abstractmethod
    def generate(self, prompt: str, config) -> LLMCallResult:
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
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            text = data['choices'][0]['message']['content']
            token_count = data.get('usage', {}).get('total_tokens', 0)
            return LLMCallResult(text=text, token_usage=token_count)
        except Exception as e:
            return LLMCallResult(text="", error=str(e))

def get_backend() -> OpenAIBackend:
    return OpenAIBackend()
