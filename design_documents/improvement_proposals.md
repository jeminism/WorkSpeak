# WorkSpeak Improvement Proposals

**Date:** April 22, 2026  
**Status:** Proposed architecture for addressing limitations

---

## Current Implementation Summary

### Architecture Flow
```
User Message → Bolt Event Handler → Thread Context Fetch → MessageRewriter → LLM Backend → chatUpdate
```

### Key Components
- `app.py`: Event handler that listens for messages and edits them via `chat_update()`
- `rewriter.py`: Multi-tier quality control (semantic similarity, conciseness, tone)
- `llm_backend.py`: OpenAI-compatible HTTP client (currently uses external API endpoint)
- Embeddings: `all-MiniLM-L6-v2` pre-loaded in `rewriter.py` for semantic similarity checks

### Known Issues
1. **Missing reversal flow:** Users cannot easily revert edited messages
2. **Network latency:** HTTP requests to LLM API cause visible lag (original message visible for 2-5 seconds)

---

## Problem 1: Missing Reversal Flow

### Current State Analysis
Once a message is edited, there is no obvious way for users to revert it. Slack's UI shows "(edited)" but users must manually remember the original text.

### Proposed Solutions

#### Option A: Add "Undo" Button (Recommended)
Add an interactive "Undo" button via Slack Block Actions that appears alongside edited messages.

**Features:**
- Button appears only on messages that have been edited by WorkSpeak
- Clicking triggers a revert action
- Bot calls `chat_update()` with the original message text
- Logs the reversal for analytics

**Implementation Notes:**
- Store original message text in temporary cache (in-memory dict or Redis, keyed by `ts` + `channel`)
- Add new Bolt action handler for button clicks
- Need to add `block_id` and interactive elements to message blocks

**Message Block Example:**
```json
{
  "type": "section",
  "text": {"type": "mrkdwn", "text": "🚀 Sending out the weekly report now"},
  "accessory": {
    "type": "button",
    "text": {"type": "plain_text", "text": "Undo"},
    "value": "undo",
    "action_id": "workspeaks-undo"
  }
}
```

#### Option B: Slash Command for Manual Undo
Create a `/undo` slash command that reverts recent edits by the user.

**Commands:**
- `/undo [ts]` - revert specific message by timestamp
- `/undo last` - revert most recent edit
- `/undo history` - show list of recent edits with undo options

#### Option C: Auto-Undo Feature
Add toggle commands to temporarily disable edits:
- `/workspeaks pause` - stop editing messages temporarily
- `/workspeaks resume` - resume editing
- `/workspeaks status` - show current configuration

---

## Problem 2: Network Latency

### Current State Analysis
Bot makes HTTP request to LLM API endpoint. Latency includes:
1. Network round-trip to API endpoint
2. API processing time
3. Response parsing

No local model is currently being used for the rewriting LLM (only for semantic similarity quality check).

### Proposed Solutions

#### Option A: Async Processing + Temporary Status Message (Recommended)
Process rewrites asynchronously without blocking the event handler acknowledgment. Display temporary status to indicate processing is happening.

**Implementation:**
1. Run rewrite in background thread or async task
2. Immediately acknowledge receipt to Slack
3. Optionally show loading indicator: "🔄 WorkSpeak is rewriting..."
4. Replace with final edited message when complete

