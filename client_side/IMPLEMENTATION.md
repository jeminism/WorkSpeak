# WorkSpeak Client Implementation Guide

## Overview

This document explains how to implement a client-side message interceptor that can rewrite Slack messages before they're sent, including 1:1 DMs to other humans.

## Why Client-Side?

**The Problem**: Slack's privacy model prevents bots from seeing messages in private 1:1 DMs between two humans, even with `im:read` and `im:write` scopes.

**The Solution**: Monitor the message as you're typing, rewrite it locally, and replace it in the input field before you press send.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    YOUR COMPUTER                            │
│                                                             │
│  ┌──────────────┐    ┌────────────────────────────────┐   │
│  │  Slack App   │◀──▶│   WorkSpeak Client Agent       │   │
│  │              │    │                                │   │
│  │ [Message     │    │  1. Detect input field         │   │
│  │  Input]      │    │  2. Monitor text changes       │   │
│  │   ^  │       │    │  3. Intercept send action      │   │
│  │   │  │       │    │  4. Call LLM for rewrite       │   │
│  │   │  ▼       │    │  5. Replace text in field      │   │
│  └───┼──────────┘    │  6. Show preview (optional)     │   │
│      │              │  7. Apply rewrite               │   │
│      │              └────────────────────────────────┘   │
│      ▼                                                  │
│  ┌─────────────────────────────────────────────────────┐ │
│  │                LLM API (Remote)                     │ │
│  │  1. receives rewritten prompt                       │ │
│  │  2. returns professional version                    │ │
│  └─────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────┘
```

## Implementation Strategy

### 1. Platform Detection Layer

**File**: `integrations/slack_detector.py`

Purpose: Detect when Slack is running and locate message input fields.

**Windows Implementation**:
```python
import UIAutomation as uia
from win32gui import GetForegroundWindow

class WindowsDetector:
    def get_input_field(self):
        # Find Edit control with specific name
        edit_control = uia.EditControl(AutoName="Type a message")
        text = edit_control.GetValueControl().Value
        return edit_control, text
```

**macOS Implementation**:
```python
import AppKit
import Quartz

class macOSDetector:
    def get_input_field(self):
        # Use AXUIElement to find text fields in Slack
        # Requires Accessibility permissions
        pass
```

**Fallback**: Use screen OCR (slower but universal)

### 2. Message Interception

**File**: `core/interceptor.py`

Purpose: Monitor input fields and detect send actions.

**Key Design Decisions**:

1. **Polling vs Event-Based**: 
   - Polling (0.5-1s interval) is simpler and reliable
   - Event-based requires system hooks
   - Current implementation uses polling

2. **Thread Handling**:
   - Run monitoring in background daemon thread
   - Non-blocking, doesn't interfere with Slack

3. **Channel Type Detection**:
   - Extract channel ID from Slack UI
   - Classify as 'dm', 'channel', or 'group'
   - Use for context-aware prompts

### 3. Rewriting Engine

**File**: `core/rewriter.py`

Purpose: Generate professional rewrites of input text.

**Key Components**:

1. **Prompt Construction**:
   - Include channel type for context
   - DM vs channel prompts differ significantly
   - No thread context (unlike Slack bot)

2. **Quality Control**:
   - Fast heuristics (no embeddings for speed)
   - Length ratio check
   - Change detection
   - Professionalism scoring

3. **Post-Processing**:
   - Remove LLM metadata
   - Strip explanation text
   - Clean up formatting artifacts

### 4. Desktop Hook (Text Injection)

**File**: `integrations/desktop_hook.py`

Purpose: Replace text in Slack input field with rewritten version.

**Windows**:
```python
import pyautogui
import UIAutomation as uia

def inject_text(text):
    # Focus input field
    input_field.Focus()
    
    # Clear existing text
    pyautogui.hotkey('ctrl', 'a')
    pyautogui.press('delete')
    
    # Type new text
    pyautogui.write(text, interval=0.01)
```

**macOS**:
```python
import pyautogui

pyautogui.hotkey('command', 'a')  # Select all
pyautogui.press('delete')
pyautogui.write(text, interval=0.01)
```

**Important**: This requires Accessibility permissions on macOS.

### 5. Preview System

**File**: `core/preview.py`

Purpose: Show preview before applying rewrite.

**Decision Logic**:
1. If `auto_rewrite=False`: Always show preview
2. If `quality_score >= 0.85`: Auto-apply (high confidence)
3. If `quality_score < 0.85`: Show preview window
4. User can Accept (ENTER) or Cancel (ESC)

**Implementation**: Simple Tkinter window (cross-platform)

### 6. Configuration System

**File**: `config/__init__.py`

**Hierarchy**:
1. Environment variables (highest priority)
2. YAML config file
3. Command-line arguments
4. Default values

**Environment Variables**:
```bash
LLM_API_KEY=your-key
LLM_ENDPOINT=https://api.openai.com/...
CLIENT_AUTO_REWRITE=true
CLIENT_PREVIEW_ENABLED=true
CLIENT_KEYBOARD_SHORTCUT=Ctrl+Shift+R
```

## Technical Challenges & Solutions

### Challenge 1: Platform-Specific Detection

**Problem**: Each OS has different APIs for UI automation

**Solution**: Abstract interface with platform-specific implementations

```python
class PlatformDetector(ABC):
    @abstractmethod
    def get_input_field(self):
        pass

