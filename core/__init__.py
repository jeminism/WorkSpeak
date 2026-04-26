"""
WorkSpeak Core Libraries
Shared components for both CDP overlay and Slack bot implementations.
"""

from .config import LLMConfig, load_llm_config
from .llm_backend import (
    LLMBackend, 
    OpenAIBackend,
    get_backend,
    LLMCallResult
)
from .logging_config import setup_logging
from .rewriter import MessageRewriter

__all__ = [
    'LLMConfig',
    'load_llm_config',
    'LLMBackend',
    'OpenAIBackend', 
    'get_backend',
    'LLMCallResult',
    'setup_logging',
    'MessageRewriter',
]
