# WorkSpeak Multi-Platform Architecture Design

**Date:** April 22, 2026  
**Version:** 2.0  
**Status:** Design Document

---

## Executive Summary

WorkSpeak will provide **two complementary interfaces** to the same rewriting engine:

1. **CDP Overlay** - Seamless real-time typing experience on Linux desktop
2. **Slack Bot** - Multi-device, team-wide functionality across all platforms

Both share the **identical** rewriter and backend layers for consistency.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           WorkSpeak Core Libraries                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    rewriter.py                                      │   │
│  │  ─────────────────────────────────────────────────────────────────  │   │
│  │  - MessageRewriter (class)                                        │   │
│  │  - Quality control (semantic, conciseness, tone)                  │   │
│  │  - Post-processing (metadata removal, artifact cleanup)           │   │
│  │  - rewrite(text, thread_context, config) → (final_text, decision) │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    llm_backend.py                                   │   │
│  │  ─────────────────────────────────────────────────────────────────  │   │
│  │  - LLMBackend (ABC)                                               │   │
│  │  - OpenAIBackend (class)                                          │   │
│  │  - generate(prompt, config) → LLMCallResult                       │   │
│  │  - Thread-safe, retry logic, timeout handling                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    config.py                                        │   │
│  │  ─────────────────────────────────────────────────────────────────  │   │
│  │  - LLMConfig (dataclass)                                          │   │
│  │  - load_llm_config() → unified config for both implementations      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    logging_config.py                                │   │
│  │  ─────────────────────────────────────────────────────────────────  │   │
│  │  - Unified logging setup for both components                        │   │
│  │  - Same log format, same handlers                                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                   │
                                   │ Shared Core
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     Platform-Specific Adaptation Layer                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    CDP Overlay (Linux Desktop)                      │   │
│  │  ─────────────────────────────────────────────────────────────────  │   │
│  │  - devtools_client.py     (Chrome DevTools Protocol client)          │   │
│  │  - input_monitor.py       (DOM change observer for Slack input)      │   │
│  │  - overlay_ui.py          (Popup overlay widget)                     │   │
│  │  - channel_context.py     (Slack Redux state access via CDP)         │   │
│  │  - worker.py              (Background worker for rewrite tasks)      │   │
│  │                                                             │      │
│  │  Purpose: Real-time rewrite preview + inline replacement           │   │
│  │  Use Case: Linux desktop user with Slack app                     │   │
│  │  Setup: Wrapper script (slack --inspect=9229)                    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    Slack Bot (Multi-Platform)                       │   │
│  │  ─────────────────────────────────────────────────────────────────  │   │
│  │  - app.py               (Bolt event handlers, channel context)       │   │
│  │  - batch_evaluator.py   (Evaluation pipeline, already exists)        │   │
│  │  - cli_rewriter.py      (CLI interface, already exists)              │   │
│  │  - __main__.py          (Bot launcher with Socket Mode)              │   │
│  │                                                             │      │
│  │  Purpose: Message rewriting, team collaboration, multi-device      │   │
│  │  Use Case: Team-wide deployment, cloud sync, all Slack clients   │   │
│  │  Setup: Slack App Token, App Manifest, OAuth installation          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Component Details

### Core Libraries (Shared)

| File | Purpose | Used By |
|------|---------|---------|
| `rewriter.py` | Message rewriting, quality control | Both |
| `llm_backend.py` | LLM API client (OpenAI-compatible) | Both |
| `config.py` | Config loading (env vars or YAML) | Both |
| `logging_config.py` | Logging setup | Both |
| `__init__.py` | Package exports | Both |

**Key Design Principle:** The core rewriting logic is **100% portable**. Only the input/output adapters differ.

---

### CDP Overlay (Linux Desktop)

#### Components

| Module | Responsibility |
|--------|----------------|
| `devtools_client.py` | Chrome DevTools Protocol connection, session management |
| `input_monitor.py` | DOM observers for Slack input field, change detection |
| `overlay_ui.py` | Tkinter/GTK popup overlay for showing rewrites |
| `channel_context.py` | Access Slack Redux state via CDP to get channel info |
| `worker.py` | Background rewrite worker, thread-safe API calls |
| `main.py` | Entry point, launcher, config validation |
| `wrapper.py` | Slack startup wrapper script generator |

