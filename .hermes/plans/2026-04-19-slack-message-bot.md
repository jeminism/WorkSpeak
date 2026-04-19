# Slack Professional Message Bot Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Build a Slack bot that listens for user messages, rewrites them to be more professional and concise using an LLM, and edits the original message with quality control checks.

**Architecture:** Event-driven server using Slack Bolt SDK for Socket Mode. Pipeline: MessageEvent → ThreadHistoryFetcher → LLM Rewriter (configurable backend) → Quality Control (3-tier) → EditMessage with bot signature. Config via env vars/YAML/CLI args.

**Tech Stack:** Slack Bolt SDK, FastAPI, OpenAI/Anthropic API, sentence-transformers, PyYAML, python-dotenv

---

### Task 1: Initialize project structure and dependencies

**Objective:** Create base project with requirements.txt and directory structure.

**Files:**
- Create: `requirements.txt`
- Create: `slack_message_bot/`
- Create: `slack_message_bot/__init__.py`
- Create: `config/`

**Step 1: Write requirements.txt**

```txt
slack-bolt>=1.18.0
pyyaml>=6.0.1
python-dotenv>=1.0.0
sentence-transformers>=2.3.0
openai>=1.12.0
requests>=2.31.0
numpy>=1.26.0
```

**Step 2: Create directories**

```bash
mkdir -p slack_message_bot config tests
touch slack_message_bot/__init__.py config/__init__.py tests/__init__.py
```

**Step 3: Commit**

```bash
git init -q && git add . && git commit -m "chore: init project structure"
```

---

### Task 2: Create LLM configuration manager

**Objective:** Build config loader supporting env vars → YAML → CLI args priority.

**Files:**
- Create: `slack_message_bot/config.py`

```python
import os
import yaml
from dataclasses import dataclass
from typing import Optional

@dataclass
class LLMConfig:
    endpoint: str
    api_key: str
    model: str = "gpt-4o"
    provider: str = "openai"

def load_llm_config() -> LLMConfig:
    """Load LLM config with priority: env vars > YAML file > raise error."""
    
    # Priority 1: Environment variables
    api_key = os.getenv("LLM_API_KEY")
    endpoint = os.getenv("LLM_ENDPOINT")
    
    if api_key and endpoint:
        return LLMConfig(
            endpoint=endpoint,
            api_key=api_key,
            model=os.getenv("LLM_MODEL", "gpt-4o"),
            provider=os.getenv("LLM_PROVIDER", "openai")
        )
    
    # Priority 2: YAML config file
    config_path = os.getenv("LLM_CONFIG_FILE", "config/llm_config.yaml")
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f)
        return LLMConfig(
            endpoint=config_data['endpoint'],
            api_key=config_data['api_key'],
            model=config_data.get('model', 'gpt-4o'),
            provider=config_data.get('provider', 'openai')
        )
    
    raise ValueError(
        "No LLM configuration found. "
        "Set LLM_API_KEY and LLM_ENDPOINT env vars, "
        "or create config/llm_config.yaml"
    )

```

**Step 3: Commit**

```bash
git add slack_message_bot/config.py && git commit -m "feat: add LLM config manager"
```

---

### Task 3: Create LLM backend abstraction

**Objective:** Build backend interface supporting OpenAI and any OpenAI-compatible endpoint.

**Files:**
- Create: `slack_message_bot/llm_backend.py`

```python
import json
import requests
from abc import ABC, abstractmethod
from dataclasses import dataclass
from slack_message_bot.config import LLMConfig

@dataclass
class LLMCallResult:
    text: str
    token_usage: Optional[int] = None
    error: Optional[str] = None

class LLMBackend(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    def generate(self, prompt: str, config: LLMConfig) -> LLMCallResult:
        pass
    
    def _normalize_prompt(self, original_text: str, thread_context: str = "") -> str:
        """Build the prompt for rewriting."""
        context_section = f"\n\nThread context:\n{thread_context}\n\n" if thread_context else ""
        
        return f"""You are a professional message editor. Rewrite the following Slack message to be:
- More professional yet friendly
- Concise (no long prose or circular statements)
- Semantically equivalent to the original

Original message:
{original_text}{context_section}

Rewrite the message below. Return ONLY the rewritten text, nothing else. No explanation, no notes, no preamble. Just the rewritten message.
"""

class OpenAIBackend(LLMBackend):
    """OpenAI-compatible endpoint backend."""
    
    def generate(self, prompt: str, config: LLMConfig) -> LLMCallResult:
        try:
            response = requests.post(
                config.endpoint,
                headers={
                    "Authorization": f"Bearer {config.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": config.model,
                    "messages": [{"role": "user", "content": prompt}]
                },
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            text = data['choices'][0]['message']['content']
            return LLMCallResult(text=text, token_usage=data.get('usage', {}).get('total_tokens'))
        except Exception as e:
            return LLMCallResult(text="", error=str(e))

def get_backend() -> LLMBackend:
    return OpenAIBackend()

```

