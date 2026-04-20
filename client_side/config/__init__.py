"""
Configuration management for WorkSpeak Client

Supports environment variables, YAML config, and CLI overrides.
Same configuration system as the Slack bot for consistency.
"""

import os
import yaml
from dataclasses import dataclass
from typing import Optional, List
from pathlib import Path


@dataclass
class LLMConfig:
    """LLM backend configuration"""
    endpoint: str
    api_key: str
    model: str = "gpt-4o"
    provider: str = "openai"
    timeout: int = 30


@dataclass
class ClientConfig:
    """Complete client-side configuration"""
    llm: LLMConfig
    auto_rewrite: bool = True
    preview_enabled: bool = True
    keyboard_shortcut: str = "Ctrl+Shift+R"
    detect_slack: bool = True
    platforms: List[str] = None
    log_level: str = "INFO"
    log_file: str = "logs/workSpeak_client.log"
    
    def __post_init__(self):
        if self.platforms is None:
            self.platforms = ["desktop", "browser"]


def load_client_config(config_path: Optional[str] = None) -> ClientConfig:
    """Load client configuration with priority: env vars > YAML file > defaults"""
    
    # Priority 1: Environment variables
    llm_api_key = os.getenv("LLM_API_KEY")
    llm_endpoint = os.getenv("LLM_ENDPOINT")
    
    if not llm_api_key or not llm_endpoint:
        # Priority 2: YAML config file
        if config_path is None:
            config_path = os.getenv("CLIENT_CONFIG_FILE", "config/client_config.yaml")
        
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config_data = yaml.safe_load(f)
                
            return ClientConfig(
                llm=LLMConfig(
                    endpoint=config_data['llm']['endpoint'],
                    api_key=config_data['llm']['api_key'],
                    model=config_data['llm'].get('model', 'gpt-4o'),
                    provider=config_data['llm'].get('provider', 'openai'),
                    timeout=config_data['llm'].get('timeout', 30)
                ),
                auto_rewrite=config_data.get('auto_rewrite', True),
                preview_enabled=config_data.get('preview_enabled', True),
                keyboard_shortcut=config_data.get('keyboard_shortcut', 'Ctrl+Shift+R'),
                platforms=config_data.get('platforms', ['desktop', 'browser']),
                log_level=config_data.get('log_level', 'INFO')
            )
    
    # Priority 3: Environment variables (if file not found)
    return ClientConfig(
        llm=LLMConfig(
            endpoint=llm_endpoint,
            api_key=llm_api_key,
            model=os.getenv("LLM_MODEL", "gpt-4o"),
            provider=os.getenv("LLM_PROVIDER", "openai"),
            timeout=int(os.getenv("LLM_TIMEOUT", "30"))
        ),
        auto_rewrite=os.getenv("CLIENT_AUTO_REWRITE", "true").lower() == "true",
        preview_enabled=os.getenv("CLIENT_PREVIEW_ENABLED", "true").lower() == "true",
        keyboard_shortcut=os.getenv("CLIENT_KEYBOARD_SHORTCUT", "Ctrl+Shift+R"),
        platforms=["desktop", "browser"],
        log_level=os.getenv("CLIENT_LOG_LEVEL", "INFO")
    )


def create_default_config(config_path: str = "config/client_config.yaml"):
    """Create default configuration file if it doesn't exist"""
    Path(config_path).parent.mkdir(parents=True, exist_ok=True)
    
    config_template = """
# WorkSpeak Client Configuration

# LLM Configuration (required)
llm:
  endpoint: "https://api.openai.com/v1/chat/completions"
  api_key: "your-api-key-here"
  model: "gpt-4o"
  provider: "openai"
  timeout: 30

# Client Behavior
auto_rewrite: true
preview_enabled: true
keyboard_shortcut: "Ctrl+Shift+R"

# Platform Detection
detect_slack: true
platforms:
  - desktop
  - browser

# Logging
log_level: INFO
log_file: "logs/workSpeak_client.log"
"""
    
    Path(config_path).write_text(config_template.strip())
    print(f"Created default config at: {config_path}")
    print("Please edit this file and add your LLM API key")
