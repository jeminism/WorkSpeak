# WorkSpeak Client - Connection Architecture Clarification

## CRITICAL CLARIFICATION

The client-side agent **DOES NOT CONNECT TO SLACK'S API**. Instead, it operates as a **local monitoring tool** on your computer.

## Three Connection Types

```
┌────────────────────────────────────────────────────────────────┐
│                     CONNECTION TYPES                           │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  1. Slack Desktop App Connection                              │
│     ─────────────────────────────                            │
│     Type:   OS-level hooks (UI Automation, Accessibility)     │
│     Purpose: Read/write text in Slack's input field           │
│     Uses:   pyautogui, UIAutomation, Accessibility API        │
│     Works:  Windows, macOS, Linux, Chrome OS                  │
│     Requires: System permissions/Accessibility access         │
│                                                                 │
│  2. LLM API Connection                                        │
│     ───────────────────────                                   │
│     Type:   Remote HTTP API call                              │
│     Purpose: Send text for rewriting, receive rewrite         │
│     Uses:   requests library                                    │
│     Config: LLM API endpoint + key (same as Slack bot)        │
│     Example: https://api.openai.com/v1/chat/completions       │
│                                                                 │
│  3. Your Computer (Local Session)                             │
│     ─────────────────────────                                 │
│     Type:   Local process                                       │
│     Purpose: Runs alongside Slack, monitors your typing       │
│     Uses:   Python, system events, file system                │
│     Runs:  Your desktop machine only                          │
│                                                                 │
│  NO CONNECTION 4: Slack API                                    │
│  ───────────────────────────────────────────────────────────  │
│  The client agent NEVER calls Slack's REST or Events API      │
│  It has NO Slack Bot Token or App Token                       │
│  It does NOT use Socket Mode or Webhooks                      │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

---

## Connection 1: Slack Desktop App

### How It Works

The agent monitors your **local Slack desktop application** using operating system accessibility hooks:

### Windows Implementation
```python
# Uses UIAutomation (COM-based Windows API)
import UIAutomation as uia

def get_slack_input_text():
    # Find the "Type a message" Edit control in Slack window
    edit = uia.EditControl(AutoName="Type a message")
    text = edit.GetValueControl().Value
    return text

def set_slack_input_text(text):
    edit = uia.EditControl(AutoName="Type a message")
    edit.Focus()
    pyautogui.hotkey('ctrl', 'a')  # Select all
    pyautogui.press('delete')       # Clear
    pyautogui.write(text)           # Insert new text
```

### macOS Implementation
```python
# Uses Accessibility API (requires system permission)
import quartz
from AppKit import AXUIElement

def get_slack_input_text():
    # Query AXUIElement hierarchy of Slack app
    # Find the NSTableCellView with edit field
    pass

def set_slack_input_text(text):
    # Use AXUIElement to set text value
    pass
```

### Linux Implementation
```python
# Uses X11/Wayland + python-xlib
from Xlib import X, display

def get_slack_input_text():
    # Query X11 window hierarchy
    # Find Slack's message input field
    pass

def set_slack_input_text(text):
    # Use XSendEvent or xdotool to send key events
    pass
```

### What This Connection Allows

| Action | Possible via OS Hooks |
|--------|----------------------|
| Read input field text | ✅ Yes |
| Write text to field | ✅ Yes (as keystrokes) |
| Detect when Slack starts | ✅ Yes |
| Detect which channel active | ⚠️ Limited (UI parsing only) |
| Send messages | ❌ No (uses pyautogui, not Slack API) |
| Read messages sent | ❌ No (only your input field) |

---

## Connection 2: LLM API

### How This Works

This is a **separate HTTP connection** to your LLM provider (OpenAI, Anthropic, etc.):

```python
import requests

def rewrite_text(text, channel_type):
    prompt = build_rewrite_prompt(text, channel_type)
    
    response = requests.post(
        config.llm.endpoint,
        headers={"Authorization": f"Bearer {config.llm.api_key}"},
        json={
            "model": config.llm.model,
            "messages": [{"role": "user", "content": prompt}]
        },
        timeout=config.llm.timeout
    )
    
    return response.json()['choices'][0]['message']['content']
