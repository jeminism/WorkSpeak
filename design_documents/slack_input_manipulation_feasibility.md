# Slack Input Manipulation - Technical Feasibility Analysis

**Date:** April 22, 2026  
**Status:** Detailed evaluation of programmatic input access approaches

---

## Executive Summary

**Your instinct is correct:** Programmatic reading/writing of Slack's input box is **feasible** but requires **special setup**.

The most viable approach: **Chrome DevTools Protocol (CDP) with manual Slack configuration**

---

## All Approaches Ranked by Feasibility

### 1. Chrome DevTools Protocol (CDP) - HIGHEST FEASIBILITY ✅

**How it works:**
- Slack Electron app uses Chromium-based WebView
- Chrome DevTools Protocol allows external clients to introspect/modify browser content
- Standard port: 9222 (or 9229 for interactive)

**Requirements:**
```bash
# User must run Slack with debug port enabled
slack --inspect=9229 --remote-debugging-port=9229
```

**Capabilities:**
- ✅ Read input field content in real-time
- ✅ Replace input text programmatically
- ✅ Access channel ID, user ID from internal state
- ✅ Monitor DOM changes (when message sent, channel switched)

**Setup (user-guided):**

macOS (create wrapper script):
```bash
#!/bin/bash
/Applications/Slack.app/Contents/MacOS/Slack --inspect=9229 --remote-debugging-port=9229 "$@"
# Save as ~/bin/slack-cdp and make executable: chmod +x ~/bin/slack-cdp
```

Windows (PowerShell):
```powershell
Start-Process "C:\Users\...\slack.exe" -ArgumentList "--inspect=9229", "--remote-debugging-port=9229"
```

Linux:
```bash
slack-desktop --inspect=9229 --remote-debugging-port=9229
# Add to /usr/bin/slack or create wrapper in PATH
```

**WorkSpeak Overlay Implementation:**
```python
# Python using ChromeDevToolsProtocol
from devtools import DevToolsConnection

cdp = DevToolsConnection(host='localhost', port=9229)
cdp.start_session()

# Monitor input field
input_field = cdp.get_element('#message-input')  # hypothetical selector

def on_input_changed(text):
    rewritten = rewrite_api(text)
    show_overlay_popup(rewritten)

# Access current channel
channel_context = cdp.evaluate("window.Store.Actions.channel.get()")
```

**Tradeoffs:**
- ✅ Real-time, no latency
- ✅ Has full Slack context (channel, user)
- ✅ No special OS permissions
- ❌ Requires manual config (user must modify Slack startup)
- ❌ Slack auto-updates may overwrite wrapper script
- ❌ Only works on Linux desktop app, not web version

---

### 2. Accessibility API (macOS/Windows only) - MEDIUM FEASIBILITY ⚠️

**How it works:**
- Operating system provides accessibility tree for foreground app
- macOS: AppleScript + Accessibility Framework
- Windows: UI Automation / MSAA

**Capabilities:**
- ✅ Read text from input fields (sometimes read-only)
- ✅ Get window hierarchy
- ❌ Limited write capability (depends on control type)
- ❌ Channel info not exposed

**macOS Example (AppleScript):**
```bash
set inputText to text of first field of window 1 of application process "Slack"
```

**Windows Example (PowerShell):**
```powershell
$window = Get-UIAutomationTargetWindow -Name "Slack"
$inputField = $window.FindFirst("Name", "Message Input")
$inputField.InvokePattern.Select()
$inputField.Current.Value  # Read text
```

**Tradeoffs:**
- ✅ No Slack modification needed
- ✅ Works with default Slack installation
- ⚠️ Read-only on many controls (cannot write)
- ⚠️ macOS requires Accessibility permission (System Settings)
- ⚠️ Windows has limited write support
- ❌ No channel context

---

### 3. Keyboard Event Interception (Linux X11 only) - LOW-MEDIUM FEASIBILITY ⚠️

**How it works:**
- Hook into X11 event loop
- Monitor for Enter key in Slack window
- Capture, rewrite, resend

**Capabilities:**
- ✅ Can intercept before message is sent
- ✅ Can replace text
- ❌ Only works on X11 (not Wayland)
- ❌ Requires keyboard grab permissions
- ❌ Complex, fragile, may break

**Python Example (python-xlib):**
```python
from Xlib import X, display

d = display.Display()
slack_window = find_slack_window()
d.grab_keyboard(slack_window, True, X.GrabModeAsync, X.GrabModeAsync, CurrentTime)

# Wait for Enter key in Slack window
event = d.next_event()
if event.response_type == X.KeyPress and event.detail == 36:  # Enter
    current_text = get_slack_input_text()
    rewritten = rewrite_api(current_text)
    # Simulate backspace + new text + Enter
```

**Tradeoffs:**
- ✅ No Slack modification needed
- ❌ Linux/X11 only (not Wayland, not Windows, not macOS)
- ❌ May break when Slack updates input field ID
- ❌ Requires elevated permissions
- ❌ Doesn't provide channel context

---

### 4. Clipboard-Based (Universal) - LOW FEASIBILITY ❌

**How it works:**
- Monitor clipboard when user copies in Slack
- Rewrite and paste back
- User confirms

**Tradeoffs:**
- ❌ Two-step workflow (copy → paste)
- ❌ User visible (clipboard flash)
- ❌ No channel context
- ❌ Not real-time

---