**Step 4: Commit**

```bash
git add slack_message_bot/llm_backend.py && git commit -m "feat: add LLM backend abstraction"
```

---

### Task 4: Create message rewriter with quality control

**Objective:** Build the rewriter pipeline with 3-tier quality control (heuristic → embedding → LLM-as-judge).

**Files:**
- Create: `slack_message_bot/rewriter.py`

```python
import re
import numpy as np
from typing import Optional, Tuple
from sentence_transformers import SentenceTransformer
from slack_message_bot.llm_backend import LLMBackend, LLMCallResult, get_backend
from slack_message_bot.config import LLMConfig

class MessageRewriter:
    """Rewrites messages with 3-tier quality control."""
    
    def __init__(self):
        self.backend = get_backend()
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.post_processors = [self._remove_metadata, self._remove_artifacts]
    
    def _remove_metadata(self, text: str) -> str:
        """Remove standard LLM metadata patterns."""
        patterns = [
            r'with\s+\d+\s+tokens?\s+used(?:[,].*)?(?:\$?\d+\.?\d*)?(?:,|$).*a\s+successful\s+outcome',
            r'with\s+\d+\s+tokens?\s+used',
            r'Estimated\s+cost:\s+\$?\d+\.?\d+',
            r'Quality\s+score:\s*[\d.]+',
            r'\d+\s+iterations?',
        ]
        result = text
        for pattern in patterns:
            result = re.sub(pattern, '', result, flags=re.IGNORECASE)
        return result.strip()
    
    def _remove_artifacts(self, text: str) -> str:
        """Remove LLM explanation artifacts."""
        patterns = [
            r'This revised response aims to:',
            r'The rewritten text is:',
            r'###?\s*(Summary|Explanation|Reasoning|Thinking)',
            r'(In\s+summary|To\s+summarize|Here is the revised):',
            r'Here is the rewritten text:',
        ]
        result = text
        for pattern in patterns:
            result = re.sub(pattern, '', result, flags=re.IGNORECASE).strip()
        
        # Remove numbered lists and bullets from explanations
        result = re.sub(r'^\d+\.\s+', '', result, flags=re.MULTILINE)
        result = re.sub(r'^[-•*]\s+', '', result, flags=re.MULTILINE)
        result = re.sub(r'^###?.*\n', '', result, flags=re.MULTILINE)
        
        return result.strip()
    
    def _post_process(self, text: str) -> str:
        """Apply all post-processors."""
        for processor in self.post_processors:
            text = processor(text)
        return text
    
    def _check_semantic_similarity(self, original: str, rewritten: str) -> float:
        """Check cosine similarity between embeddings."""
        try:
            orig_emb = self.embedding_model.encode(original, convert_to_numpy=True)
            rewrt_emb = self.embedding_model.encode(rewritten, convert_to_numpy=True)
            similarity = np.dot(orig_emb, rewrt_emb) / (np.linalg.norm(orig_emb) * np.linalg.norm(rewrt_emb))
            return float(similarity)
        except:
            return 0.0
    
    def _check_conciseness(self, original: str, rewritten: str) -> float:
        """Check word count ratio (0-1, where 1 means equally concise)."""
        orig_words = len(original.split())
        rewrt_words = len(rewritten.split())
        if orig_words == 0:
            return 1.0
        # Penalize if rewritten is more than 2x longer or less than 0.5x
        ratio = rewrt_words / orig_words
        if ratio <= 0.5:
            return min(0.5 + ratio, 1.0)
        elif ratio >= 2.0:
            return max(0.5 - (ratio - 2), 0.0)
        else:
            return 1.0
    
    def _check_tone(self, text: str) -> float:
        """Simple heuristic tone check (presence of unprofessional markers)."""
        unprofessional = ['lol', 'omg', 'wtf', 'idk', 'tbh', 'imo', 'fyi', 'thx', 'thanks!', 'thanks!']
        lower_text = text.lower()
        violations = sum(1 for w in unprofessional if w in lower_text)
        return max(0.0, 1.0 - (violations * 0.3))
    
    def _quality_score(self, original: str, rewritten: str, rerun_llm: bool = False) -> Tuple[str, bool]:
        """
        Perform multi-tier quality check.
        Returns (decision: accept/rewrite/keep, should_retry)."""
        
        # Tier 1: Heuristic (fast, no cost)
        similarity = self._check_semantic_similarity(original, rewritten)
        conciseness = self._check_conciseness(original, rewritten)
        tone = self._check_tone(rewritten)
        
        overall_score = 0.4 * similarity + 0.3 * conciseness + 0.3 * tone
        
        # Thresholds
        if overall_score >= 0.85:
            return ("accept", False)
        elif overall_score >= 0.60:
            return ("rewrite", rerun_llm)
        else:
            return ("keep", False)
    
    def rewrite(self, original_text: str, thread_context: str = "", max_iterations: int = 3) -> Tuple[str, str]:
        """
        Rewrite message with quality control.
        Returns (final_text, quality_decision)."""
        
        iterations = 0
        current_text = original_text
        
        while iterations < max_iterations:
            # Generate rewrite using LLM
            prompt = self.backend._normalize_prompt(current_text, thread_context)
            result = self.backend.generate(prompt, config)
            
            if result.error:
                # No modification if LLM fails
                return (original_text, f"error: {result.error}")
            
            # Post-process the output
            rewritten = self._post_process(result.text)
            
            if not rewritten or rewritten == current_text:
                return (current_text, "keep")
            
            # Quality check
            decision, should_retry = self._quality_score(current_text, rewritten)
            
            if decision == "accept":
                return (rewritten, "accepted")
            elif decision == "rewrite" and should_retry:
                current_text = rewritten
                iterations += 1
                continue
            else:
                # Decide to keep or accept based on score
                if overall_score >= 0.60:
                    return (rewritten, "accepted_low_confidence")
                else:
                    return (current_text, "rejected")
        
        # Max iterations reached
        return (current_text, "max_iterations")

```

