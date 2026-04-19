import os
import yaml
from dataclasses import dataclass
from typing import Optional

@dataclass
class LLMConfig:
    endpoint: str
    api_key: str
    model: str = "gpt-4o"
    provider: str = "openai"

def load_llm_config() -> LLMConfig:
    """Load LLM config with priority: env vars > YAML file > raise error."""
    
    # Priority 1: Environment variables
    api_key = os.getenv("LLM_API_KEY")
    endpoint = os.getenv("LLM_ENDPOINT")
    
    if api_key and endpoint:
        return LLMConfig(
            endpoint=endpoint,
            api_key=api_key,
            model=os.getenv("LLM_MODEL", "gpt-4o"),
            provider=os.getenv("LLM_PROVIDER", "openai")
        )
    
    # Priority 2: YAML config file
    config_path = os.getenv("LLM_CONFIG_FILE", "config/llm_config.yaml")
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f)
        return LLMConfig(
            endpoint=config_data['endpoint'],
            api_key=config_data['api_key'],
            model=config_data.get('model', 'gpt-4o'),
            provider=config_data.get('provider', 'openai')
        )
    
    raise ValueError(
        "No LLM configuration found. "
        "Set LLM_API_KEY and LLM_ENDPOINT env vars, "
        "or create config/llm_config.yaml"
    )
