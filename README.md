# WorkSpeak - Professional Message Rewriting

A comprehensive system for automatically rewriting Slack messages to be more professional and concise.

## Architecture Overview

WorkSpeak offers **two complementary approaches** to message rewriting, each suited to different use cases:

### 1. Slack Bot (Channel-Based)

**Best for**: Channel messages with thread context, cross-device operation

- Listens via Slack Bolt SDK with Socket Mode
- Rewrites messages **asynchronously** (after sending)
- Supports full thread context via Slack API
- Limited to channels where bot is added
- ✗ Cannot work with 1:1 DMs to other humans (Slack platform limitation)
- ✅ Works on all devices when bot is in channel

### 2. Client-Side Agent (Local Interceptor)

**Best for**: Universal rewriting including 1:1 DMs, preview before sending

- Monitors Slack desktop app input fields locally
- Rewrites messages **before sending** (synchronous)
- Works in any channel without bot installation
- ✅ Can rewrite 1:1 DMs to other humans (solves Slack API limitation)
- ✅ Can show preview before sending
- Limited to single device (your computer)

**Read more**: [Client-Side Agent Documentation](client_side/README.md)

### Feature Comparison

| Feature | Slack Bot | Client-Side Agent |
|---------|-----------|-------------------|
| ✅ Works in channels | Yes | Yes |
| ✅ Works in 1:1 DMs to others | ❌ No | ✅ **Yes** |
| ✅ Preview before sending | ❌ No | ✅ **Yes** |
| ✅ Thread context access | Full | Limited |
| ✅ Cross-device operation | Yes | ❌ One only |
| ✅ Requires bot installation | Yes | ❌ No |
| ✅ Latency | 1-2 seconds | <1 second |

## Architecture Details

**Slack Bot** connects to Slack's API platform:
- Requires Slack App Token + Bot Token
- Listens via Socket Mode or Events API
- Can access Slack thread history
- Subject to Slack's channel privacy model

**Client-Side Agent** runs locally on your computer:
- NO Slack API connection required
- Uses OS-level accessibility hooks
- Monitors your local Slack input field
- Not subject to platform privacy restrictions

## Documentation

Read the documentation that fits your use case:

- **[Main Project Documentation](README.md)** - This overview
- **[Slack Bot Setup Guide](slack_message_bot/README.md)** - Channel-based approach
- **[Client-Side Agent Guide](client_side/README.md)** - Local interception approach
- **[Architecture Design](slack_rewriter_architecture.md)** - Technical system design
- **[Connection Clarification](client_side/CONNECTION_CLARIFICATION.md)** - How client connects (it doesn't!)

## Quick Setup

### Slack Bot (Channel-Based)

```bash
# Install bot dependencies
pip install -r requirements.txt

# Configure LLM
cp config/llm_config.yaml.example config/llm_config.yaml
# Edit config/llm_config.yaml with your API key

# Run bot
python -m slack_message_bot --mode slack
```

### Client-Side Agent (Local Interceptor)

```bash
# Install client dependencies
pip install -r client_side/requirements.txt

# Create configuration
python -m client_side --create-config

# Grant permissions (macOS only)
# System Settings → Privacy → Accessibility → Add Python

# Run client
python -m client_side
```

## Use Case Recommendations

### When to use Slack Bot:

✅ You mainly need channel rewriting  
✅ You want thread context for better rewrites  
✅ You need cross-device operation  
✅ Your workspace allows bot installation  
✅ You primarily use public/work channels  

### When to use Client-Side Agent:

✅ You need to rewrite 1:1 DMs to other humans  
✅ You want to see preview before sending  
✅ You don't want to install bots in channels  
✅ You mainly use one computer  
✅ You have macOS/Windows/Linux desktop access  

### Best of Both Worlds:

Many users benefit from **both approaches**:
- Use Slack Bot for channels with thread context
- Use Client-Side Agent for personal DMs and preview control

## Components

### Slack Bot
- `slack_message_bot/` - Core bot implementation
- `slack_message_bot/rewriter.py` - Messages rewriter
- `slack_message_bot/llm_backend.py` - LLM integration
- `slack_message_bot/app.py` - Event handler

### Client-Side Agent
- `client_side/core/` - Message interception, rewriting logic
- `client_side/integrations/` - Platform hooks and monitors
- `client_side/interfaces/` - UI components (tray, config dialog)
- `client_side/config/` - Configuration management

## Quality Control

Both agents implement multi-tier quality assurance:

1. **Heuristic checks**: Length, professionalism, grammar (fast, no cost)
2. **Quality scoring**: Confidence-based decision making
3. **Post-processing**: Removes LLM artifacts and metadata
4. **Fallback handling**: Graceful degradation on errors

## LLM Configuration

Both architectures share the same LLM configuration system:

```yaml
# config/llm_config.yaml (Slack Bot)
# config/client_config.yaml (Client-Side)
llm:
  endpoint: "https://api.openai.com/v1/chat/completions"
  api_key: "your-api-key"
  model: "gpt-4o"
  provider: "openai"
```

Supported providers:
- OpenAI (default)
- Anthropic Claude
- Any OpenAI-compatible endpoint (Groq, Together AI, vLLM, etc.)

## Testing

### Slack Bot Tests

```bash
cd tests
pytest test_llm_backend.py -v
pytest test_rewriter.py -v
pytest test_config.py -v
```

### Client-Side Tests

```bash
cd client_side
pytest tests/test_client.py -v
python -m client_side --test
```

## Troubleshooting

### Slack Bot Issues

**"Bot doesn't edit messages"**
- Verify `BOT_USER_ID` is set correctly
- Check bot has `chat:write` and `chat:write.customize` scopes
- Ensure bot is added to the channel

**"Slack API errors"**
- Check `SLACK_BOT_TOKEN` is valid
- Verify Workspace has bot installed
- Review logs: `cat logs/workSpeak.log`

### Client-Side Issues

**"Slack not detected"**
- Make sure Slack desktop app is running
- Grant accessibility permissions (macOS)
- Check system logs for platform-specific errors

**"Text not being replaced"**
- Verify accessibility permissions granted
- Check keyboard shortcuts aren't conflicting
- Update `pyautogui` to latest version

## License

MIT License

## Contributing

### Development

```bash
# Setup both components
git clone <repo-url>
cd workSpeak

# Slack Bot
pip install -r requirements.txt

# Client-Side
cd client_side
bash quickstart.sh
cd ..

# Create config files
python -m client_side --create-config
```

### Testing

```bash
# Run all tests
pytest

# Code coverage
pytest --cov=. --cov-report=html
```

## Related Resources

- [Slack API Documentation](https://api.slack.com/)
- [Slack Bolt SDK](https://slack.dev/bolt-python/)
- [UI Automation (Windows)](https://github.com/yossiyas/UIAutomation)
- [Accessibility API (macOS)](https://developer.apple.com/documentation/accessibility)
- [pyautogui](https://pyautogui.readthedocs.io/)

## Changelog

### Version 2.0.0 (Current)
- ✅ Added Client-Side Agent with 1:1 DM support
- ✅ Cross-platform desktop monitoring (Windows, macOS, Linux)
- ✅ Preview window for user confirmation
- ✅ Improved quality control system
- ✅ Better error handling and logging

### Version 1.0.0
- ✅ Initial Slack Bot implementation
- ✅ Channel-based message rewriting
- ✅ Thread context support
- ✅ Multi-tier quality control
- ✅ LLM backend abstraction

---

**WorkSpeak** helps you communicate more professionally across all of Slack's features. Choose the approach that fits your workflow, or use both for comprehensive coverage.
