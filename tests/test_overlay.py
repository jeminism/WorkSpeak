"""
Test suite for WorkSpeak CDP Overlay
Tests core module functionality without requiring actual Slack instance
"""

import pytest
from core.config import LLMConfig, load_llm_config, validate_config
from core.llm_backend import OpenAIBackend, LLMCallResult


class TestLLMConfig:
    """Tests for LLM configuration."""
    
    def test_config_creation(self):
        """Test creating an LLMConfig."""
        config = LLMConfig(
            endpoint="https://api.example.com",
            api_key="test_key",
            model="gpt-4o"
        )
        
        assert config.endpoint == "https://api.example.com"
        assert config.api_key == "test_key"
        assert config.model == "gpt-4o"
    
    def test_default_config(self):
        """Test default LLMConfig values."""
        config = LLMConfig()
        
        assert config.model == "gpt-4o-mini"
        assert config.provider == "openai"
        assert config.timeout == 60
        assert config.temperature == 0.2
    
    def test_validate_config_valid(self):
        """Test validation with valid config."""
        config = LLMConfig(
            endpoint="https://api.example.com",
            api_key="test",
            model="gpt-4o"
        )
        
        is_valid, errors = validate_config(config)
        
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_config_missing_endpoint(self):
        """Test validation with missing endpoint."""
        config = LLMConfig(api_key="test", model="gpt-4o")
        
        is_valid, errors = validate_config(config)
        
        assert is_valid is False
        assert len(errors) > 0
        assert any("endpoint" in str(e).lower() for e in errors)
    
    def test_validate_config_missing_api_key(self):
        """Test validation with missing API key."""
        config = LLMConfig(endpoint="https://api.com", model="gpt-4o")
        
        is_valid, errors = validate_config(config)
        
        assert is_valid is False
        assert len(errors) > 0
        assert any("api_key" in str(e).lower() for e in errors)


class TestOpenAIBackend:
    """Tests for OpenAI backend."""
    
    def test_backend_creation(self):
        """Test creating an OpenAIBackend."""
        config = LLMConfig(
            endpoint="https://api.openai.com/v1/chat/completions",
            api_key="test",
            model="gpt-4o-mini"
        )
        
        backend = OpenAIBackend(config)
        
        assert backend.config == config
        assert backend.api_url == config.endpoint
    
    def test_backend_default_config(self):
        """Test backend with default config."""
        backend = OpenAIBackend(LLMConfig())
        
        assert backend.api_url == ""
        assert backend.config.model == "gpt-4o-mini"


class TestMessageRewriter:
    """Tests for MessageRewriter."""
    
    def test_rewriter_init(self):
        """Test MessageRewriter initialization."""
        from core.rewriter import MessageRewriter
        
        rewriter = MessageRewriter()
        
        assert rewriter.backend is not None
    
    def test_rewrite_test_mode(self):
        """Test rewrite in test mode (no LLM config)."""
        from core.rewriter import MessageRewriter
        
        rewriter = MessageRewriter()
        
        # Without config, should return original text in test mode
        text, decision = rewriter.rewrite("Hello world")
        
        assert text == "Hello world"
        assert "test_mode" in decision


class TestOverlayModules:
    """Tests for overlay modules."""
    
    def test_rewrite_request(self):
        """Test creating a rewrite request."""
        from overlay.worker import RewriteRequest
        
        request = RewriteRequest(
            original_text="Hello world",
            channel_context="#general",
            request_id="test_123"
        )
        
        assert request.original_text == "Hello world"
        assert request.channel_context == "#general"
        assert request.request_id == "test_123"
    
    def test_rewrite_status_enum(self):
        """Test RewriteStatus enum values."""
        from overlay.worker import RewriteStatus
        
        assert RewriteStatus.PENDING.value == "pending"
        assert RewriteStatus.PROCESSING.value == "processing"
        assert RewriteStatus.COMPLETED.value == "completed"
    
    def test_ui_state(self):
        """Test UIState dataclass."""
        from overlay.overlay_ui import UIState
        
        state = UIState()
        
        assert state.visible is False
        assert state.has_suggestion is False
        assert state.needs_action is False
        
        # Test with content
        state2 = UIState(visible=True, rewritten_text="Test rewrite")
        assert state2.has_suggestion is True


# Integration test markers
@pytest.mark.integration
class TestIntegration:
    """Integration tests requiring actual dependencies."""
    
    @pytest.mark.skip(reason="Requires actual LLM endpoint")
    def test_llm_call(self):
        """Test making an actual LLM call."""
        import os
        
        endpoint = os.getenv("TEST_LLM_ENDPOINT")
        api_key = os.getenv("TEST_LLM_API_KEY")
        
        if not endpoint or not api_key:
            pytest.skip("TEST_LLM_ENDPOINT and TEST_LLM_API_KEY must be set")
        
        config = LLMConfig(endpoint=endpoint, api_key=api_key)
        backend = OpenAIBackend(config)
        
        prompt = "Say hello in one word"
        result = backend.generate(prompt)
        
        assert result.error is None
        assert len(result.text) > 0
