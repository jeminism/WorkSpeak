"""
MessageIntercepto r

Detects Slack text input fields and monitors for message composition
and send events across all supported platforms.
"""

import time
import logging
from abc import ABC, abstractmethod
from typing import Optional, Callable, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class MessageState:
    """Current state of a message being composed"""
    channel_type: str  # 'dm', 'channel', 'group'
    channel_id: str
    text: str
    timestamp: float
    
    @property
    def is_empty(self) -> bool:
        return not self.text or self.text.strip() == ""


class PlatformDetector(ABC):
    """Abstract base class for platform detection"""
    
    @abstractmethod
    def is_slack_running(self) -> bool:
        """Check if Slack application is currently running"""
        pass
    
    @abstractmethod
    def get_input_field(self) -> Optional[Tuple[str, str]]:
        """Get current input field location and content
        
        Returns: (channel_id, text) or None if no input field found
        """
        pass


class WindowsDetector(PlatformDetector):
    """Windows-specific Slack detection using UI Automation"""
    
    def __init__(self):
        try:
            import comtypes
            import UIAutomation as uia
            self.uia = uia
            self.can_detect = True
        except ImportError:
            logger.warning("UIAutomation not available on Windows")
            self.can_detect = False
    
    def is_slack_running(self) -> bool:
        if not self.can_detect:
            return False
        
        try:
            # Look for Slack window by class name
            slack_window = self.uia.WindowControl(ClassName="Slack")
            return slack_window.IsNone is False
        except Exception as e:
            logger.debug(f"Windows detection error: {e}")
            return False
    
    def get_input_field(self) -> Optional[Tuple[str, str]]:
        if not self.can_detect:
            return None
        
        try:
            # Find the message input field in Slack
            # Slack uses Edit control for message input
            edit_control = self.uia.EditControl(AutoName="Type a message")
            
            if edit_control.IsNone:
                return None
            
            text = edit_control.GetValueControl().Value
            channel_id = self._detect_channel_id()
            
            return (channel_id, text) if text else None
        except Exception as e:
            logger.debug(f"Get input field error: {e}")
            return None
    
    def _detect_channel_id(self) -> str:
        """Extract channel ID from current context"""
        # In production, this would inspect the window hierarchy
        # to find the current channel identifier
        # For now, return a placeholder
        return "detecting"


class macOSDetector(PlatformDetector):
    """macOS-specific Slack detection using Accessibility API"""
    
    def __init__(self):
        try:
            import ApplicationServices
            import Quartz
            self.can_detect = True
        except ImportError:
            logger.warning("Accessibility framework not available on macOS")
            self.can_detect = False
    
    def is_slack_running(self) -> bool:
        if not self.can_detect:
            return False
        
        try:
            import AppKit
            app = AppKit.NSRunningApplication.runningApplicationWithCFBundleIdentifier_("com.slack.Slack")
            return app is not None
        except Exception as e:
            logger.debug(f"macOS detection error: {e}")
            return False
    
    def get_input_field(self) -> Optional[Tuple[str, str]]:
        if not self.can_detect:
            return None
        
        # macOS accessibility API implementation
        # Would use AXUIElement to find text fields
        return None


