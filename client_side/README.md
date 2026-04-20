# WorkSpeak Client-Side Agent

A local monitoring and rewriting agent that intercepts your Slack messages **before sending**, providing professional rewriting for all message types including:
- Direct messages to other humans (NOT possible with Slack bot)
- Messages in any channel (no bot installation needed)
- Group conversations
- Any text field your computer sees

## Why Client-Side?

The client-side solution was designed to solve a fundamental limitation of Slack's API architecture:

**Problem**: Slack's privacy model prevents bots from seeing messages in private 1:1 DMs between two humans, even with `im:read` and `im:write` scopes.

**Solution**: Monitor the message as you're typing, rewrite it locally, and replace it in the input field before you press send.

## How It Works (Simple Explanation)

1. **You start the agent** in the background on your computer
2. **You use Slack normally** - type, send messages, everything as before
3. **When you type in Slack's input field**:
   - Agent detects your keystrokes via OS-level hooks
   - Agent sends text to LLM for professional rewriting
   - Agent replaces your text in the input field
   - You see the rewritten version and hit send
4. **When you switch to other apps** (Chrome, VS Code, etc.), the agent does nothing

**Key Insight**: The agent NEVER connects to Slack's API. It runs locally on your computer and uses operating system accessibility hooks to monitor and modify text in your Slack desktop app.

```
You type → Agent sees it (OS hook) → Agent rewrites (HTTPS) → Agent replaces → You send
                    ↓                      ↓                    ↓
                Local Windows          Your LLM API         Your input field
```

## Key Advantages Over Slack Bot

| Feature | Slack Bot | Client-Side Agent |
|---------|-----------|-------------------|
| **Works in 1:1 DMs** | ❌ No | ✅ **Yes** |
| **Works in any channel** | ❌ Needs bot added | ✅ **Yes** (no setup) |
| **Preview before sending** | ❌ No | ✅ **Yes** |
| Thread context | ✅ Full | ❌ Limited |
| Works across devices | ✅ Yes | ❌ One device only |
| Requires bot installation | ✅ Yes | ❌ No |
| Latency | 1-2 seconds | <1 second |

## System Requirements

### Operating Systems

- **Windows 10+** (Windows 10, Windows 11)
  - Python 3.8+
  - UIAutomation support

- **macOS 10.14+** (Mojave and later)
  - Python 3.8+
  - Accessibility permissions required

- **Linux** (Ubuntu, Fedora, Debian, etc.)
  - Python 3.8+
  - X11 or Wayland display server

### System Permissions

- **Windows**: May need to run as Administrator for some applications
- **macOS**: Requires Accessibility permission (granted via System Settings)
- **Linux**: May require X11/Wayland access

## Installation

### Quick Setup

```bash
# Method 1: Automated script
./client_side/quickstart.sh

# Method 2: Manual installation
cd client_side
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m client_side --create-config
```

### Manual Setup

1. **Install Python dependencies**
   ```bash
   pip install -r client_side/requirements.txt
   ```

2. **Create configuration file**
   ```bash
   python -m client_side --create-config --config config/client_config.yaml
   ```

3. **Edit configuration with your LLM API key**
   ```bash
   nano config/client_config.yaml
   # Or use your text editor of choice
   ```

4. **Grant permissions (macOS only)**
   - Go to System Settings → Privacy & Security → Accessibility
   - Add Terminal/Python to the allowed list
   - Restart the agent after granting permission

### Platform-Specific Dependencies

#### Windows
```bash
pip install pywin32 uiautomation pyautogui
```

#### macOS
```bash
pip install pyobjc pyautogui
```

#### Linux
```bash
# Install xdotool first (Ubuntu/Debian)
sudo apt-get install xdotool

# Then install Python packages
pip install python-xlib pyautogui
```

## Usage

### Starting the Agent

```bash
# With system tray (default)
python -m client_side

# Without tray icon (headless background)
python -m client_side --no-tray

# With custom config file
python -m client_side --config /path/to/config.yaml

# Run in test mode (no monitoring)
python -m client_side --test
```

### System Tray

