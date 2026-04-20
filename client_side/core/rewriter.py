"""
Client Rewriter

LLM-based message rewriting optimized for pre-send use cases
(without thread context from Slack API).
"""

import re
import logging
from typing import Optional, Tuple
from dataclasses import dataclass

from .llm_backend import LLMBackend, LLMCallResult, get_backend
from ..config import load_client_config

logger = logging.getLogger(__name__)


@dataclass
class RewriteResult:
    """Result of a rewrite attempt"""
    success: bool
    rewritten_text: str
    original_text: str
    quality_score: float
    decision: str  # 'accept', 'fallback', 'reject'
    error: Optional[str] = None


class ClientRewriter:
    """
    Rewrite messages for client-side use.
    
    Differs from Slack bot rewriter:
    - No access to Slack thread context
    - Needs to work faster (pre-send)
    - Can show preview before sending
    - Must be robust without Slack API fallbacks
    """
    
    # Post-processing patterns for LLM artifacts
    METADATA_PATTERNS = [
        r'with\s+\d+\s+tokens?\s+used(?:[,].*)?(?:\$?\d+\.?\d*)?(?:,|$).*a\s+successful\s*outcome',
        r'with\s+\d+\s+tokens?\s+used',
        r'Estimated\s+cost:\s+\$?\d+\.?\d+',
        r'Quality\s+score:\s*[\d.]+',
        r'\d+\s+iterations?',
        r'#\s+Rewritten:',
        r'###\s*(Summary|Explanation|Reasoning|Thinking)',
        r'(In\s+summary|To\s+summarize|Here is the revised):',
        r'Here is the rewritten text:',
    ]
    
    def __init__(self):
        self.config = load_client_config()
        self.backend = get_backend()
        self.post_processors = [self._remove_metadata, self._remove_explanations]
    
    def rewrite(self, original_text: str, channel_type: str = "unknown") -> RewriteResult:
        """
        Rewrite a message.
        
        Args:
            original_text: The message to rewrite
            channel_type: 'dm', 'channel', 'group', etc.
        
        Returns:
            RewriteResult with rewritten text and quality metrics
        """
        
        # Step 1: Generate rewrite
        prompt = self._build_prompt(original_text, channel_type)
        result = self.backend.generate(prompt, self.config.llm)
        
        if result.error:
            return RewriteResult(
                success=False,
                rewritten_text=original_text,
                original_text=original_text,
                quality_score=0.0,
                decision='reject',
                error=result.error
            )
        
        # Step 2: Post-process
        rewritten = result.text
        for processor in self.post_processors:
            rewritten = processor(rewritten)
            if not rewritten:
                return RewriteResult(
                    success=False,
                    rewritten_text=original_text,
                    original_text=original_text,
                    quality_score=0.0,
                    decision='reject',
                    error="Post-processing resulted in empty text"
                )
        
        # Step 3: Quality check (simplified for client-side)
        quality_score = self._quick_quality_check(original_text, rewritten)
        decision = self._make_decision(quality_score, original_text, rewritten)
        
        return RewriteResult(
            success=True,
            rewritten_text=rewritten,
            original_text=original_text,
            quality_score=quality_score,
            decision=decision
        )
    
    def _build_prompt(self, text: str, channel_type: str) -> str:
        """Build rewrite prompt for client-side use"""
        
        # Context-aware prompts
        channel_context = ""
        if channel_type == "dm":
            channel_context = "\n\nThis is a direct message to another person. Keep it professional but personal."
        elif channel_type == "group":
            channel_context = "\n\nThis is a group message with multiple people. Be clear and inclusive."
        else:
            channel_context = "\n\nThis is a workplace message. Be professional and concise."
        
        return f"""You are a professional message editor. Rewrite the following text to be:
- More professional yet friendly
- Concise (no long prose or circular statements)
- Clear and grammatically correct
- Appropriately toned for {channel_type} communication

Original text:
{text}{channel_context}

Rewrite the message above. Return ONLY the rewritten text, nothing else. No explanation, no notes, no preamble. Just the rewritten message."""
    
    def _remove_metadata(self, text: str) -> str:
        """Remove LLM metadata patterns"""
        result = text
        for pattern in self.METADATA_PATTERNS:
            result = re.sub(pattern, '', result, flags=re.IGNORECASE)
        
        # Remove common intro/outro text
        intro_patterns = [
            r'This revised response aims to:',
            r'The rewritten text is:',
            r'Here is the rewritten version:',
        ]
        
        result = text
        for pattern in intro_patterns:
            result = re.sub(pattern, '', result, flags=re.IGNORECASE)
        
        return result.strip()
    
    def _remove_explanations(self, text: str) -> str:
        """Remove explanations and reasoning blocks"""
        # Remove numbered lists from explanations
        result = re.sub(r'^\d+\.\\s+', '', text, flags=re.MULTILINE)
        
        # Remove bullet points
        result = re.sub(r'^[-•*]\\s+', '', result, flags=re.MULTILINE)
        
        # Remove headers
        result = re.sub(r'^###?.*\\n', '', result, flags=re.MULTILINE)
        
        return result.strip()
    
    def _quick_quality_check(self, original: str, rewritten: str) -> float:
        """Quick quality check (no embeddings to keep it fast)"""
        
        # Check 1: Length ratio (0-1)
        orig_words = len(original.split())
        rewrt_words = len(rewritten.split())
        
        if orig_words == 0:
            length_score = 1.0
        else:
            ratio = rewrt_words / orig_words
            if ratio <= 0.3 or ratio >= 3.0:
                length_score = 0.3
            else:
                length_score = 1.0
        
        # Check 2: Change detection (has it actually changed?)
        if rewritten.lower() == original.lower():
            change_score = 0.0
        else:
            change_score = 1.0
        
        # Check 3: Basic professionalism heuristics
        unprofessional = ['lol', 'omg', 'wtf', 'idk', 'tbh', 'imo', 'fyi', 'thx', 'thx!']
        lower_text = rewritten.lower()
        violations = sum(1 for word in unprofessional if word in lower_text)
        professionalism_score = max(0.0, 1.0 - (violations * 0.2))
        
        # Weighted average
        overall = 0.3 * length_score + 0.3 * change_score + 0.4 * professionalism_score
        return round(overall, 2)
    
    def _make_decision(self, score: float, original: str, rewritten: str) -> str:
        """Make rewrite decision based on quality score"""
        
        if score >= 0.75:
            return 'accept'  # Good rewrite
        elif score >= 0.5:
            return 'fallback'  # Acceptable but not great
        else:
            return 'reject'  # Don't rewrite


class ClientRewriterWithPreview(ClientRewriter):
    """Rewriter with preview capability for user confirmation"""
    
    def rewrite_with_preview(self, original_text: str, 
                           channel_type: str = "unknown") -> Tuple[RewriteResult, bool]:
        """
        Rewrite and return whether to auto-apply or show preview.
        
        Returns: (result, should_preview)
        """
        result = self.rewrite(original_text, channel_type)
        
        # Always show preview for first-time users or low scores
        should_preview = (
            result.quality_score < 0.85 or
            result.decision == 'fallback' or
            result.decision == 'reject'
        )
        
        return result, should_preview
