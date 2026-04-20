"""
Slack Desktop App Integration Layer

Provides interfaces to monitor and control Slack's text input fields
on Windows, macOS, and Linux platforms.
"""

from .slack_detector import SlackDetector
from .desktop_hook import DesktopHook
from .accessibility_monitor import AccessibilityMonitor

__all__ = [
    "SlackDetector",
    "DesktopHook",
    "AccessibilityMonitor"
]