**Benefits:**
- Eliminates perceived lag (user doesn't wait during rewrite)
- Background task can be retried on failure
- No need for complex caching initially

**Code Pattern:**
```python
async def perform_rewrite(event):
    rewritten, decision = self.rewriter.rewrite(original_text, thread_context, config)
    if rewritten != original_text:
        client.chat_update(channel=event["channel"], ts=event["ts"], blocks=blocks)
        logger.info(f"Successfully edited message ts={event['ts']}")
```

Event handler then just schedules the async task:
```python
asyncio.create_task(perform_rewrite(event))
```

#### Option B: In-Memory LRU Cache Layer
Cache recent original message → rewritten pairs to prevent redundant API calls.

**Design:**
- Key: SHA256(original_text) for exact matches
- Key: Semantic embedding hash for near-duplicates (fuzzy matching)
- TTL: 24 hours
- Max size: 10,000 entries (configurable)

**Benefits:**
- Reduces API calls by 30-60% for duplicate messages
- Instant response for cached messages
- Can still fall back to LLM for new content

**Implementation:**
```python
from functools import lru_cache
import hashlib

@lru_cache(maxsize=10000)
def get_rewrite_cache_key(text):
    return hashlib.sha256(text.encode()).hexdigest()
```

#### Option C: Faster LLM Endpoint
Evaluate switching to a faster provider or model:

| Provider/Model | Typical Latency | Cost |
|---------------|-----------------|------|
| Hugging Face Inference (Llama 3 8B) | 2-5s (cold) / 500ms | Free / $ |
| Groq (Llama 3 8B) | 50-200ms | Low |
| Fireworks (Llama 3) | 150-300ms | Low |
| OpenAI gpt-4o | 1-2s | Medium |
| OpenAI gpt-4o-mini | 300-500ms | Low |

**Recommendation:** Switch to Groq or Fireworks for 10-50x speed improvement with similar model quality.

#### Option D: Hybrid Local + Cloud Approach (Advanced)
Use local models for simple rewrites, only fall back to LLM API when needed.

**Strategy:**
1. Local sentence-transformer already pre-loaded for similarity check
2. Implement rule-based rewrites for common patterns (typos, grammar fixes)
3. Only call LLM API if quality threshold isn't met

**Implementation:**
- Rule-based pre-processor (spelling, punctuation, common phrases)
- Quality check before calling LLM API
- Cache local model results

**Tradeoff:** More complex implementation but 60-80% reduction in API calls

---

## Recommended Combined Implementation Plan

### Phase 1: Quick Wins (1-3 hours)
**Priority:** High impact, low complexity

1. **Add temporary status message** during rewrite
   - Edit: Show "🔄 WorkSpeak is editing your message..."
   - Replace with final content when complete
2. **Switch to async processing**
   - Remove blocking wait for LLM response
   - Fire and forget event handler
3. **Pre-load embeddings at startup** (already exists, verify)

### Phase 2: Feature Parity (2-4 hours)
**Priority:** User experience improvements

1. **Add "Undo" button** with Bolt Block Actions
2. **Implement in-memory message cache** for undo storage
3. **Add `/pause` and `/undo` slash commands**

### Phase 3: Performance Optimization (4-8 hours)
**Priority:** Long-term scalability

1. **Implement LRU cache for rewrite results**
2. **Add metrics/logging for latency tracking**
3. **Evaluate and potentially switch LLM endpoint** (Groq/Fireworks)
4. **Add fallback to local model when API is slow**

---

## Architecture Diagram (Proposed v2.0)

```
┌─────────────────────────────────────────────────────────────────┐
│                      WorkSpeak Bot v2.0                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Slack Event → Handler ──→ Async Task Queue                    │
│        ↓                                                       │
│  [Cache Original Msg]    │                                   │
│        ↓                 ↓                                    │
│  Temp Store (Key: ts)  LLM Pipeline                          │
│        │               ┌──────────────┐                       │
│        │               │ Pre-loaded   │                       │
│        │               │ Embeddings   │                       │
│        │               └──────────────┘                       │
│        ↓                 ↓                                    │
│  Cache Rewrite Result  LLM API (Cached/Fast Endpoint)         │
│        │                 │                                    │
│        └────┬────────────┘                                    │
│             ↓                                                 │
│        chat_update() ──→ Add "Undo" Button                   │
│             ↓                                                 │
│        Slack Display ✓                                       │
│                                                                 │
│  User Action → /undo or Button Click → Revert via chat_update │
└─────────────────────────────────────────────────────────────────┘
```

---

## Implementation Checklist

### Undo Button
- [ ] Add `block_id` and interactive elements to `build_message_blocks()`
- [ ] Create Bolt action handler for block action events
- [ ] Store original messages in temporary cache
- [ ] Implement `chat_update()` for revert
- [ ] Add logging for undo events

### Async Processing
- [ ] Refactor `handle_message()` to use async task
- [ ] Remove blocking waits from event handler
- [ ] Add error handling for failed background tasks
- [ ] Add temporary status indicator (optional)

### Caching
- [ ] Implement LRU cache for rewrite results
- [ ] Add cache key generation function
- [ ] Set TTL expiration
- [ ] Add cache hit/miss metrics

### Performance
- [ ] Measure current latency breakdown
- [ ] Test alternative endpoints (Groq, Fireworks)
- [ ] Implement fallback mechanism
- [ ] Add latency metrics logging

---

## Monitoring & Metrics

### Track These Metrics
- Message edit latency (total time from send to edit)
- LLM API call latency
- Cache hit rate
- Undo button usage
- Error rate by type
- Daily message volume

### Logging Format
```
[WORKSPEAK] ts=123456 channel=C000 action=edit latency=1.2s decision=accept
[WORKSPEAK] ts=123456 action=undo user=U000 original=...
[WORKSPEAK] latencies_api=0.8s latency_total=1.2s cache_hit=false
```

---

## Next Steps

1. Confirm which solution set you want to implement
2. Choose priority order (Undo vs Performance vs Both)
3. Estimate implementation time
4. Begin development

**Recommended starting point:** Phase 1 (Async + Temporary Status) for immediate perceived improvement, then Phase 2 (Undo Button) for user experience.

---

*Document created: April 22, 2026*  
*For future reference and implementation planning*