class LinuxDetector(PlatformDetector):
    """Linux-specific Slack detection"""
    
    def is_slack_running(self) -> bool:
        try:
            import subprocess
            result = subprocess.run(
                ["pgrep", "-x", "slack"],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception as e:
            logger.debug(f"Linux detection error: {e}")
            return False
    
    def get_input_field(self) -> Optional[Tuple[str, str]]:
        # Linux implementation would use xdotool or similar
        return None


class BrowserDetector(PlatformDetector):
    """Web Slack detection for browser integration"""
    
    def __init__(self):
        try:
            from selenium import webdriver
            self.webdriver = webdriver
            self.can_detect = True
        except ImportError:
            logger.warning("Selenium not available for browser detection")
            self.can_detect = False
    
    def is_slack_running(self) -> bool:
        if not self.can_detect:
            return False
        
        try:
            # Check if Slack web tab is open
            # This would use browser automation to check tabs
            return False  # Placeholder
        except Exception as e:
            logger.debug(f"Browser detection error: {e}")
            return False
    
    def get_input_field(self) -> Optional[Tuple[str, str]]:
        if not self.can_detect:
            return None
        
        # Would use JavaScript to access the message input field
        # in the browser version of Slack
        return None


class SlackDetector:
    """Platform-agnostic Slack detection"""
    
    def __init__(self):
        import platform
        
        self.system = platform.system().lower()
        self.detector = self._create_detector()
    
    def _create_detector(self) -> PlatformDetector:
        """Create platform-specific detector"""
        if self.system == "windows":
            return WindowsDetector()
        elif self.system == "darwin":
            return macOSDetector()
        elif self.system == "linux":
            return LinuxDetector()
        else:
            logger.warning(f"Unsupported platform: {self.system}")
            return PlatformDetector()  # Fallback
    
    def is_slack_running(self) -> bool:
        """Check if Slack is running"""
        return self.detector.is_slack_running()
    
    def get_input_field(self) -> Optional[Tuple[str, str]]:
        """Get current input field"""
        return self.detector.get_input_field()


class MessageInterceptor:
    """Monitors Slack input fields for message composition"""
    
    def __init__(self, on_message_detected: Callable[[MessageState], None],
                 on_send_detected: Callable[[MessageState], None],
                 poll_interval: float = 0.5):
        self.on_message_detected = on_message_detected
        self.on_send_detected = on_send_detected
        self.poll_interval = poll_interval
        
        self.detector = SlackDetector()
        self.detected_fields: dict = {}  # Track input fields
        
        self._running = False
        self._background_thread = None
    
    def start(self):
        """Start monitoring for Slack messages"""
        if self._running:
            logger.warning("Interceptor already running")
            return
        
        logger.info("Starting message interceptor...")
        self._running = True
        self._monitor_loop()
    
    def stop(self):
        """Stop monitoring"""
        self._running = False
        logger.info("Stopping message interceptor...")
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        import threading
        
        def loop():
            last_text = ""
            last_channel = ""
            
            while self._running:
                try:
                    # Check if Slack is running
                    if not self.detector.is_slack_running():
                        last_text = ""
                        time.sleep(self.poll_interval)
                        continue
                    
                    # Get current input field
                    result = self.detector.get_input_field()
                    
                    if result is None:
                        last_text = ""
                        time.sleep(self.poll_interval)
                        continue
                    
                    channel_id, current_text = result
                    
                    # Detect new message
                    if current_text and current_text != last_text:
                        state = MessageState(
                            channel_type=self._classify_channel(channel_id),
                            channel_id=channel_id,
                            text=current_text,
                            timestamp=time.time()
                        )
                        self.on_message_detected(state)
                        last_text = current_text
                        last_channel = channel_id
                    
                    # Detect send action (simplified - in production would check for specific key events)
                    elif not current_text and last_text:
                        # Text cleared after being set - likely sent
                        state = MessageState(
                            channel_type=self._classify_channel(last_channel),
                            channel_id=last_channel,
                            text=last_text,
                            timestamp=time.time()
                        )
                        self.on_send_detected(state)
                        last_text = ""
                    
                    time.sleep(self.poll_interval)
                
                except Exception as e:
                    logger.error(f"Monitor loop error: {e}")
                    time.sleep(self.poll_interval)
        
        self._background_thread = threading.Thread(target=loop, daemon=True)
        self._background_thread.start()
    
    def _classify_channel(self, channel_id: str) -> str:
        """Classify channel type based on ID prefix"""
        if not channel_id or channel_id == "detecting":
            return "unknown"
        
        # Slack channel prefixes:
        # C = channel, D = DM, G = group DM
        prefixes = {
            'C': 'channel',
            'D': 'dm',
            'G': 'group',
            'U': 'dm',  # User ID in DM
        }
        
        return prefixes.get(channel_id[0], "unknown")
