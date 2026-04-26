# WorkSpeak CDP Overlay

Chrome DevTools Protocol (CDP) based Slack message rewriter for Linux desktop.

## Overview

The CDP Overlay provides **real-time, in-place message rewriting** for Slack on Linux. Unlike the Slack Bot which edits messages after they're sent (showing an "edited" badge), the CDP Overlay:

- ✅ **No "edited" badge** - User never sees the original text
- ✅ **Real-time preview** - As-you-type rewrite suggestions
- ✅ **Seamless integration** - Feels like native Slack functionality
- ✅ **No Slack permissions** - Uses CDP to access DOM directly

### Requirements

- **Linux desktop** (Electron-based Slack app)
- Python 3.11+
- Chrome DevTools Protocol (CDP) enabled on Slack

### Trade-offs

| Feature | CDP Overlay | Slack Bot |
|---------|-------------|-----------|
| Real-time preview | ✅ Yes | ❌ No |
| No "edited" badge | ✅ Yes | ❌ No |
| Multi-platform | ❌ Linux only | ✅ All platforms |
| Team deployment | ❌ No | ✅ Yes |
| Setup complexity | ⚠️ Manual config | ⚠️ OAuth |

---

## Installation

### Step 1: Install Dependencies

```bash
# Install overlay-specific dependencies
pip install -r requirements-overlay.txt

# Activate virtual environment
source .venv/bin/activate
```

### Step 2: Configure LLM Backend

Edit `config/llm_config.yaml` or set environment variables:

```bash
export LLM_ENDPOINT=https://api.openai.com/v1/chat/completions
export LLM_API_KEY=sk-your-api-key-here
export LLM_MODEL=gpt-4o-mini
```

### Step 3: Generate Slack Wrapper Script

```bash
python -m overlay.main --wrapper
```

This creates `~/bin/slack-cdp` (or `~/bin/slack-cdp` on macOS) which launches Slack with CDP enabled.

**Alternative manual command:**
```bash
#!/bin/bash
/usr/bin/slack --inspect=9229 --remote-debugging-port=9229 "$@"
```

Save as `~/bin/slack-cdp`, make executable:
```bash
chmod +x ~/bin/slack-cdp
```

---

## Usage

### 1. Launch Slack with CDP

**Using wrapper script (recommended):**
```bash
slack-cdp
```

**Or manually:**
```bash
slack --inspect=9229 --remote-debugging-port=9229
```

**Verify CDP is running:**
```bash
ss -tlnp | grep 9229
# Should show: 127.0.0.1:9229
```

### 2. Start the Overlay

In a new terminal:
```bash
cd /proj/WorkSpeak
source .venv/bin/activate

python -m overlay.main
```

### 3. Follow On-Screen Instructions

The overlay will:
1. Connect to Slack CDP endpoint
2. Detect Slack's input field
3. Start monitoring for text changes

### 4. Use in Slack

1. Type a message in Slack
2. Wait ~200-500ms for rewrite suggestion
3. Press `[y]` to accept or `[n]` to reject
4. Press Enter to send

---

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `y` | Accept rewrite |
| `n` | Reject rewrite |
| `u` | Undo/Cancel |
| `Ctrl+C` | Quit overlay |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Slack Desktop                              │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Electron Process (Chromium)                              │  │
│  │  ┌─────────────────────────────────────────────────────┐  │  │
│  │  │  WebView                                              │  │  │
│  │  │  ┌─────────────────────────────────────────────────┐│  │  │
│  │  │  │  #message-input field                            ││  │  │
│  │  │  │  "Hello team!"                                   ││  │  │
│  │  │  └─────────────────────────────────────────────────┘│  │  │
│  │  └─────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────┘  │
│                    ↓                                             │
│           Chrome DevTools Protocol                              │
│                    ↓                                             │
└─────────────────────────────────────────────────────────────────┘
                           │
┌──────────────────────────┴──────────────────────────────────────┐
│                     WorkSpeak Overlay                           │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐  │
│  │  CDP Client      │  │  Input Monitor   │  │  Rewrite     │  │
│  │  (devtools)      │  │  (DOM observer)  │  │  Worker      │  │
│  └────────┬─────────┘  └────────┬─────────┘  └──────┬───────┘  │
│           │                     │                    │          │
│           └─────────────────────┴────────────────────┘          │
│                                 │                               │
│                          ┌──────▼──────┐                        │
│                          │  Overlay UI │                        │
│                          │  (Popup)    │                        │
│                          └──────┬──────┘                        │
│                                 │                               │
└─────────────────────────────────┼───────────────────────────────┘
                                  │
                        ┌─────────▼─────────┐
                        │  Core Libraries   │
                        │  (rewriter.py)    │
                        └─────────┬─────────┘
                                  │
                        ┌─────────▼─────────┐
                        │  LLM Backend      │
                        │  (API call)       │
                        └───────────────────┘
