"""
Message Preview Window

Shows rewrite preview and allows user confirmation before sending.
"""

import logging
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PreviewOptions:
    """Options for preview display"""
    auto_rewrite: bool = True
    show_preview_window: bool = True
    confirm_on_low_score: bool = True
    timeout_seconds: int = 5


class MessagePreview:
    """
    Handles preview logic for client-side rewriting.
    
    Decision tree:
    1. If auto_rewrite=False, always show preview
    2. If quality_score >= 0.85, auto-apply (unless timeout)
    3. If quality_score < 0.85 or low score, show preview
    """
    
    def __init__(self, options: PreviewOptions = None):
        self.options = options or PreviewOptions()
        self.last_preview: Optional[str] = None
        self.user_confirmed: bool = False
    
    def should_show_preview(self, quality_score: float, 
                           auto_rewrite: bool = True) -> bool:
        """
        Determine if preview window should be shown.
        
        Returns True if user should see preview before sending.
        """
        if not auto_rewrite:
            return True
        
        if quality_score >= 0.85:
            # High quality rewrite - auto-apply
            return False
        
        if self.options.confirm_on_low_score and quality_score < 0.5:
            # Low quality - definitely show preview
            return True
        
        # Medium quality - show preview for user to verify
        return True
    
    def should_apply_rewrite(self, decision: str) -> bool:
        """
        Determine if rewrite should be automatically applied.
        
        Decision logic:
        - 'accept': Apply rewrite
        - 'fallback': Show preview
        - 'reject': Don't apply
        """
        if decision == 'accept':
            return True
        elif decision == 'fallback':
            return self.options.show_preview_window
        else:
            return False
    
    def format_preview(self, original: str, rewritten: str,
                      quality_score: float, decision: str) -> str:
        """Format preview text for display"""
        
        # Truncate long messages
        orig_preview = self._truncate(original, 200)
        rewrt_preview = self._truncate(rewritten, 200)
        
        preview = f"""
┌─────────────────────────────────────────────────────┐
│                    PREVIEW                          │
├─────────────────────────────────────────────────────┤
│ ORIGINAL:                                          │
│ {orig_preview:<48} │
│                                                      │
│ REWRITTEN:                                         │
│ {rewrt_preview:<48} │
│                                                      │
│ Quality Score: {quality_score:.2f}   Decision: {decision:<10} │
├─────────────────────────────────────────────────────┤
│ Auto-apply on high quality ≥0.85                    │
│ Press ESC to cancel, ENTER to approve               │
└─────────────────────────────────────────────────────┘
"""
        return preview
    
    def _truncate(self, text: str, max_length: int) -> str:
        """Truncate text with ellipsis"""
        if len(text) <= max_length:
            return text
        return text[:max_length-3] + "..."
    
    def track_preview(self, window_text: str):
        """Track last preview shown"""
        self.last_preview = window_text
    
    def clear_preview(self):
        """Clear preview tracking"""
        self.last_preview = None
        self.user_confirmed = False