class WindowsDetector(PlatformDetector):
    def get_input_field(self):
        # Uses UIAutomation COM
        pass

class macOSDetector(PlatformDetector):
    def get_input_field(self):
        # Uses Accessibility API
        pass
```

### Challenge 2: Accessibility Permissions (macOS)

**Problem**: macOS requires explicit permission for UI monitoring

**Solution**: 
1. Detect missing permission
2. Show helpful dialog with instructions
3. Check permissions on startup

```python
def check_accessibility_permission():
    from AppKit import NSWorkspace
    import subprocess
    
    result = subprocess.run(
        ["tccutil", "status", "Accessibility"],
        capture_output=True
    )
    return "Slack" in result.stdout.decode()
```

### Challenge 3: Text Injection Timing

**Problem**: Injecting text at wrong time causes issues

**Solution**:
1. Detect send key press (Ctrl+Enter)
2. Intercept BEFORE actual send
3. Replace text
4. Allow normal send to proceed

### Challenge 4: Performance

**Problem**: Rewriting should be fast (<2 seconds)

**Solution**:
1. Lightweight quality checks (no embeddings)
2. Async LLM calls
3. Background processing
4. Timeout handling

### Challenge 5: False Positives

**Problem**: Rewriting messages you don't want changed

**Solution**:
1. High quality threshold for auto-apply (0.85)
2. Preview for uncertain rewrites
3. Easy override (ESC to cancel)
4. Quality score logging

## Testing Strategy

### Unit Tests
```python
# Test rewriter logic
def test_rewrite_professionalism():
    result = rewriter.rewrite("hey guys lol", "dm")
    assert result.quality_score > 0.5
    assert "lol" not in result.rewritten_text

# Test preview logic
def test_preview_threshold():
    preview = MessagePreview()
    assert not preview.should_show_preview(0.9)
    assert preview.should_show_preview(0.7)
```

### Integration Tests
```python
# Test with real LLM (requires API key)
def test_llm_connection():
    backend = OpenAIBackend()
    result = backend.generate("test", config)
    assert result.error is None
```

### Manual Tests
1. Start bot, type in Slack, verify rewrite
2. Test different channel types (DM, channel, group)
3. Verify keyboard shortcuts work
4. Test preview window appearance/disappearance

## Deployment Checklist

- [ ] Install Python 3.8+
- [ ] Create virtual environment
- [ ] Install all dependencies
- [ ] Configure LLM API key
- [ ] Grant accessibility permissions (macOS)
- [ ] Test with one channel first
- [ ] Enable auto-rewrite after verification
- [ ] Set up logging for monitoring
- [ ] Create backup of original config

## Alternative Approaches

### Option A: Browser Extension
**Pros**: Easier to implement (DOM manipulation)  
**Cons**: Only works for Slack web version  
**Best for**: Users who prefer web Slack

### Option B: Clipboard Interceptor
**Pros**: Simpler implementation  
**Cons**: Requires manual copy/paste trigger  
**Best for**: Non-real-time rewriting

### Option C: Accessibility API
**Pros**: Works across all platforms  
**Cons**: Slower, higher resource usage  
**Best for**: Fallback when native hooks unavailable

## Security Considerations

1. **API Key Storage**: Use environment variables or encrypted config
2. **Message Privacy**: All messages sent to your LLM provider
3. **System Access**: May require elevated permissions
4. **Data Transmission**: Over HTTPS only
5. **Local Logging**: Don't log sensitive messages in production

## Future Enhancements

- [ ] Smart context (learn your style)
- [ ] Template-based rewrites
- [ ] Multilingual support
- [ ] Integration with Slack API for better context
- [ ] Analytics dashboard
- [ ] Mobile app version
- [ ] Customizable prompts
- [ ] Batch processing for old messages

## Troubleshooting

**"Slack not detected"**: Run as Administrator (Windows) or enable Accessibility (macOS)

**"Text not being replaced"**: Check hook permissions, verify pyautogui is installed

**"Rewrite too conservative"**: Lower quality threshold in config

**"Slow rewriting"**: Check LLM response time, consider smaller model

## References

- Slack Platform: https://api.slack.com/
- Slack Bolt SDK: https://slack.dev/bolt-python/
- UI Automation (Windows): https://github.com/yossiyas/UIAutomation
- Accessibility API (macOS): https://developer.apple.com/documentation/accessibility
- pyautogui: https://pyautogui.readthedocs.io/
