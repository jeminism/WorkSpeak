#!/usr/bin/env python3
"""
WorkSpeak Batch Evaluator - Process text files through the rewriter pipeline

Usage:
    python -m slack_message_bot.batch_evaluator <input_file>
    
Input file formats supported:
    - Plain text (.txt): One message per line
    - JSON (.json): Array of strings or {"messages": [...]}
    - CSV (.csv): Single column of messages (first column)
    - YAML (.yaml, .yml): Array of strings or {"messages": [...]}

Output:
    - Prints each rewrite to terminal
    - Creates output file: <input_name>_evaluated.txt
"""

import sys
from pathlib import Path
import json
import csv
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

from .llm_backend import get_backend
from .rewriter import MessageRewriter
from .logging_config import get_logger, configure_logging
from .config import load_llm_config

logger = get_logger(__name__)

# ============== File Parsers ==============

def parse_text_file(filepath: str) -> list:
    """Parse plain text file (one message per line)."""
    messages = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):  # Skip comments
                    messages.append(line)
    except Exception as e:
        logger.error(f"Error reading text file: {e}")
    return messages

def parse_json_file(filepath: str) -> list:
    """Parse JSON file (array or dict with 'messages' key)."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if isinstance(data, list):
            return [str(item) for item in data]
        elif isinstance(data, dict):
            if 'messages' in data:
                return [str(item) for item in data['messages']]
            else:
                # Try first list value
                for key, value in data.items():
                    if isinstance(value, list):
                        return [str(item) for item in value]
    except Exception as e:
        logger.error(f"Error parsing JSON file: {e}")
    return []

def parse_csv_file(filepath: str) -> list:
    """Parse CSV file (first column)."""
    messages = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if row and row[0].strip():
                    messages.append(row[0].strip())
    except Exception as e:
        logger.error(f"Error parsing CSV file: {e}")
    return messages

def parse_yaml_file(filepath: str) -> list:
    """Parse YAML file (array or dict with 'messages' key)."""
    if not HAS_YAML:
        logger.error("PyYAML not installed. Install with: pip install pyyaml")
        return []
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        if isinstance(data, list):
            return [str(item) for item in data]
        elif isinstance(data, dict):
            if 'messages' in data:
                return [str(item) for item in data['messages']]
            else:
                # Try first list value
                for key, value in data.items():
                    if isinstance(value, list):
                        return [str(item) for item in value]
    except Exception as e:
        logger.error(f"Error parsing YAML file: {e}")
    return []

def parse_file(filepath: str) -> list:
    """Parse file based on extension."""
    ext = Path(filepath).suffix.lower()
    
    parsers = {
        '.txt': parse_text_file,
        '.json': parse_json_file,
        '.csv': parse_csv_file,
        '.yaml': parse_yaml_file,
        '.yml': parse_yaml_file,
    }
    
    parser = parsers.get(ext)
    if parser:
        return parser(filepath)
    else:
        # Fallback: try as text file
        logger.warning(f"Unrecognized extension {ext}, trying as text file")
        return parse_text_file(filepath)

# ============== Output Formatting ==============

class BatchEvaluator:
    """Batch evaluation helper class."""
    
    def __init__(self, rewriter: MessageRewriter, config=None):
        self.rewriter = rewriter
        self.config = config
        self.results = []
    
    def evaluate(self, message: str, thread_context: str = "") -> dict:
        """Evaluate a single message."""
        original_len = len(message)
        original_words = len(message.split())
        
        rewritten, decision = self.rewriter.rewrite(
            original_text=message,
            thread_context=thread_context,
            config=self.config
        )
        
        rewritten_len = len(rewritten)
        rewritten_words = len(rewritten.split())
        
        # Calculate metrics
        if original_words > 0:
            word_ratio = rewritten_words / original_words
            char_ratio = rewritten_len / original_len
        else:
            word_ratio = 1.0
            char_ratio = 1.0
        
        result = {
            "original": message,
            "rewritten": rewritten,
            "decision": decision,
            "metrics": {
                "original_length": original_len,
                "rewritten_length": rewritten_len,
                "original_words": original_words,
                "rewritten_words": rewritten_words,
                "word_ratio": word_ratio,
                "char_ratio": char_ratio,
            },
            "timestamp": 0  # Will be set by caller
        }
        
        self.results.append(result)
        return result
    
    def print_results(self, show_all: bool = True):
        """Print all results to terminal."""
        print("\n" + "=" * 80)
        print("BATCH EVALUATION RESULTS")
        print("=" * 80)
        print()
        
        for i, result in enumerate(self.results, 1):
            print(f"--- Message {i} ---")
            print()
            print(f"DECISION: {result['decision']}")
            print()
            
            if show_all:
                print("ORIGINAL:")
                print("-" * 40)
                print(result['original'])
                print()
                print("REWRTITTEN:")
                print("-" * 40)
                if result['rewritten'] == result['original']:
                    print("(no change)")
                else:
                    print(result['rewritten'])
                print()
            
            print(f"METRICS:")
            print(f"  Original length:  {result['metrics']['original_length']} chars, {result['metrics']['original_words']} words")
            print(f"  Rewritten length: {result['metrics']['rewritten_length']} chars, {result['metrics']['rewritten_words']} words")
            print(f"  Word ratio:       {result['metrics']['word_ratio']:.2f}")
            print(f"  Char ratio:       {result['metrics']['char_ratio']:.2f}")
            print()
            print()
        
        # Summary
        print("=" * 80)
        print("SUMMARY")
        print("=" * 80)
        
        total = len(self.results)
        accepted = sum(1 for r in self.results if 'accepted' in r['decision'].lower())
        rejected = sum(1 for r in self.results if 'rejected' in r['decision'].lower())
        no_change = sum(1 for r in self.results if r['original'] == r['rewritten'])
        
        print(f"Total messages:   {total}")
        print(f"Accepted:         {accepted} ({accepted/total*100:.1f}%)")
        print(f"Rejected/Modified: {rejected}")
        print(f"No change:        {no_change} ({no_change/total*100:.1f}%)")
        print()
        
        if total > 0:
            avg_words = sum(r['metrics']['rewritten_words'] for r in self.results) / total
            print(f"Average rewritten: {avg_words:.1f} words per message")
            print()

# ============== Main Entry Point ==============

def main():
    """Main batch evaluator."""
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nError: Missing input file argument")
        sys.exit(1)
    
    input_file = sys.argv[1]
    
    if not os.path.exists(input_file):
        logger.error(f"Input file not found: {input_file}")
        sys.exit(1)
    
    # Get optional thread context from args
    thread_context = sys.argv[2] if len(sys.argv) > 2 else ""
    
    # Configure logging
    configure_logging(log_level="INFO")
    
    print("=" * 80)
    print("WorkSpeak Batch Evaluator")
    print("=" * 80)
    print()
    print(f"Input file: {input_file}")
    print(f"Thread context: '{thread_context}'")
    print()
    
    # Parse input file
    logger.info("Parsing input file...")
    messages = parse_file(input_file)
    
    if not messages:
        logger.error("No messages found in input file")
        sys.exit(1)
    
    print(f"Found {len(messages)} messages")
    print()
    
    # Load config
    try:
        config = load_llm_config()
        logger.info(f"Loaded LLM config: {config.provider}/{config.model}")
    except ValueError as e:
        logger.warning(f"Config error: {e}")
        logger.info("Using test mode - post-processing only (no LLM)")
        config = None
    
    # Initialize rewriter
    rewriter = MessageRewriter()
    evaluator = BatchEvaluator(rewriter, config)
    
    # Process messages
    for i, message in enumerate(messages, 1):
        print(f"Processing {i}/{len(messages)}...")
        print("-" * 40)
        result = evaluator.evaluate(message, thread_context)
        
        print(f"Decision: {result['decision']}")
        print()
    
    # Print all results
    evaluator.print_results()
    
    # Save output
    output_path = Path(input_file).with_suffix("") / f"{Path(input_file).stem}_evaluated.txt"
    output_file = f"{Path(input_file).stem}_evaluated.txt"
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            for i, result in enumerate(evaluator.results, 1):
                f.write(f"{'='*60}\n")
                f.write(f"Message {i}\n")
                f.write(f"Decision: {result['decision']}\n")
                f.write(f"{'='*60}\n\n")
                f.write(f"Original:\n{result['original']}\n\n")
                f.write(f"Rewritten:\n{result['rewritten']}\n\n")
                f.write(f"Metrics:\n")
                for k, v in result['metrics'].items():
                    f.write(f"  {k}: {v}\n")
                f.write("\n")
        
        logger.info(f"Results saved to: {output_file}")
    except Exception as e:
        logger.error(f"Failed to save results: {e}")
    
    print()
    print("Batch evaluation complete!")
    sys.exit(0)

if __name__ == "__main__":
    main()