When running with tray:
- A tray icon appears in your system tray (Windows) or menu bar (macOS)
- Right-click (Windows) or click (macOS) to access options:
  - **Toggle Auto-Rewrite**: On/Off
  - **Status**: View current state
  - **Configuration**: Open settings
  - **Quit**: Stop the agent

### Keyboard Shortcut

The default trigger shortcut is **Ctrl+Shift+R** (or **Cmd+Shift+R** on macOS).

Press this combination anytime you want to:
- Trigger a manual rewrite of the current Slack input field
- Override the automatic rewriting

Configurable in `client_config.yaml`:
```yaml
keyboard_shortcut: "Ctrl+Shift+R"
```

### Preview Window

When preview is enabled (default):
- A window appears showing the difference between original and rewritten text
- For high-quality rewrites (≥0.85 score), the rewrite is applied automatically
- For lower-quality rewrites, the preview window appears and you can:
  - Press **Enter** to approve the rewrite
  - Press **Esc** to cancel and keep your original text

### Configuration Options

Edit `config/client_config.yaml`:

```yaml
# LLM Configuration (Required)
llm:
  endpoint: "https://api.openai.com/v1/chat/completions"
  api_key: "YOUR_API_KEY_HERE"  # ← Edit this!
  model: "gpt-4o"
  provider: "openai"
  timeout: 30

# Client Behavior
auto_rewrite: true               # Auto-apply rewrites without preview
preview_enabled: true             # Show preview for uncertain rewrites
keyboard_shortcut: "Ctrl+Shift+R" # Manual trigger shortcut

# Platform Detection
detect_slack: true                # Automatically detect Slack app
platforms:                        # Platforms to monitor
  - desktop                       # Slack desktop app
  - browser                       # Slack web version

# Logging
log_level: INFO                   # DEBUG, INFO, WARNING, ERROR
log_file: "logs/workSpeak_client.log"

# Quality Control
min_quality_score: 0.75           # Minimum score for auto-accept
preview_threshold: 0.85           # Show preview below this score

# Privacy
respect_dm_privacy: true          # Don't rewrite if message is marked private
```

## Architecture Overview

```
client_side/
├── __main__.py                    # Application entry point
├── README.md                      # This file
├── IMPLEMENTATION.md              # Technical deep dive
├── CONNECTION_CLARIFICATION.md    # Connection model explained
├── requirements.txt               # Dependencies
├── quickstart.sh                  # Setup script
├── tests/
│   └── test_client.py            # Test suite
├── config/
│   ├── __init__.py               # Configuration loader
│   └── client_config.yaml.example
├── core/
│   ├── interceptor.py            # Message detection & monitoring
│   ├── rewriter.py               # LLM-based rewriting engine
│   ├── llm_backend.py            # API integration (shared with bot)
│   └── preview.py                # Preview management
├── integrations/
│   ├── slack_detector.py         # Platform detection
│   ├── desktop_hook.py           # OS-level hooks
│   └── accessibility_monitor.py  # Fallback monitoring
└── interfaces/
    ├── tray_icon.py              # System tray UI
    └── config_dialog.py          # Configuration window
```

## Technical Implementation Details

### 1. Platform Detection

The agent detects Slack running on your computer using OS-specific methods:

**Windows**:
- UI Automation API to find Slack windows
- Process name detection ("Slack.exe")
- Window class name matching

**macOS**:
- Accessibility API for window inspection
- Process bundle identifier detection
- System events monitoring

**Linux**:
- X11/Wayland window information
- Process name detection
- Window property queries

### 2. Message Monitoring

The agent uses continuous polling with smart optimization:

- **Polling interval**: 0.5 seconds (balances performance and responsiveness)
- **Text comparison**: Detects meaningful changes vs cursor movement
- **Channel detection**: Classifies as DM, channel, or group based on context
- **Smart idle handling**: Reduces polling when Slack is inactive

### 3. Text Injection

After rewriting, the agent replaces text in Slack's input field:

1. Focuses the input field
2. Selects all existing text (Ctrl+A)
3. Deletes the selected text
4. Types the rewritten text character-by-character
5. Timing is adjusted for reliability

### 4. Quality Control

Multi-tier quality assessment without slow embedding calculations:

