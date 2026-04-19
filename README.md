# WorkSpeak Bot

A Slack bot that listens for your messages and automatically rewrites them to be more professional and concise using LLM-powered editing.

## Features

- **Automatic message editing**: Detects your messages and rewrites them in real-time
- **LLM-powered**: Uses OpenAI-compatible models for intelligent rewriting
- **3-tier quality control**: Combines heuristic checks, semantic embeddings, and iterative refinement
- **Flexible configuration**: Set up via environment variables or YAML config
- **Thread context**: Considers conversation context when rewriting
- **Professional signature**: All edits are clearly marked

## Architecture

```
┌─────────────┐     ┌──────────────────┐     ┌──────────────┐
│   Slack     │────▶│   Bolt Server    │────▶│  LLM Rewriter│
│  Socket     │     │   (Event Handler)│     │  + QC Layer  │
│    Mode     │     └──────────────────┘     └──────────────┘
└─────────────┘                                  │
                                                 ▼
                                          ┌──────────────┐
                                          │  Edit Message│
                                          │  in Channel  │
                                          └──────────────┘
```

## Setup

### 1. Create a Slack App

1. Visit [Slack API](https://api.slack.com/apps)
2. Click "Create New App" → "From scratch"
3. Add these OAuth scopes:
   - `chat:write` - To edit messages
   - `chat:write.customize` - To customize bot messages
   - `im:read` / `im:write` - For DMs
   - `channels:history` - To read thread context

4. Install the app to your workspace
5. Generate and copy:
   - **Bot User OAuth Token** (starts with `xoxb-`)
   - **Signing Secret**
   - **App-Level Token** (starts with `xapp-`) for Socket Mode

### 2. Get your User ID

The bot will only edit messages from your account. Get your Slack user ID:

```python
import requests
r = requests.get('https://slack.com/api/auth.test', headers={'Authorization': 'Bearer YOUR_BOT_TOKEN'})
print(r.json()['user_id'])  # e.g., U0123456789
```

### 3. Configure Environment

Copy the example `.env`:

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```bash
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_SIGNING_SECRET=your-signing-secret
SLACK_APP_TOKEN=xapp-your-app-token
BOT_USER_ID=U0123456789
LLM_API_KEY=your-openai-key
LLM_ENDPOINT=https://api.openai.com/v1/chat/completions
LLM_MODEL=gpt-4o
```

### 4. Install Dependencies

```bash
# Create virtual environment (if needed)
python3 -m venv venv
source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

## Running the Bot

```bash
# Direct run
python -m slack_message_bot

# Or with bash
bash run.sh
```

The bot will:
1. Connect to Slack via Socket Mode
2. Listen for messages from your user ID
3. Fetch thread context if available
4. Rewrite the message using the LLM
5. Apply quality control checks
6. Update the original message with a signature

## Configuration

### LLM Configuration Priority

1. **Environment variables** (highest priority)
   ```bash
   LLM_API_KEY=...
   LLM_ENDPOINT=https://...
   LLM_MODEL=gpt-4o
   LLM_PROVIDER=openai
   ```

2. **YAML config file**
   - Default: `config/llm_config.yaml`
   - Override with: `LLM_CONFIG_FILE=/path/to/config.yaml`

3. **OpenAI-compatible endpoints**

The bot works with any OpenAI-compatible endpoint:

```yaml
# Groq
endpoint: https://api.groq.com/openai/v1/chat/completions
model: llama-3.1-70b-versatile

# Together AI
endpoint: https://api.together.xyz/v1/chat/completions
model: mistralai/Mixtral-8x7B-Instruct-v0.1

# vLLM (self-hosted)
endpoint: https://your-vllm-server/v1/chat/completions
model: your-locally-served-model
```

## Quality Control

The bot uses a multi-tier quality assurance system:

### Tier 1: Heuristic Checks
- Metadata removal (token counts, costs, iteration info)
- Artifact filtering (exploration text, summaries, reasoning)
- Tone detection (slang, abbreviations)
- Conciseness ratio (word count comparison)

### Tier 2: Semantic Similarity
- Uses `sentence-transformers` (all-MiniLM-L6-v2)
- Cosine similarity between original and rewritten
- Default fallback if embeddings unavailable

### Tier 3: Iterative Refinement
- If score is in "grey zone" (0.60-0.85), re-attempt rewrite
- Maximum 3 iterations
- Returns best result or original text if no improvement

### Decision Logic

| Score | Action |
|-------|--------|
| ≥0.85 | Accept rewrite |
| 0.60-0.85 | Retry rewrite |
| <0.60 | Keep original |

## Logging

Logs are written to `logs/workSpeak.log` (configurable via `WORKSPEAK_LOG_FILE`).

Quality decisions are logged:
```
2026-04-19 23:45:12 - slack_message_bot.app - INFO - [Quality] Decision: accepted (score: 0.87)
2026-04-19 23:45:12 - slack_message_bot.app - INFO - [Original] hey guys lol omg meeting is super important
2026-04-19 23:45:12 - slack_message_bot.app - INFO - [Rewritten] Hello team, confirming an important meeting
```

## Thread Context

When rewriting messages in a thread, the bot fetches up to 5 recent messages in the thread to provide context. This helps maintain conversation coherence.

## Testing

```bash
# Run tests (using existing venv pytest)
.venv/bin/python -m pytest tests/ -v
```

### Test Coverage
- `test_config.py`: LLM configuration loading
- `test_llm_backend.py`: Prompt formatting
- `test_rewriter.py`: Post-processing, quality checks
- `test_integration.py`: Integration tests

## Troubleshooting

### Bot doesn't edit my messages
1. Verify `BOT_USER_ID` is set to your Slack user ID
2. Check logs: `cat logs/workSpeak.log`
3. Ensure the app has `chat:write` and `chat:write.customize` scopes
4. Message must be in a channel or DM where the bot can see it

### LLM errors
1. Verify `LLM_API_KEY` is valid
2. Test endpoint manually:
   ```bash
   curl -X POST https://api.openai.com/v1/chat/completions \
        -H "Authorization: Bearer YOUR_KEY" \
        -H "Content-Type: application/json" \
        -d '{"model": "gpt-4o", "messages": [{"role": "user", "content": "test"}]}'
   ```
3. Check logs for error details

### Message not being edited (stays same)
- Quality score may be too low (<0.60)
- Original message may already be professional
- Try sending a more informal message to test

## License

MIT License - feel free to use and modify as needed.