**Step 5: Commit**

```bash
git add slack_message_bot/rewriter.py && git commit -m "feat: add message rewriter with quality control"
```

---

### Task 5: Create Slack event handler

**Objective:** Build Bolt app that listens for message events and triggers rewriting.

**Files:**
- Create: `slack_message_bot/app.py`

```python
import os
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_message_bot.llm_backend import get_backend, LLMConfig
from slack_message_bot.rewriter import MessageRewriter
from slack_message_bot.config import load_llm_config

class SlackMessageBot:
    """Main Slack bot handler."""
    
    def __init__(self):
        self.config = load_llm_config()
        self.rewriter = MessageRewriter()
        bot_token = os.getenv("SLACK_BOT_TOKEN")
        signing_secret = os.getenv("SLACK_SIGNING_SECRET")
        
        self.app = App(token=bot_token, signing_secret=signing_secret)
        
        # Listen for message events from the logged-in user
        @self.app.event("message")
        def handle_message(event, say, client):
            # Skip if bot sent it or if it's an edit
            if event.get("subtype") in ["bot_message", "message_edit"]:
                return
            
            # Only process messages from the bot user itself
            bot_user_id = client.users_info(user="U0123456789")["user"]["id"]  # Replace or get dynamically
            # Note: You'll need to add environment var for your user ID or detect it
            
            # Fetch thread context
            thread_context = self._fetch_thread_context(event["channel"], event.get("thread_ts", event["ts"]))
            
            # Rewrite
            original_text = event["message"]["text"]
            rewritten, decision = self.rewriter.rewrite(original_text, thread_context)
            
            if rewritten != original_text:
                # Post quality log
                self._log_quality(original_text, rewritten, decision)
                
                # Edit the message with professional rewrite
                try:
                    client.chat_update(
                        channel=event["channel"],
                        ts=event["ts"],
                        text=f"{rewritten}\n\n— edited by professional-bot"
                    )
                except Exception as e:
                    self._log_error(f"Failed to edit message: {e}")
    
    def _fetch_thread_context(self, channel: str, ts: str, max_messages: int = 5) -> str:
        """Fetch recent messages in thread for context."""
        client = App().client
        try:
            response = client.chat_list_replies(
                channel=channel,
                ts=ts,
                limit=min(max_messages, 5)
            )
            messages = response.get("messages", [])
            context = "\n".join([f"@{m['user']}: {m['text']}" for m in messages[:3]])
            return context
        except Exception as e:
            return f"Error fetching context: {e}"
    
    def _log_quality(self, original: str, rewritten: str, decision: str):
        """Log quality decision (can be enhanced with W&B later)."""
        print(f"[Quality] Decision: {decision}")
        print(f"[Original] {original[:100]}...")
        print(f"[Rewritten] {rewritten[:100]}...")
    
    def _log_error(self, error: str):
        """Log errors silently."""
        print(f"[Error] {error}")
    
    def run(self):
        """Start the bot."""
        mode_handler = SocketModeHandler(
            self.app,
            os.getenv("SLACK_APP_TOKEN")
        )
        mode_handler.start()

```

**Step 6: Create main entry point**

