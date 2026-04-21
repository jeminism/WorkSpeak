import re
import pytest
from slack_message_bot.rewriter import MessageRewriter

def test_post_remove_metadata():
    rewriter = MessageRewriter()
    test_text = "The rewritten text is great with 256 tokens used, an estimated cost of $0.00128, a quality score of 0.0, 1 iteration, and a successful outcome"
    cleaned = rewriter._remove_metadata(test_text)
    assert "tokens used" not in cleaned
    assert "estimated cost" not in cleaned
    assert "quality score" not in cleaned
    assert "iteration" not in cleaned

def test_post_remove_artifacts_explanations():
    rewriter = MessageRewriter()
    test_text = """Here is the rewritten text:
The actual message: Hello there is the content.
### Summary
Reasoning: just cleanup text."""
    cleaned = rewriter._remove_artifacts(test_text)
    assert "Here is the rewritten text" not in cleaned
    # The actual message content should remain
    assert "Hello there" in cleaned
    assert "### Summary" not in cleaned
    assert "Reasoning" not in cleaned.lower()

def test_post_remove_numbered_lists():
    rewriter = MessageRewriter()
    test_text = """1. First point
2. Second point
The actual message"""
    cleaned = rewriter._remove_artifacts(test_text)
    lines = cleaned.split('\n')
    assert not any(line.startswith('1.') or line.startswith('2.') for line in lines)

def test_post_process_combined():
    rewriter = MessageRewriter()
    test_text = """Here is the rewritten text:
256 tokens used with cost.
Hello there is the message."""
    cleaned = rewriter._post_process(test_text)
    # Metadata and intro/outro should be removed
    assert "Here is the rewritten text" not in cleaned
    # Remaining text should be clean
    assert "Hello there" in cleaned

def test_tone_check():
    rewriter = MessageRewriter()
    
    # No violations
    assert rewriter._check_tone("Hello, I wanted to confirm the meeting") == 1.0
    
    # One violation
    score = rewriter._check_tone("lol, omg meeting is important")
    assert score < 1.0
    
    # Multiple violations
    score = rewriter._check_tone("lol omg wtf tbh")
    assert score < 0.5

def test_conciseness_check():
    rewriter = MessageRewriter()
    
    # Same length
    score = rewriter._check_conciseness("hello world", "good morning")
    assert score == 1.0
    
    # Shorter is okay
    score = rewriter._check_conciseness("hello world this is a long message", "hi")
    assert score >= 0.5
    
    # Much shorter is penalized
    score = rewriter._check_conciseness("hello world this is a long message", "ok")
    assert score < 1.0
    
    # Much longer is penalized
    score = rewriter._check_conciseness("hi", "hello world this is a much longer message than the original")
    assert score < 1.0

def test_quality_score_high():
    rewriter = MessageRewriter()
    original = "hey guys this meeting is super important"
    rewritten = "Hello team, just confirming an important meeting"
    decision, retry, score = rewriter._quality_score(original, rewritten)
    assert decision in ["accept", "rewrite"]  # Should pass basic quality check
