import pytest
from slack_message_bot.llm_backend import OpenAIBackend, LLMCallResult

def test_normalize_prompt_with_context():
    backend = OpenAIBackend()
    prompt = backend._normalize_prompt("hello world", "thread context here")
    assert "hello world" in prompt
    assert "thread context here" in prompt

def test_normalize_prompt_without_context():
    backend = OpenAIBackend()
    prompt = backend._normalize_prompt("hey guys lol")
    assert "hey guys lol" in prompt
    assert "Thread context" not in prompt

def test_normalize_prompt_structure():
    backend = OpenAIBackend()
    prompt = backend._normalize_prompt("test message")
    assert "professional message editor" in prompt
    assert "concise" in prompt.lower()
    assert "no explanation" in prompt.lower()