```

### This Connection Allows

| Action | Possible | Notes |
|--------|----------|-------|
| Send text for rewriting | ✅ Yes | Always via HTTPS |
| Receive rewritten text | ✅ Yes | Always via HTTPS |
| Access thread context | ❌ No | Only has your input text |
| Know channel details | ⚠️ Limited | From UI parsing only |

---

## Connection Flow: Complete Message Cycle

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         MESSAGE CYCLE                                   │
└─────────────────────────────────────────────────────────────────────────┘

STEP 1: You type in Slack desktop app
─────────────────────────────────────
Your typing → Slack Desktop App → Input field updated

STEP 2: Client monitors local Slack window
────────────────────────────────────────────
OS hooks poll Slack window → Detect text change → MessageState created

STEP 3: Client calls LLM API
─────────────────────────────────────────────
WorkSpeak Client → HTTPS POST → LLM Provider API

STEP 4: LLM returns rewrite
─────────────────────────────────────────────
LLM Provider → HTTPS Response → Client receives rewritten text

STEP 5: Client replaces text in Slack
─────────────────────────────────────────
WorkSpeak Client → pyautogui → Slack Input field overwritten

STEP 6: You send the rewritten message
────────────────────────────────────────────
YOU press Ctrl+Enter → Slack sends message (via Slack's normal path)

NOTE: The workSpeak client NEVER sends the message itself!
You initiate the send, not the agent.
```

---

## Permission Requirements

### Why Permissions Are Needed

```
Windows: No special permissions (works as regular user)
          - May need to run as Administrator for some apps
          
macOS: Strict Accessibility permission required
          - Settings → Privacy → Accessibility → Add Python/Terminal
          - macOS won't let apps control other apps without this
          
Linux: Varies by distribution
          - Usually requires X11 access
          - Some desktop environments restrict this
```

### How Permissions Work

```
OS Security Model:
┌─────────────────────────────────────┐
│ App A (Slack)    │ App B (WorkSpeak)│
│                  │                  │
│ ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄│┄┄┄┄┄┄┄┄┄┄┄┄┄┄ |
│                 │                  │
│  [App A] ┄─❌───┸─── [App B]       │
│                 │                  │
│  CAN'T read/write without     │
│    user permission          │
└─────────────────────────────────────┘

macOS asks:
"Do you want WorkSpeak to control Slack?"
If YES → WorkSpeak can read Slack input field and replace text
If NO → WorkSpeak has zero access to Slack
```

---

## What the Client CANNOT Do

Because it doesn't have Slack API access, the client:

| Action | Possible? | Reason |
|--------|-----------|--------|
| Read messages from other users | ❌ No | Only your input field visible |
| See messages sent by you | ❌ No | Doesn't see output from Slack |
| Access thread history | ❌ No | Not via Slack API |
| Respond to other users | ❌ No | Only rewrites YOUR input |
| Work on mobile Slack | ❌ No | Only desktop app |
| Work across all your devices | ❌ No | Runs on one computer only |
| Know if message is "private" | ❌ No | Can't read Slack UI deeply |

---

## What the Client CAN Do

| Action | Possible? | Why |
|--------|-----------|-----|
| See what you're typing | ✅ Yes | Monitors local input field |
| Rewrite before you send | ✅ Yes | Replaces text in input |
| Work in 1:1 DMs | ✅ Yes | Not subject to privacy model |
| Work in any channel | ✅ Yes | No channel restrictions |
| Show preview before apply | ✅ Yes | Local UI component |
| Remember your preferences | ✅ Yes | Local config file |

---

## Slack Bot vs Client: Connection Comparison