```bash
cat > slack_message_bot/main.py << 'EOF'
from slack_message_bot.app import SlackMessageBot

if __name__ == "__main__":
    bot = SlackMessageBot()
    bot.run()
EOF

```

**Step 7: Commit**

```bash
git add slack_message_bot/app.py slack_message_bot/main.py && git commit -m "feat: add Slack event handler"
```

---

### Task 6: Add configuration examples and environment setup

**Files:**
- Create: `config/llm_config.yaml.example`
- Create: `.env.example`
- Create: `README.md`

**Step 1: Create example YAML config**

```bash
cat > config/llm_config.yaml.example << 'EOF'
endpoint: "https://api.openai.com/v1/chat/completions"
api_key: "your-api-key-here"
model: "gpt-4o"
provider: "openai"
EOF
```

**Step 2: Create env example**

```bash
cat > .env.example << 'EOF'
# Slack credentials
SLACK_BOT_TOKEN=xxx
SLACK_SIGNING_SECRET=xxx
SLACK_APP_TOKEN=xxx

# LLM config (can override YAML file)
LLM_API_KEY=your-openai-key
LLM_ENDPOINT=https://api.openai.com/v1/chat/completions
LLM_MODEL=gpt-4o
LLM_PROVIDER=openai
EOF
```

**Step 3: Create README**

Write comprehensive README with:
- Setup instructions
- Environment variable docs
- Running the bot
- Testing instructions

**Step 4: Commit**

```bash
git add config/ .env.example README.md && git commit -m "docs: add configuration examples and docs"
```

---

### Task 7: Add user ID detection and testing utilities

**Objective:** Add automatic user ID detection and simple test commands.

**Files:**
- Modify: `slack_message_bot/app.py` (add user ID detection)
- Create: `tests/test_bot.py` (basic integration tests)
- Create: `tests/test_rewriter.py` (rewriter tests)

**Step 1: Add user ID detection to app.py**

```python
def get_current_user_id(client) -> str:
    """Get the user ID of the authenticated user."""
    info = client.auth_test()
    return info["user_id"]
```

**Step 2: Write tests for rewriter**

```python
# tests/test_rewriter.py
from slack_message_bot.rewriter import MessageRewriter

def test_rewrite_basic():
    rewriter = MessageRewriter()
    original = "hey guys lol omg this is so important omg"
    rewritten, decision = rewriter.rewrite(original)
    assert decision != "rejected"  # Should accept or rewrite

def test_semantic_preservation():
    rewriter = MessageRewriter()
    original = "the meeting is moved to 3pm tomorrow"
    rewritten, decision = rewriter.rewrite(original)
    assert "3pm" in rewritten or "tomorrow" in rewritten  # Preserve key info

def test_conciseness():
    rewriter = MessageRewriter()
    original = "I was just wondering if maybe we could potentially consider rescheduling"
    rewritten, decision = rewriter.rewrite(original)
    assert len(rewritten.split()) < len(original.split())  # Should be shorter
```

**Step 3: Commit all tests**

```bash
git add tests/ && git commit -m "test: add rewriter and bot tests"
```

---

### Task 8: Add logging and monitoring

**Objective:** Add structured logging and optional W&B integration for quality tracking.

**Files:**
- Create: `slack_message_bot/logging_config.py`
- Modify: `slack_message_bot/rewriter.py` (add logging hooks)

**Step 1: Structured logging**

```python
# slack_message_bot/logging_config.py
import logging
import json
from datetime import datetime

def setup_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger
```

**Step 2: Modify rewriter to use logging**

Replace print statements with logger calls.

**Step 3: Commit**

```bash
git add slack_message_bot/logging_config.py slack_message_bot/rewriter.py && git commit -m "feat: add structured logging"
```

---

## Summary of Tasks

1. ✅ Initialize project structure and dependencies
2. ✅ Create LLM configuration manager
3. ✅ Create LLM backend abstraction
4. ✅ Create message rewriter with quality control
5. ✅ Create Slack event handler
6. ✅ Add configuration examples and environment setup
7. ✅ Add user ID detection and testing utilities
8. ✅ Add logging and monitoring

## Running the Bot

1. Set up Slack App:
   - Enable Socket Mode
   - Add bot scopes: `chat:write`, `channels:history`, `chat:write.customize`
   - Install to workspace

2. Configure environment:
```bash
cp .env.example .env
cp config/llm_config.yaml.example config/llm_config.yaml
# Edit .env and llm_config.yaml with your credentials
```

3. Run:
```bash
python -m slack_message_bot
```

---

**Plan complete. Ready to execute using subagent-driven-development — I'll dispatch a fresh subagent per task with two-stage review (spec compliance then code quality). Shall I proceed?**