```

---

## Component Details

### Core Libraries (`core/`)

Shared between CDP overlay and Slack bot:

- **config.py**: Configuration loading from YAML/environment variables
- **llm_backend.py**: OpenAI-compatible API client
- **logging_config.py**: Unified logging setup
- **rewriter.py**: Message rewriting with quality control

### CDP Overlay (`overlay/`)

#### devtools_client.py

Chrome DevTools Protocol client for interacting with Slack's WebView:

```python
from overlay import DevToolsConnection

cdp = DevToolsConnection(host="localhost", port=9229)
await cdp.start_session()

# Evaluate JavaScript in Slack context
result = await cdp.send_command("Runtime.evaluate", {
    "expression": "document.querySelector('#message-input')?.value"
})
```

#### input_monitor.py

Monitors Slack's input field for text changes using DOM observation:

```python
from overlay import InputMonitor

monitor = InputMonitor()

async def on_text_change(change_type, new_text):
    print(f"Text changed: {new_text}")

monitor.set_on_text_change_callback(on_text_change)
await monitor.start(cdp)
```

#### worker.py

Background worker that processes rewrite requests:

```python
from overlay import RewriteWorker, RewriteRequest

worker = RewriteWorker()

async def on_result(result):
    print(f"Rewrite complete: {result.status}")

worker.set_on_result_callback(on_result)
worker.start()

request = RewriteRequest(original_text="Hello world")
await worker.queue_rewrite(request)
```

#### overlay_ui.py

Simple text-based UI for showing rewrite suggestions:

```python
from overlay import OverlayUI

ui = OverlayUI()
ui.show_suggestion("Hello world", "Hi there!")
# Displays suggestion in terminal with accept/reject keys
```

---

## Testing

### Test Mode (No LLM)

If no LLM config is found, the overlay runs in test mode:

```bash
python -m overlay.main
```

Output:
```
TEST MODE: No LLM configured
The overlay will display messages but won't rewrite them.
```

### Debug Mode

Enable debug logging:
```bash
python -m overlay.main --debug
```

### Integration Test

1. Start Slack with CDP:
   ```bash
   slack --inspect=9229
   ```

2. Start overlay:
   ```bash
   python -m overlay.main
   ```

3. Type in Slack → See overlay suggestion

---

## Troubleshooting

### Connection Refused

**Error:** `Could not connect to CDP endpoint`

**Fix:**
1. Make sure Slack is running with `--inspect=9229`
2. Verify: `ss -tlnp | grep 9229` shows `127.0.0.1:9229`
3. Try different port: `slack --inspect=9228`

### Input Not Detected

**Error:** `Could not find input element`

**Diagnosis:**
- Slack UI may have changed
- Try restarting Slack with CDP

**Workaround:** The overlay falls back to generic mode which uses JavaScript evaluation.

### Rewrite Not Working

**Check:**
1. LLM config is valid: `LLM_ENDPOINT` and `LLM_API_KEY` set
2. API key works: Test endpoint directly
3. Debug logs: `python -m overlay.main --debug`

### High Latency

**Solutions:**
1. Use faster LLM endpoint (Groq, Fireworks)
2. Reduce `max_tokens` in config
3. Check network latency to API

---

## Security

### CDP Port Security

Slack binds to `127.0.0.1:9229` by default. This is **NOT exposed** to your network:

- ✅ WiFi users cannot access `127.0.0.1`
- ✅ Only local processes can connect
- ✅ Kernel-level isolation

**DO NOT use:** `slack --inspect=0.0.0.0:9229` ❌

### Data Privacy

- ✅ Chat data stays on your machine
- ✅ No Slack API permissions required
- ✅ CDP session only sees what you see

---

## Future Enhancements

The following enhancements are planned:

1. **GUI Overlay**: Replace terminal UI with Tkinter/GTK popup window
2. **Context Awareness**: Access Slack's Redux state for channel context
3. **Smart Fallbacks**: Rule-based rewrites for common patterns
4. **Cache Layer**: Store recent rewrites for instant responses
5. **Multi-Tab Support**: Monitor multiple Slack tabs
6. **Custom Prompts**: Allow users to define rewrite styles

---

## Contributing

### Adding a Feature

1. Create feature branch
2. Implement in appropriate module
3. Add tests
4. Update documentation

### Running Tests

```bash
pytest tests/ -v
```

---

## License

See [LICENSE.md](../LICENSE.md)

---

## Acknowledgments

- Based on WorkSpeak architecture design
- Chrome DevTools Protocol by Google
- Slack Electron platform
