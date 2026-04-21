#!/usr/bin/env python3
"""
WorkSpeak CLI - Interactive Message Rewriter Testing

Usage:
    python -m slack_message_bot.cli_rewriter
"""

import sys
import os
import re

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .llm_backend import get_backend
from .rewriter import MessageRewriter, HAS_EMBEDDINGS
from .logging_config import get_logger
from .config import load_llm_config

logger = get_logger(__name__)

def get_input(prompt=""):
    """Get input with custom prompt. Returns None on Ctrl+C."""
    try:
        if prompt:
            print(prompt, end="", flush=True)
        return input()
    except EOFError:
        return None
    except KeyboardInterrupt:
        print("\n")
        return None

def display_summary(original: str, rewritten: str, decision: str):
    """Display rewrite summary with formatting."""
    print("\n" + "=" * 60)
    print(f"DECISION: {decision.upper()}")
    print("-" * 60)
    print()
    print("ORIGINAL:")
    print("-" * 20)
    print(original)
    print()
    print("REWRTITTEN:")
    print("-" * 20)
    if rewritten == original:
        print("(no change)")
    else:
        print(rewritten)
    print("=" * 60 + "\n")

def main():
    """CLI interactive rewriter."""
    print("=" * 60)
    print("WorkSpeak CLI - Interactive Message Rewriter")
    print("=" * 60)
    print()
    print("Instructions:")
    print("  - Type a message and press Enter to trigger rewrite")
    print("  - Use 'q' to quit")
    print("  - Use 'c=<text>' to set custom thread context")
    print("  - Use 'l' to toggle logging verbosity")
    print()
    print("-" * 60)
    print()
    
    # Initialize components
    try:
        config = load_llm_config()
        logger.info(f"Loaded LLM config: {config.provider}/{config.model}")
    except ValueError as e:
        logger.error(f"Config error: {e}")
        logger.info("Using test mode (no LLM connection)")
        config = None
    
    rewriter = MessageRewriter()
    
    # Session state
    thread_context = ""
    verbose = False
    
    print_history = []
    
    while True:
        line = get_input("> ")
        
        if line is None:
            print("\nGoodbye!")
            break
        
        line = line.strip()
        
        # Commands
        if line.lower() == 'q':
            print("\nGoodbye!")
            break
        
        elif line.lower() == 'c':
            thread_context = ""
            print("Cleared thread context.")
            continue
        
        elif line.startswith('c='):
            thread_context = line[2:]
            print(f"Set thread context: {thread_context[:50]}...")
            continue
        
        elif line.lower() == 'l':
            verbose = not verbose
            logger.info(f"Logging verbosity: {'ON' if verbose else 'OFF'}")
            continue
        
        elif line.lower() == 'h' or line.lower() == 'help':
            print("""
Commands:
  [any text]   Submit message for rewriting
  c=<text>     Set thread context for this message
  c            Clear thread context
  l            Toggle logging verbosity
  h            Show this help
  q            Quit
""")
            continue
        
        # Empty input
        if not line:
            print("(empty input, try again)")
            continue
        
        # Submit message for rewriting
        logger.debug(f"Processing message: {line[:50]}...")
        
        if config:
            rewritten, decision = rewriter.rewrite(
                original_text=line,
                thread_context=thread_context,
                config=config
            )
        else:
            # Test mode: just return original with decision
            rewritten = line
            decision = "test_mode_no_llm_config"
            logger.info("Test mode - no LLM connection. Showing original text.")
        
        print_history.append({
            "original": line,
            "rewritten": rewritten,
            "decision": decision,
            "thread_context": thread_context
        })
        
        display_summary(line, rewritten, decision)
        
        # Show context if used
        if thread_context:
            print("THREAD CONTEXT USED:")
            print("-" * 20)
            print(thread_context)
            print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted. Goodbye!")
        sys.exit(0)
