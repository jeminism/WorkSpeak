import os
import pytest
from slack_message_bot.config import load_llm_config, LLMConfig

def test_env_var_priority():
    os.environ['LLM_API_KEY'] = 'env_key'
    os.environ['LLM_ENDPOINT'] = 'env_endpoint'
    config = load_llm_config()
    assert config.api_key == 'env_key'
    assert config.endpoint == 'env_endpoint'
    assert config.model == 'gpt-4o'

def test_env_var_model_override():
    os.environ['LLM_API_KEY'] = 'test_key'
    os.environ['LLM_ENDPOINT'] = 'https://test.com/api'
    os.environ['LLM_MODEL'] = 'custom-model'
    os.environ['LLM_PROVIDER'] = 'custom'
    config = load_llm_config()
    assert config.model == 'custom-model'
    assert config.provider == 'custom'
