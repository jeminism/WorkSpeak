"""
Accessibility Monitor

Uses accessibility APIs to monitor Slack across all platforms
as a fallback when native hooks are unavailable.
"""

import logging
import time
from abc import ABC, abstractmethod
from typing import Optional, Callable

logger = logging.getLogger(__name__)


class AccessibilityMonitor(ABC):
    """Abstract base class for accessibility monitoring"""
    
    @abstractmethod
    def monitor_text_field(self) -> Optional[str]:
        """Monitor current text field content"""
        pass
    
    @abstractmethod
    def focus_field(self) -> bool:
        """Focus on the message input field"""
        pass
    
    @abstractmethod
    def inject_text(self, text: str) -> bool:
        """Inject text into focused field"""
        pass


class AccessibilityMonitorFallback:
    """
    Fallback monitor using screen scraping and OCR.
    This is slower but works on any platform with screen access.
    """
    
    def __init__(self):
        self.tesseract_available = False
        self.screenshot_available = False
        
        try:
            import pytesseract
            from PIL import Image
            self.tesseract_available = True
            self.screenshot_available = True
            logger.info("Accessibility monitor initialized (OCR mode)")
        except ImportError:
            logger.warning("Accessibility monitor not available (pytesseract not installed)")
    
    def monitor_text_field(self) -> Optional[str]:
        """Use OCR to extract text from screen"""
        if not self.tesseract_available or not self.screenshot_available:
            return None
        
        try:
            import pytesseract
            from PIL import Image
            import pyautogui
            
            # Take screenshot of likely input area (bottom of screen)
            width, height = pyautogui.size()
            screenshot = pyautogui.screenshot(
                region=(0, height - 300, width, 200)
            )
            
            # Extract text
            text = pytesseract.image_to_string(screenshot)
            return text if text.strip() else None
            
        except Exception as e:
            logger.error(f"OCR monitor error: {e}")
            return None
    
    def focus_field(self) -> bool:
        """Try to focus input field - would require more complex logic"""
        # In production: use screen coordinates, click simulation, etc.
        logger.warning("Accessibility monitor - focus not implemented")
        return False
    
    def inject_text(self, text: str) -> bool:
        """Inject text using clipboard or keyboard"""
        try:
            import pyautogui
            pyautogui.write(text, interval=0.01)
            return True
        except Exception as e:
            logger.error(f"Text injection error: {e}")
            return False