### 5. Screen Scraper + OCR - LOW FEASIBILITY ❌

**How it works:**
- Periodically screenshot input area
- OCR the text
- Display rewrite

**Tradeoffs:**
- ❌ 200-500ms latency
- ❌ Error-prone (OCR accuracy)
- ❌ User visible flash
- ❌ Heavy CPU usage
- ❌ No channel context

---

## Recommended Architecture: CDP-Based Overlay

```
┌─────────────────────────────────────────────────────────────────┐
│              WorkSpeak CDP Overlay v2.0                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Slack Desktop (with --inspect=9229)                           │
│  ┌─────────────────────────────────────────────┐               │
│  │  Electron Process                          │               │
│  │  ┌─────────────────────────────────────┐   │               │
│  │  │  WebView (BrowserView)              │   │               │
│  │  │  ┌───────────────────────────────┐  │   │               │
│  │  │  │ #message-input field          │  │   │               │
│  │  │  │ "Hello world"                 │  │   │               │
│  │  │  └───────────────────────────────┘  │   │               │
│  │  │                                      │   │               │
│  │  │  Channel Context: Redux State        │   │               │
│  │  │  - activeChannelId: "C012345678"     │   │               │
│  │  │  - channelName: "#general"           │   │               │
│  │  └─────────────────────────────────────┘   │               │
│  └─────────────────────────────────────────────┘               │
│         ↓                                                     │
│  Chrome DevTools Protocol (CDP) - Port 9229                   │
│         ↓                                                     │
│  ┌─────────────────────────────────────────────┐               │
│  │  WorkSpeak Overlay                          │               │
│  │  ┌───────────────────────────────────────┐  │               │
│  │  │  Input Monitor: Listen for text change│  │               │
│  │  │  Rewrite API: Fast LLM call           │  │               │
│  │  │  Popup: Show rewritten text           │  │               │
│  │  │  [Undo] [Accept] [Reject] buttons     │  │               │
│  │  └───────────────────────────────────────┘  │               │
│  └─────────────────────────────────────────────┘               │
│         ↓                                                     │
│  WorkSpeak API (same backend as bot)                          │
│         ↓                                                     │
│  LLM Rewrite → Quality Check → Return Text                    │
└─────────────────────────────────────────────────────────────────┘

User Action Flow:
1. User types in Slack input
2. CDP detects text change → sends to overlay
3. Overlay calls rewrite API (200-500ms)
4. Overlay shows popup: "Your text → Rewritten text"
5. User clicks "Accept" → Overlay sends new text back to Slack
6. Message sent to channel (no "edited" badge, user never saw original)
```

---

## Implementation Steps

### Phase 1: Basic CDP Connection (3-4 hours)

1. Create wrapper script for Slack startup
2. Implement CDP client in Python
3. Connect to Slack debug port
4. Query input field selector
5. Monitor for text changes

**Dependencies:**
```python
# pip install chrome-devtools-protocol websocket-client
from devtools import ChromeDevTools
cdp = ChromeDevTools(host='localhost', port=9229)
```

### Phase 2: Input Monitoring & Rewrite (4-6 hours)

1. Add DOM observer for input field content
2. Call rewrite API on change
3. Show overlay popup
4. Handle accept/reject buttons

### Phase 3: Text Replacement (2-3 hours)

1. Send new text to input field via CDP
2. Trigger message send on Enter key
3. Handle edge cases (paste, autocomplete, formatting)

### Phase 4: Channel Context Integration (2-3 hours)

1. Access Slack Redux store via CDP
2. Extract channel ID, channel name
3. Provide context to rewrite API
4. Log channel-specific metrics

---

## Tradeoffs Summary

| Approach | Channel Context | Latency | Permissions | Complexity | Feasibility |
|----------|-----------------|---------|-------------|------------|-------------|
| **CDP (Recommended)** | ✅ Full | ✅ <1s | ⚠️ Manual config | ⚠️ Medium | ✅ High |
| Accessibility API | ❌ No | ⚠️ 200ms | ⚠️ OS permission | ⚠️ Medium | ⚠️ Medium |
| Keyboard Interception | ❌ No | ✅ <10ms | ⚠️ Elevated | ❌ High | ⚠️ Low |
| Clipboard | ❌ No | ❌ 500ms+ | ✅ None | ✅ Low | ❌ Low |
| Screen Scraper | ❌ No | ❌ 500ms+ | ✅ None | ✅ Low | ❌ Low |

---

## Migration Path

### If CDP Setup Works (Recommended):
- ✅ Full real-time rewrite with context
- ✅ Can add features: channel-specific settings, history, etc.
- ✅ Feels like native Slack integration

### If CDP Setup Fails or User Doesn't Want Config:
- Fall back to: Slack Bot improvements (undo + async)
- No feature loss, just different UX

---

## Conclusion

**Your idea is feasible** with the CDP approach, but requires:
1. User to configure Slack with debug flag (one-time)
2. Wrapper script to persist across updates
3. Python implementation of CDP client

**Best path forward:**
1. **Try Phase 1 (CDP connection)** - simple proof of concept
2. If successful, proceed to overlay implementation
3. If not, fall back to Slack Bot improvements

**Time estimate:** 10-15 hours total for working CDP overlay
**Complexity:** Medium (more than bot improvements, but feasible)

---

*Document created: April 22, 2026*  
*For technical reference and implementation planning*
