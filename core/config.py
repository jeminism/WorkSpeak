"""
Configuration loading for WorkSpeak.
Supports both YAML config files and environment variables.
"""

import os
import yaml
from dataclasses import dataclass, field
from typing import Optional

DEFAULT_CONFIG_PATH = "config/llm_config.yaml"


@dataclass
class LLMConfig:
    """Configuration for LLM backend."""
    endpoint: str = ""
    api_key: str = ""
    model: str = "gpt-4o-mini"
    provider: str = "openai"
    timeout: int = 60
    max_retries: int = 3
    
    # Temperature and other inference params
    temperature: float = 0.2
    max_tokens: int = 500
    
    # Source of config (for logging/debugging)
    config_source: str = "default"


def load_llm_config(config_path: Optional[str] = None) -> LLMConfig:
    """
    Load LLM configuration from environment variables, YAML file, or defaults.
    
    Priority order (highest to lowest):
    1. Environment variables
    2. Config file specified by config_path
    3. Default config file
    4. Hardcoded defaults
    
    Environment variable mapping:
    - LLM_ENDPOINT -> endpoint
    - LLM_API_KEY -> api_key  
    - LLM_MODEL -> model
    - LLM_PROVIDER -> provider
    - LLM_TIMEOUT -> timeout
    - LLM_MAX_RETRIES -> max_retries
    """
    
    # Check environment variables first (highest priority)
    endpoint = os.getenv('LLM_ENDPOINT')
    api_key = os.getenv('LLM_API_KEY')
    model = os.getenv('LLM_MODEL', 'gpt-4o-mini')
    provider = os.getenv('LLM_PROVIDER', 'openai')
    timeout = int(os.getenv('LLM_TIMEOUT', '60'))
    max_retries = int(os.getenv('LLM_MAX_RETRIES', '3'))
    
    if endpoint and api_key:
        # Env vars provided
        return LLMConfig(
            endpoint=endpoint,
            api_key=api_key,
            model=model,
            provider=provider,
            timeout=timeout,
            max_retries=max_retries,
            config_source="environment"
        )
    
    # Try explicit config path
    if config_path and os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                config_dict = yaml.safe_load(f)
            
            return LLMConfig(
                endpoint=config_dict.get('endpoint', ''),
                api_key=config_dict.get('api_key', ''),
                model=config_dict.get('model', 'gpt-4o-mini'),
                provider=config_dict.get('provider', 'openai'),
                timeout=int(config_dict.get('timeout', 60)),
                max_retries=int(config_dict.get('max_retries', 3)),
                config_source=config_path
            )
        except Exception as e:
            print(f"Warning: Could not load config from {config_path}: {e}")
    
    # Try default config path
    default_path = DEFAULT_CONFIG_PATH
    if os.path.exists(default_path):
        try:
            with open(default_path, 'r') as f:
                config_dict = yaml.safe_load(f)
            
            return LLMConfig(
                endpoint=config_dict.get('endpoint', ''),
                api_key=config_dict.get('api_key', ''),
                model=config_dict.get('model', 'gpt-4o-mini'),
                provider=config_dict.get('provider', 'openai'),
                timeout=int(config_dict.get('timeout', 60)),
                max_retries=int(config_dict.get('max_retries', 3)),
                config_source=default_path
            )
        except Exception as e:
            print(f"Warning: Could not load default config: {e}")
    
    # Return defaults
    return LLMConfig(config_source="default")


def validate_config(config: LLMConfig) -> tuple[bool, list[str]]:
    """
    Validate LLM configuration.
    Returns (is_valid, list_of_errors).
    """
    errors = []
    
    if not config.endpoint:
        errors.append("LLM_ENDPOINT is not configured")
    
    if not config.api_key:
        errors.append("LLM_API_KEY is not configured")
    
    if not config.model:
        errors.append("LLM_MODEL is not configured")
    
    return (len(errors) == 0, errors)