#### Features

- Real-time rewrite preview (as-you-type)
- Inline text replacement without "edited" badge
- Popup overlay with Accept/Reject/Undo controls
- Channel-aware context (reads from Slack's internal state)
- No Slack App permissions required
- Local privacy (no external network calls for chat data)

#### Requirements

- Linux desktop (Electron-based Slack app)
- Slack started with `--inspect=9229` (user-configured)
- Python 3.11+ with devtools dependencies
- X11 display (default on Linux)

#### Setup Command

```bash
#!/bin/bash
# Create wrapper script
echo '#!/bin/bash
slack-desktop --inspect=9229 --remote-debugging-port=9229 "$@"' | sudo tee /usr/local/bin/slack-cdp

sudo chmod +x /usr/local/bin/slack-cdp

# Now launch Slack-cdp instead of slack
slack-cdp
```

---

### Slack Bot (Multi-Platform)

#### Components (Existing + New)

| Module | Responsibility | Status |
|--------|----------------|--------|
| `app.py` | Bolt event handlers, channel context | Existing |
| `rewriter.py` | Message rewriting | Existing |
| `llm_backend.py` | LLM API client | Existing |
| `config.py` | Config loading | Existing |
| `batch_evaluator.py` | Evaluation pipeline | Existing |
| `cli_rewriter.py` | CLI interface | Existing |
| `logging_config.py` | Logging setup | Existing |
| `__main__.py` | Bot launcher | Existing |
| **NEW: undo_handler.py** | "Undo" button handler | Planned |
| **NEW: async_rewrite.py** | Async rewrite tasks | Planned |
| **NEW: cache.py** | Rewrite result cache | Planned |

#### Features

- Message rewriting with quality control
- Thread-aware context (fetches from Slack API)
- Multi-device sync (cloud-based)
- Team-wide deployment
- Undo button (planned)
- Async processing (planned)
- Cache layer (planned)

#### Requirements

- Slack App Token
- Slack App Installation (OAuth)
- Bot permissions: channels:read, chat:write
- Slack App Manifest configuration

#### Setup Command

```bash
# Via Slack App Manifest
{
  "display_information": {
    "name": "WorkSpeak"
  },
  "features": {
    "bot_user": {
      "display_name": "WorkSpeak",
      "always_online": true
    }
  },
  "slack_token_features": {
    "bot_api": true
  },
  "events": {
    "bot": ["message.channels", "message.groups", "message.im", "message.mpim"],
    "appHomeOpened": [],
    "commands": ["/undo", "/pause", "/workspeaks-status"]
  }
}
```

---

## Feature Parity Table

| Feature | CDP Overlay | Slack Bot | Notes |
|---------|-------------|-----------|-------|
| **Real-time preview** | ✅ Yes | ❌ No | After-send edit |
| **As-you-type rewrite** | ✅ Yes | ❌ No | CDP DOM access |
| **Inline text replace** | ✅ Yes | ⚠️ Post-send | "edited" badge |
| **No "edited" badge** | ✅ Yes | ❌ No | Bot always shows |
| **Channel context** | ✅ From Redux | ✅ From API | Both have it |
| **Multi-device** | ❌ No | ✅ Yes | Bot wins |
| **Team deployment** | ❌ No | ✅ Yes | Bot wins |
| **Privacy (local data)** | ✅ Yes | ⚠️ Server | Depends |
| **Slack permissions** | ❌ None | ✅ OAuth | CDP wins |
| **Setup complexity** | ⚠️ Medium | ⚠️ Medium | Similar |
| **Platform support** | Linux only | All | Bot wins |

---

## Data Flow Comparison

### CDP Overlay Flow

```
User types in Slack
        ↓
CDP DOM Observer detects input change
        ↓
Overlay UI sends text to rewrite worker
        ↓
Worker calls rewriteAPI (shared library)
        ↓
LLM backend → API call
        ↓
Rewritten text returns
        ↓
Overlay displays popup: "Your text → Rewritten"
        ↓
User clicks [Accept] OR [Reject]
        ├─→ Accept: Text replaced in Slack input (no "edited" badge)
        └─→ Reject: Original text stays
        ↓
User presses Enter
        ↓
Message sent to Slack channel
```

### Slack Bot Flow

```
User sends message in Slack
        ↓
Slack Event → Bolt Handler
        ↓
Bot fetches message text + channel context
        ↓
Bot calls rewriteAPI (shared library)
        ↓
LLM backend → API call
        ↓
Rewritten text returns
        ↓
Quality check passes/fails
        ↓
Bot calls chat_update()
        ↓
Message edited (shows "edited" badge)
        ↓
Original message replaced with rewritten
        ↓
(Optional) Undo button added via attachment
```

---

## Shared Interface Contract

Both implementations must use the **same function signature** for rewriting:

```python
# rewriter.py - Unified Interface

class MessageRewriter:
    def rewrite(
        self,
        original_text: str,
        thread_context: str = "",
        max_iterations: int = 3,
        config: LLMConfig = None
    ) -> Tuple[str, str]:
        """
        Rewrite message with quality control.
        
        Args:
            original_text: The raw message text
            thread_context: Optional context from Slack replies
            max_iterations: Max LLM retry attempts
            config: LLMConfig from config.py
            
        Returns:
            (final_text, quality_decision)
            - final_text: The rewritten message
            - quality_decision: "accepted", "rejected", "keep", etc.
        """
```

Both overlay and bot import and call this **identical** function.

---

## Configuration Sharing

Both implementations use the same config file:

```yaml
# config/llm_config.yaml
endpoint: "https://api.example.com/v1/chat"
api_key: "sk-..."
model: "gpt-4o"
provider: "openai"  # or "huggingface", etc.
```

Env var override:
```bash
LLM_API_KEY=sk-... \
LLM_ENDPOINT=https://api.example.com \
python -m slack_message_bot  # Bot
python -m workspeaks_overlay  # Overlay
```

---

## Implementation Roadmap

### Phase 1: Code Share Setup (3-4 hours)

- [ ] Create `src/workspeak_core/` for shared libraries
- [ ] Move `rewriter.py`, `llm_backend.py`, `config.py` to core
- [ ] Create `src/workspeak_overlay/` for CDP code
- [ ] Create `src/workspeak_bot/` for Slack Bot wrappers
- [ ] Update imports to use shared core
- [ ] Verify both implementations produce identical outputs

### Phase 2: CDP Overlay Foundation (6-8 hours)

- [ ] Implement `devtools_client.py` (CDP connection)
- [ ] Implement `input_monitor.py` (DOM observers)
- [ ] Implement `worker.py` (background rewrite tasks)
- [ ] Create simple text-based overlay (command line output)
- [ ] Test flow: type → capture → rewrite → display
- [ ] Add Accept/Reject button simulation

### Phase 3: Slack Bot Enhancements (4-6 hours)

- [ ] Add async rewrite tasks to `app.py`
- [ ] Implement "Undo" button handler
- [ ] Add cache layer for common rewrites
- [ ] Add `/undo`, `/pause` slash commands
- [ ] Test flow: send → rewrite → edit → undo

### Phase 4: Integration & Polish (4-6 hours)

- [ ] Unified packaging (pip install workspeaks)
- [ ] Common CLI interface (`workspeak --help`)
- [ ] Unified logging format
- [ ] Documentation for both approaches
- [ ] Example config files
- [ ] Test suite covering both implementations

---

## Security Considerations

### CDP Overlay

- ✅ Uses localhost-only binding
- ✅ No network access to chat data
- ✅ Slack session cookies stay local
- ⚠️ Requires user to manually configure Slack startup
- ⚠️ Slack auto-updates may need reconfiguration

### Slack Bot

- ✅ Uses official Slack API (audited)
- ✅ OAuth scopes are limited/chosen by user
- ⚠️ Chat data transmitted to external server
- ⚠️ Requires trust in server security
- ✅ Can be self-hosted if needed

### Comparison

| Aspect | CDP Overlay | Slack Bot |
|--------|-------------|-----------|
| Data residency | Local only | Server |
| Permissions | None | OAuth |
| Attack surface | localhost:9229 | Public API |
| Privacy | User-controlled | Server trust |

---

## User Experience Comparison

### CDP Overlay User Flow

```
1. User installs WorkSpeak overlay
2. User creates wrapper script (1-time)
3. User launches Slack with `slack-cdp`
4. WorkSpeak overlay starts automatically
5. User types message in Slack
6. Overlay shows popup in 200-500ms: "Rewrite: ..."
7. User clicks [Accept] or [Reject]
8. User presses Enter
9. Message sent (no "edited" badge)
```

### Slack Bot User Flow

```
1. User installs Slack App
2. OAuth consent, app installed
3. User types message in Slack (any client)
4. Bot rewrites in background (2-5s latency)
5. Message is edited (shows "edited" badge)
6. User can click [Undo] button if needed
7. Message updated
```

---

## Package Structure

```
WorkSpeak/
├── core/                         # Shared libraries
│   ├── __init__.py
│   ├── rewriter.py              # MessageRewriter class
│   ├── llm_backend.py           # LLMBackend ABC + implementations
│   ├── config.py                # Config loading & LLMConfig
│   └── logging_config.py        # Logging setup
│
├── overlay/                      # CDP Overlay
│   ├── __init__.py
│   ├── devtools_client.py       # CDP connection
│   ├── input_monitor.py         # DOM observers
│   ├── overlay_ui.py            # Popup UI
│   ├── worker.py                # Background worker
│   ├── channel_context.py       # Slack Redux access
│   └── main.py                  # Entry point
│
├── bot/                          # Slack Bot
│   ├── __init__.py
│   ├── app.py                   # Bolt handlers
│   ├── undo_handler.py          # Undo button
│   ├── async_rewrite.py         # Async task queue
│   ├── cache.py                 # Rewrite cache
│   └── slash_commands.py        # /undo, /pause, etc.
│
├── config/
│   └── llm_config.yaml          # LLM configuration
│
├── scripts/
│   ├── setup-overlay.sh         # Overlay installation
│   ├── wrapper-slack.sh         # Slack wrapper generator
│   └── setup-bot.sh             # Bot installation guide
│
├── tests/
│   ├── test_core/               # Core library tests
│   │   ├── test_rewriter.py
│   │   └── test_llm_backend.py
│   └── integration/             # Integration tests
│
├── requirements.txt
├── setup.py                     # Multi-package setup
├── pyproject.toml
└── README.md
```

---

## Decision Rationale

### Why Two Implementations?

1. **Different User Needs:**
   - Power users want "as-you-type" (CDP)
   - Teams want collaboration (Bot)
   - Multi-device users need cloud sync (Bot)
   - Privacy-focused users prefer local (CDP)

2. **No Technical Conflict:**
   - Same rewriting core
   - Different input/output adapters
   - Can evolve independently

3. **Competitive Advantage:**
   - Only solution offering both approaches
   - Flexibility for different use cases
   - Better market positioning

---

## Risk Mitigation

### CDP Overlay Risks

| Risk | Mitigation |
|------|------------|
| Slack updates break CDP access | Document wrapper script, provide update tool |
| User misconfigures debug port | Validation in overlay startup |
| Security concerns from CDP | Detailed security docs, verification tools |
| Linux-only limitation | Don't promise, be clear about platform support |

### Slack Bot Risks

| Risk | Mitigation |
|------|------------|
| Slack API rate limits | Implement retry + caching |
| OAuth permission friction | Clear docs, minimal scopes |
| Latency perception | Async + loading indicators |
| Server cost | Option to self-host |

---

## Success Metrics

### CDP Overlay

- [ ] Real-time rewrite preview < 500ms latency
- [ ] 95% success rate on text replacement
- [ ] < 10% user rejection rate of rewrites
- [ ] Zero security incidents

### Slack Bot

- [ ] Multi-device message sync
- [ ] < 5 second total rewrite latency
- [ ] > 50% undo/confirm button usage
- [ ] Team-wide adoption rate

---

## Conclusion

**Two approaches serve different user segments but share the same core.**

- **CDP Overlay** = Premium desktop experience (Linux)
- **Slack Bot** = Team collaboration (all platforms)

Both can coexist, evolve independently, and share the rewriting core. This maximizes market fit while minimizing redundancy.

---

*Document created: April 22, 2026*  
*Version 2.0 - Multi-platform architecture finalized*
