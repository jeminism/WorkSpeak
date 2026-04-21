# WorkSpeak Bot - Functional Evaluation Scripts

## Overview

Two additional scripts have been added for manual testing and evaluation of the rewriter pipeline:

### 1. CLI Interactive Rewriter (`cli_rewriter.py`)
An interactive command-line tool that triggers the rewriter pipeline on Enter keypress.

### 2. Batch Evaluator (`batch_evaluator.py`)
Reads messages from a text file (in various formats) and processes them sequentially.

---

## Script 1: CLI Interactive Rewriter

### Usage

```bash
# From the project root:
python -m slack_message_bot.cli_rewriter

# Or run directly:
python slack_message_bot/cli_rewriter.py
```

### Features

- **Interactive**: Type any message and press Enter to trigger rewrite
- **Real-time feedback**: See original vs rewritten with quality decision
- **Thread context support**: Set context per message or globally
- **Logging control**: Toggle verbosity with `l` command
- **Help**: Type `h` for command reference

### Commands

| Command | Description |
|---------|-------------|
| `[any text]` | Submit message for rewriting (Enter = trigger) |
| `c=<text>` | Set thread context for next message |
| `c` | Clear thread context |
| `l` | Toggle logging verbosity |
| `h` / `help` | Show help |
| `q` | Quit |

### Example Session

```
> This meeting is super important omg lol
============================================================
DECISION: ACCEPTED (score: 0.87)
------------------------------------------------------------

ORIGINAL:
--------------------
This meeting is super important omg lol

REWRTITTEN:
--------------------
This meeting is very important.

============================================================

> c=Previous discussion about Q4 planning
c=Previous discussion about Q4 planning
Set thread context: Previous discussion about Q4 planning...

> Can we potentially reschedule the call?
(decision with thread context applied...)
```

### Testing Without LLM

The CLI works in "test mode" when no LLM config is provided - it demonstrates the post-processing pipeline only.

---

## Script 2: Batch Evaluator

### Usage

```bash
# Basic usage:
python -m slack_message_bot.batch_evaluator <input_file>

# With thread context:
python -m slack_message_bot.batch_evaluator <input_file> "<context>"

# Via CLI:
python -m slack_message_bot --mode batch --input messages.txt --context "quarterly planning"
```

### Supported Input Formats

#### Plain Text (.txt)
```
Message 1 here
Message 2 here
Message 3 here
```

#### JSON (.json)
```json
{
  "messages": [
    "Message 1",
    "Message 2",
    "Message 3"
  ]
}
```

or as simple array:
```json
["Message 1", "Message 2", "Message 3"]
```

#### CSV (.csv)
```csv
Message 1
Message 2
Message 3
```

#### YAML (.yaml, .yml)
```yaml
- Message 1
- Message 2
- Message 3
```

or with keys:
```yaml
messages:
  - Message 1
  - Message 2
```

### Output

- **Terminal**: Full evaluation results with metrics
- **File**: `<input_name>_evaluated.txt` with structured results

### Evaluation Metrics

For each message, the evaluator tracks:
- Decision (accepted/rejected/no change)
- Character count (original vs rewritten)
- Word count (original vs rewritten)
- Word ratio (rewritten/original)
- Character ratio (rewritten/original)

### Example Usage

```bash
# Evaluate sample messages
python -m slack_message_bot.batch_evaluator sample_messages.txt

# With thread context
python -m slack_message_bot.batch_evaluator messages.json "Context: Q4 planning meeting"

# Via CLI interface
python -m slack_message_bot --mode batch --input data/messages.csv --context "team sync"
```

### Sample Output

```
--- Message 1 ---

DECISION: ACCEPTED

ORIGINAL:
Hey this meeting moved to 3pm

REWRTITTEN:
The meeting has been rescheduled to 3pm.

METRICS:
  Original length:  30 chars, 6 words
  Rewritten length: 36 chars, 7 words
  Word ratio:       1.17
  Char ratio:       1.20
```

---

## Combined Usage

You can use these scripts together for comprehensive testing:

1. **CLI**: Test real-time rewrites with custom contexts
2. **Batch**: Process large datasets and compare results
3. **Slack**: Deploy the actual bot for production use

### Workflow Example

```bash
# 1. Test individual messages interactively
python -m slack_message_bot.cli_rewriter

# 2. Create sample file with various message types
# (edit sample_messages.txt)

# 3. Run batch evaluation
python -m slack_message_bot.batch_evaluator sample_messages.txt

# 4. Review results and refine prompts/config

# 5. Deploy to Slack for real-world testing
python -m slack_message_bot
```

---

## Requirements

Both scripts use the same dependencies as the main bot:
- `slack_bolt` (for CLI integration)
- `requests` (for LLM API calls)
- `numpy` (for quality metrics)
- `sentence-transformers` (optional, for embedding similarity)
- `pyyaml` (required for YAML input files)

Install if missing:
```bash
pip install pyyaml sentence-transformers
```

---

## Notes

1. **Both scripts exit cleanly** - No lingering processes
2. **Batch evaluator is one-way** - Reads, processes, prints, exits
3. **CLI is interactive** - Use `q` to quit or `Ctrl+C` for interrupt
4. **Test mode enabled** - Works without LLM connection (demo post-processing)
5. **Thread context** - Can be set per-message (CLI) or globally (batch)