- **Length check**: Rewritten text should be 10-300% of original
- **Professionalism score**: Detects slang, informal language
- **Change detection**: Verifies actual rewriting occurred
- **Decision logic**: accept/fallback/reject based on confidence

## Testing

### Run Tests

```bash
# Run all tests
pytest client_side/tests/ -v

# Run specific test
pytest client_side/tests/test_client.py::TestRewriter::test_rewrite_professionalism

# Test with actual LLM
python -m client_side --test
```

### Manual Testing

1. **Test 1: Basic rewriting**
   - Start agent
   - Open Slack
   - Type: "hey guys lol omg meeting is super important"
   - Expected: Rewritten to something like "Hi team, the meeting is critical"

2. **Test 2: DM rewriting**
   - Start a DM with someone
   - Type informal message
   - Agent should rewrite it before you send
   - Verify text was replaced automatically

3. **Test 3: Preview window**
   - Set preview threshold high
   - Type message with low rewrite quality
   - Verify preview window appears
   - Test accept/reject functionality

## Troubleshooting

### "Slack not detected"

**Windows**: 
- Make sure Slack is running
- Try running the agent as Administrator
- Check that `pywin32` and `uiautomation` are installed

**macOS**:
- Go to System Settings → Privacy & Security → Accessibility
- Ensure Terminal/Python is in the allowed list
- Restart agent after granting permission

**Linux**:
- Verify xdotool is installed: `which xdotool`
- Check X11 access permissions

### "Text not being replaced"

1. Check that keyboard shortcuts aren't conflicting
2. Verify accessibility permissions (macOS)
3. Try updating `pyautogui` to latest version
4. Check logs for injection errors

### "Rewrite doesn't change much"

1. Check quality score in logs
2. Try using a more capable LLM model
3. Adjust prompt in `rewriter.py`
4. Consider using different quality thresholds

### "Agent is slow"

1. Check LLM response time in logs
2. Try a smaller/faster model
3. Increase polling interval (less CPU usage)
4. Close other resource-intensive applications

## Security Considerations

### Data Privacy

- **Messages**: All text sent to your LLM provider (you control which one)
- **API keys**: Stored locally in config file (use environment variables for encryption)
- **Local access**: Only monitors Slack input field, nothing else
- **System permissions**: Required for accessibility hooks (standard safety model)

### Permissions Model

```
macOS Accessibility:
  ─────────────────────────
  • Grants ability to read/write in your apps
  • Only works when explicitly granted
  • Can be revoked at any time
  • Visible in System Settings

Windows UI Automation:
  ─────────────────────
  • Standard feature for accessibility
  • No special permissions needed (runs as user)
  • May require Administrator for some apps
  • Transparent to normal users
```

### Best Practices

1. **Use environment variables** for API keys:
   ```bash
   export LLM_API_KEY="your-key"
   python -m client_side
   ```

2. **Enable logging** initially to verify behavior, then reduce:
   ```yaml
   log_level: DEBUG  # Initially
   log_level: INFO   # Production
   ```

3. **Test thoroughly** before relying on auto-rewrite:
   ```bash
   python -m client_side --test
   ```

4. **Review permissions** regularly to ensure they're still needed

## Advanced Usage

### Custom Prompts

Modify the prompt template in `core/rewriter.py`:

```python
def _build_prompt(self, text: str, channel_type: str) -> str:
    """Custom prompt for rewriting"""
    
    channel_context = {
        'dm': 'Keep professional but personal.',
        'channel': 'Be formal and concise.',
        'group': 'Inclusive and clear.'
    }
    
    return f"""Rewrite this message to be professional:
{text}

Context: {channel_context.get(channel_type, '')}

Return only the rewritten text."""
```

### Multiple LLM Backends

Support different LLMs for different channel types in `llm_backend.py`:

```python
def get_backend_for_channel(channel_type):
    if channel_type == 'dm':
        return get_backend(model='gpt-4o-mini')  # Fast, cheaper
    else:
        return get_backend(model='gpt-4o')        # Higher quality
```

### Analytics

Track rewrite statistics in `logs/workSpeak_client.log`:

```
[2026-04-20 15:30:45] Quality: 0.82, Decision: accept
[2026-04-20 15:31:02] Quality: 0.71, Decision: fallback
[2026-04-20 15:31:18] Quality: 0.94, Decision: accept
```

## Comparison with Other Approaches

### Browser Extension

**Pros**: Easier implementation, cross-platform
**Cons**: Only works for Slack web version, doesn't work in desktop app
**Best for**: Users who prefer web Slack

### Clipboard Interceptor

**Pros**: Simple, low overhead
**Cons**: Requires manual copy/paste, not real-time
**Best for**: Users who don't mind manual workflow

### OS-Level Accessibility Monitoring

**Pros**: Works everywhere, real-time, native UX
**Cons**: Requires system permissions, more complex
**Best for**: Full automation with minimal friction

## Roadmap

### Planned Features

- [ ] Smart context awareness (learn your style over time)
- [ ] Template-based rewrites (save common phrases)
- [ ] Multilingual support (rewrite in different languages)
- [ ] Integration with Slack API for thread context
- [ ] Analytics dashboard (usage statistics)
- [ ] Customizable tone sliders (more formal → more casual)
- [ ] Mobile app version (iOS/Android)

### Known Limitations

- ❌ Cannot access Slack thread history (only your input text)
- ❌ Requires running on same device where you type
- ❌ May have conflicts with some enterprise security software
- ❌ Accessibility permissions required on macOS
- ❌ Cannot see messages sent by other users

## Documentation

### Quick Links

- [README.md](../README.md) - Main project overview
- [IMPLEMENTATION.md](IMPLEMENTATION.md) - Technical deep dive
- [CONNECTION_CLARIFICATION.md](CONNECTION_CLARIFICATION.md) - Connection model explained
- [requirements.txt](requirements.txt) - Dependencies

### Related Documentation

- [Slack Bot Setup](../README.md#1-slack-bot-channel-based) - Channel-based rewriting
- [Architecture Design](../slack_rewriter_architecture.md) - Overall system design

## License

MIT License - See [../LICENSE](../LICENSE)

## Contributing

### Development Setup

```bash
# Clone repo
git clone <repo-url>
cd workSpeak

# Setup client-side
cd client_side
bash quickstart.sh

# Run development mode
python -m client_side --no-tray
```

### Testing

```bash
# Run test suite
pytest tests/ -v

# Code coverage
pytest tests/ --cov=client_side --cov-report=html
```

## FAQ

### Q: Does this work on mobile Slack apps?

**A**: No, the client-side agent only works on desktop applications (Windows, macOS, Linux). Mobile platforms don't provide the same accessibility hooks.

### Q: Can I use this on a work computer?

**A**: You can, but check your company's IT policies first. The agent requires accessibility permissions which may be restricted by enterprise security policies.

### Q: Is my data sent anywhere?

**A**: Only your typed text is sent to your LLM provider (via HTTPS). The agent doesn't send messages to anyone else.

### Q: Can the agent rewrite messages in other applications?

**A**: No, the agent specifically monitors for Slack's input field. It won't intercept text in other applications.

### Q: What if I accidentally approve a bad rewrite?

**A**: You can undo in Slack using Ctrl+Z (or Cmd+Z on macOS) to revert the text before sending.

### Q: Can I disable auto-rewrite temporarily?

**A**: Yes, click the tray icon and toggle "Auto-Rewrite" off, or use the toggle in the configuration dialog.

### Q: Does this work with Slack Enterprise Grid?

**A**: Yes, as long as your Slack desktop app is running. The agent doesn't need any Slack API access.

## Support

For issues, questions, or feature requests:

1. Check existing documentation above
2. Review logs: `cat logs/workSpeak_client.log`
3. Open an issue on the project repository
4. Email: support@example.com (placeholder)

---

## Quick Start Summary

```bash
# 1. Install
./client_side/quickstart.sh

# 2. Configure (edit config file with your LLM API key)
nano config/client_config.yaml

# 3. Grant permissions (macOS only)
# System Settings → Privacy → Accessibility → Add Python

# 4. Run
python -m client_side

# 5. Test
python -m client_side --test
```

### Ready! Now just use Slack normally. The agent will automatically rewrite your messages.