```
┌──────────────────────────────────────────────────────────────────┐
│                    CONNECTION COMPARISON                         │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│                     SLACK BOT                                    │
│                     ────────────                                 │
│                                                                  │
│   ┌──────────────┐     ┌──────────────────┐                    │
│   │  Your Slack  │────▶│  Slack Platform  │                    │
│   │              │     │                  │                    │
│   └──────────────┘     │  API/Socket Mode │                    │
│               │        │                  │                    │
│               │        │  EVENT SENT TO   │                    │
│               │        │  (if bot is in   │                    │
│               │        │   the channel)   │                    │
│               │        └────────┬─────────┘                    │
│               │                 │                              │
│               │                 ▼                              │
│               │         ┌──────────────┐                       │
│               │         │   Slack Bot  │                       │
│               │         │   (Remote)   │                       │
│               │         └──────┬───────┘                       │
│               │                │                               │
│               │                │  chat_update()                │
│               │                ▼                               │
│   ┌──────────────┐     ┌──────────────────┐                   │
│   │  Your Slack  │◀────│   Slack Platform │                   │
│   │  (edited)    │     │                  │                   │
│   └──────────────┘     └──────────────────┘                   │
│                                                                  │
│   Requires: Slack App Token, Bot Token, channel membership       │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                   CLIENT-SIDE AGENT                              │
│                                                                  │
│   ┌──────────────┐                                              │
│   │  Your Slack  │                                              │
│   │  Desktop App │                                              │
│   │              │                                              │
│   │  [Input field│────────────────────────                       │
│   │   you typing]│                                               │
│   └──────────────┘           │                                  │
│                              │ OS Hooks (UI Automation)          │
│              ▼               │                                  │
│      ┌──────────────┐        │                                  │
│      │ WorkSpeak    │◀───────┘                                  │
│      │ Client       │          │                                
│      │ (Local)      │          │                                
│      └──────┬───────┘          │                                
│             │                  │                                
│             │                  ▼                                
│             │         ┌──────────────┐                          
│             │         │   LLM API    │                          
│             │         │   (Remote)   │                          
│             │         └──────┬───────┘                          
│             │                │                                  
│             │                ▼                                  
│             │      ╔═══════════════════════════╗                
│             │      ║  Rewritten text returned ║                
│             │      ╚══════════════╦═══════════╝                
│             │                     │                             
┌─────────────┼─────────────────────┴─────────────────────────┐   
│  ┌──────────▼──────────────────────────────────────────┐   │
│  │    pyautogui / OS Hooks                             │   │
│  │    Replace text in Slack input field                │   │
│  └─────────────────────────┬────────────────────────────┘   │
│                            │                                  │
│                            ▼                                  │
│   ┌──────────────┐                                           │
│   │  Your Slack  │                                            │
│   │  Desktop App │                                            │
│   │              │                                            │
│   │  [Input field│──▶ You press send (your action!)           │
│   │  now typed]  │                                            │
│   │              │                                            │
│   │  ▼                                           │
│   │  ┌──────────────┐                             │
│   │  │  Slack sends │◀──────  You send it, not bot │
│   │  │  message     │                               │
│   │  └──────────────┘                               │
│   └──────────────────────────────────────────────────┘
│                                                              │
│   Requires: OS permissions, nothing else                     │
│   Does NOT require: Slack tokens, API access               │
│                                                              │
└────────────────────────────────────────────────────────────────┘
```

---

## Summary: The No-Secret Sauce

The client-side solution works **WITHOUT** needing any special access to Slack because:

1. **It observes your application** - Like any screen-scraping tool
2. **It modifies YOUR local input** - As long as YOU have a cursor there
3. **It calls external LLM** - Via regular HTTPS, not Slack API
4. **It relies on YOU to send** - It just pre-fills your input field

There's no magical "Slack connection." There's just local monitoring of what you're typing, remote rewriting via LLM, and text replacement in your local input field.

---

## Security Note

Because there's no Slack API connection:
- ✅ No Slack tokens stored
- ✅ No third-party apps can monitor you (only your local agent)
- ⚠️ Your text IS sent to your LLM provider
- ⚠️ Requires system-level permissions (trust required)

This is fundamentally different from the Slack bot model where a third-party service has permission to read/write messages on your behalf.
