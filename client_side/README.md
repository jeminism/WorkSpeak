# WorkSpeak Client-Side Agent

A local monitoring and rewriting agent that intercepts your Slack messages **before sending**, providing professional rewriting for all message types including:
- Direct messages to other humans (NOT possible with Slack bot)
- Messages in any channel (no bot installation needed)
- Group conversations
- Any text field your computer sees

## Key Differences from Slack Bot

| Feature | Slack Bot | Client-Side Agent |
|---------|-----------|-------------------|
| Works in 1:1 DMs | ❌ No | ✅ **Yes** |
| Works in any channel | ❌ Needs bot added | ✅ **Yes** (no setup) |
| Preview before sending | ❌ No | ✅ **Yes** |
| Cross-device | ✅ Yes | ❌ One device only |
| Mobile support | ❌ No | ❌ No |
| Latency | 1-2 seconds | <1 second |
| Privacy | Bot sees all | Only on your device |

## How It Works

1. **Monitor**: Detects Slack desktop app and monitors text input fields
2. **Intercept**: Captures messages as you type (before send)
3. **Rewrite**: Sends to LLM for professional rewriting
4. **Replace**: Automatically replaces text in Slack input field
5. **Preview** (optional): Shows preview before final send
6. **Send**: You send already-rewritten message

## Requirements

### Platform Support
- **Windows**: Python 3.8+, requires Administrator privileges for some features
- **macOS**: Python 3.8+, requires Accessibility permissions
- **Linux**: Python 3.8+, requires xdotool (for some distributions)

### Dependencies
```bash
pip install -r client_side/requirements.txt
```

### Setup Steps

1. **Create Configuration**
   ```bash
   python -m client_side --create-config
   ```

2. **Edit Configuration**
   ```bash
   nano config/client_config.yaml
   # Add your LLM API key
   ```

3. **Install Platform Dependencies**
   ```bash
   # Windows
   pip install pywin32 uiautomation
   
   # macOS  
   pip install pyobjc
   
   # Linux
   sudo apt-get install xdotool
   pip install python-xlib
   ```

4. **Grant Permissions**
   - **Windows**: Run as Administrator (optional but recommended)
   - **macOS**: 
     ```
     Settings → Privacy & Security → Accessibility → Add Terminal/Python
     ```
   - **Linux**: May require adding user to appropriate groups

5. **Run**
   ```bash
   python -m client_side
   
   # Or with system tray (default)
   python -m client_side
   
   # Or headless (no tray)
   python -m client_side --no-tray
   ```

## Usage

### Automatic Rewriting
- When enabled, rewrites happen automatically
- You'll see the new text replace what you typed
- Quality score is logged (≥0.85 = auto-accept)

### Manual Trigger
- Press `Ctrl+Shift+R` (or configured shortcut)
- Rewrites currently selected input field
- Good for retrying a rewrite

### Preview Mode
- Show preview window for messages below quality threshold
- Press `Enter` to approve, `Esc` to cancel
- Helps catch unwanted rewrites

### Status Tray
- System tray icon shows running status
- Right-click to:
  - Toggle auto-rewrite on/off
  - View statistics
  - Open configuration
  - Quit application

## Configuration Options

### LLM Settings
- `endpoint`: Your LLM API endpoint
- `api_key`: Your API key
- `model`: Model to use (gpt-4o, llama-3, etc.)
- `timeout`: Request timeout in seconds

### Behavior
- `auto_rewrite`: Enable/disable automatic rewriting
- `preview_enabled`: Show preview window
- `keyboard_shortcut`: Custom trigger key
- `min_quality_score`: Minimum score for auto-accept

### Privacy
- `respect_dm_privacy`: Only rewrite if marked as private (best-effort)
- `rewrite_all`: Rewrite all messages you compose (default: false)

## Troubleshooting

### "Slack not detected"
- Make sure Slack is running
- Check logs for platform-specific errors
- Try running as Administrator (Windows) or with Accessibility permissions (macOS)

### "Text not being replaced"
- Check keyboard shortcut is working
- Verify hook is available (`python -m client_side --test`)
- Try different input field ID

### "Rewrite doesn't change much"
- Check quality score in logs
- Try adjusting prompt in rewriter.py
- Consider using a more capable LLM model

### "Permissions denied" (macOS)
- Go to Settings → Privacy & Security → Accessibility
- Add Terminal or Python to allowed apps
- Restart application

## Development

### Testing
```bash
# Run test mode
python -m client_side --test

# Run with test config
python -m client_side --config tests/test_config.yaml
```

### Log Files
- Default: `logs/workSpeak_client.log`
- Can be changed in config file
- Includes all rewrite attempts and errors

### Architecture
```
client_side/
├── __init__.py
├── __main__.py         # Entry point
├── core/
│   ├── interceptor.py  # Message detection
│   ├── rewriter.py     # LLM rewriting
│   ├── llm_backend.py  # LLM integration
│   └── preview.py      # Preview logic
├── integrations/
│   ├── desktop_hook.py # Platform hooks
│   └── accessibility_monitor.py # Fallback monitor
├── interfaces/
│   ├── tray_icon.py    # System tray
│   └── config_dialog.py # Config UI
├── config/
│   └── __init__.py     # Configuration loader
└── requirements.txt
```

## License

MIT License - See LICENSE file

## Important Notes

⚠️ **This is experimental software**
- May not work perfectly on all configurations
- Test thoroughly before relying on it
- Report bugs via GitHub issues

⚠️ **Privacy Considerations**
- All messages are sent to your LLM provider
- Your API key is stored locally (configure encryption for production)
- Don't rewrite sensitive/confidential messages

⚠️ **Platform Limitations**
- Only works on your computer (not mobile)
- Requires Python and dependencies installed
- May not work with some Slack customizations or Enterprise Grid

## Future Features

- [ ] Mobile app integration
- [ ] Browser extension support
- [ ] Context-aware prompts (learn your style)
- [ ] Template-based rewrites
- [ ] Multilingual support
- [ ] Integration with Slack API for better context
- [ ] Analytics dashboard
- [ ] Custom prompt templates
