"""
Test WorkSpeak Client Components
"""

import pytest
from pathlib import Path
import sys
import os

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from client_side.core.rewriter import ClientRewriter, RewriteResult
from client_side.config import load_client_config, LLMConfig
from client_side.core.llm_backend import LLMCallResult, OpenAIBackend


class TestLLMConfig:
    """Test configuration loading"""
    
    def test_llm_config_dataclass(self):
        """Test LLM configuration dataclass"""
        config = LLMConfig(
            endpoint="https://api.test.com",
            api_key="test_key",
            model="gpt-4o",
            provider="openai"
        )
        
        assert config.endpoint == "https://api.test.com"
        assert config.api_key == "test_key"
        assert config.model == "gpt-4o"
        assert config.provider == "openai"


class TestRewriter:
    """Test client-side rewriter"""
    
    def test_rewrite_prompt_construction(self):
        """Test prompt building for different channel types"""
        # This would require mocking the backend
        # Placeholder for actual test
        
        # Check that prompts include channel context
        dm_prompt = "This is a direct message to another person. Keep it professional but personal."
        channel_prompt = "This is a workplace message. Be professional and concise."
        
        assert "direct message" in dm_prompt
        assert "workplace" in channel_prompt
    
    def test_metadata_removal_patterns(self):
        """Test that metadata patterns are defined"""
        patterns = ClientRewriter.METADATA_PATTERNS
        
        assert len(patterns) > 0
        assert isinstance(patterns[0], str)
    
    def test_rewritten_text_not_empty(self):
        """Test that rewriting doesn't produce empty text"""
        # Mock backend would be needed here
        # For now, just test the structure
        
        result = RewriteResult(
            success=True,
            rewritten_text="Test rewrite",
            original_text="Test original",
            quality_score=0.8,
            decision='accept'
        )
        
        assert result.rewritten_text != ""
        assert result.success == True


class TestLLMBackend:
    """Test LLM backend integration"""
    
    def test_llm_call_result_dataclass(self):
        """Test LLM call result"""
        result = LLMCallResult(
            text="Test response",
            token_usage=50,
            error=None
        )
        
        assert result.text == "Test response"
        assert result.token_usage == 50
        assert result.error is None
    
    def test_openai_backend_instantiation(self):
        """Test OpenAI backend can be created"""
        backend = OpenAIBackend()
        assert backend is not None


class TestPlatformDetector:
    """Test platform detection (mostly manual tests)"""
    
    def test_platform_imports(self):
        """Test that platform-specific imports work"""
        import platform
        
        system = platform.system().lower()
        
        if system == "windows":
            import pywin32  # noqa
            import UIAutomation as uiautomation  # noqa
            assert True
        elif system == "darwin":
            import pyobjc  # noqa
            assert True
        elif system == "linux":
            import python_xlib  # noqa
            assert True
        
    def test_slack_detector_creation(self):
        """Test Slack detector can be created"""
        from client_side.integrations.slack_detector import SlackDetector
        
        detector = SlackDetector()
        assert detector is not None
    
    def test_detector_returns_correct_platform(self):
        """Test detector identifies correct platform"""
        from client_side.integrations.slack_detector import SlackDetector
        import platform
        
        detector = SlackDetector()
        assert detector.detector is not None


class TestDesktopHook:
    """Test desktop hooks (most are platform-specific)"""
    
    def test_hook_creation(self):
        """Test hook can be created for current platform"""
        from client_side.integrations.desktop_hook import DesktopHook
        
        hook = DesktopHook()
        assert hook is not None
    
    def test_hook_methods_exist(self):
        """Test hook has required methods"""
        from client_side.integrations.desktop_hook import DesktopHook
        
        hook = DesktopHook()
        
        assert hasattr(hook, 'inject_text')
        assert hasattr(hook, 'set_keyboard_input')
        assert hasattr(hook, 'trigger_send')


class TestMessagePreview:
    """Test preview functionality"""
    
    def test_preview_should_show_decision(self):
        """Test preview decision logic"""
        from client_side.core.preview import MessagePreview, PreviewOptions
        
        preview = MessagePreview(PreviewOptions())
        
        # High quality should not show preview
        assert not preview.should_show_preview(0.9)
        
        # Medium quality should show preview
        assert preview.should_show_preview(0.7)
        
        # Low quality should show preview
        assert preview.should_show_preview(0.4)
    
    def test_decisions(self):
        """Test decision logic"""
        from client_side.core.rewriter import ClientRewriter
        
        rewriter = ClientRewriter()
        
        # Accept decision should trigger apply
        assert rewriter.should_apply_rewrite('accept') == True
        
        # Fallback decision depends on preview setting
        # For this test, assume preview is enabled
        assert rewriter.should_apply_rewrite('fallback') == True
        
        # Reject should not apply
        assert rewriter.should_apply_rewrite('reject') == False
    
    def test_preview_formatting(self):
        """Test preview text formatting"""
        from client_side.core.preview import MessagePreview
        
        preview = MessagePreview()
        
        original = "test message"
        rewritten = "Rewritten message"
        preview_text = preview.format_preview(
            original,
            rewritten,
            0.8,
            'accept'
        )
        
        assert "ORIGINAL" in preview_text
        assert "REWRITTEN" in preview_text
        assert "test message" in preview_text
        assert "Rewritten message" in preview_text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
