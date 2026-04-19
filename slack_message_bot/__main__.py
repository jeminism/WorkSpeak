"""Main entry point for WorkSpeak Bot."""
import os
import sys
import argparse

from slack_message_bot.app import SlackMessageBot
from slack_message_bot.logging_config import configure_logging, get_logger
from slack_message_bot.cli_rewriter import main as cli_rewriter_main
from slack_message_bot.batch_evaluator import main as batch_evaluator_main

logger = get_logger(__name__)

def main():
    """Main entry point with CLI argument parsing."""
    parser = argparse.ArgumentParser(
        description="WorkSpeak Bot - Slack message rewriting service"
    )
    parser.add_argument(
        "--mode",
        choices=["slack", "cli", "batch"],
        default="slack",
        help="运行模式：slack (默认), cli, 或 batch"
    )
    parser.add_argument(
        "--input",
        help="Input file for batch mode"
    )
    parser.add_argument(
        "--context",
        help="Thread context for batch/cli mode"
    )
    
    args = parser.parse_args()
    
    log_file = os.getenv("WORKSPEAK_LOG_FILE", "logs/workSpeak.log")
    configure_logging(
        log_level=os.getenv("WORKSPEAK_LOG_LEVEL", "INFO"),
        log_file=log_file
    )
    
    if args.mode == "slack":
        # Slack bot server mode
        logger.info("Starting WorkSpeak Bot (Slack Server Mode)...")
        logger.info("Checking configuration...")
        
        try:
            bot = SlackMessageBot()
            logger.info("Bot initialized successfully")
            bot.run()
        except ValueError as e:
            logger.error(f"Configuration error: {e}")
            logger.error("Make sure to set SLACK_BOT_TOKEN and LLM_API_KEY/LLM_ENDPOINT")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Failed to start bot: {e}")
            import traceback
            logger.error(traceback.format_exc())
            sys.exit(1)
    
    elif args.mode == "cli":
        # CLI interactive mode
        cli_rewriter_main()
    
    elif args.mode == "batch":
        # Batch evaluator mode
        if not args.input:
            parser.error("--input is required for batch mode")
        # Pass extra args for input file and context
        batch_input = sys.argv[sys.argv.index('--input') + 1] if '--input' in sys.argv else None
        batch_context = args.context or sys.argv[sys.argv.index('--context') + 1] if '--context' in sys.argv and '--context' in sys.argv else ""
        
        # Reconstruct sys.argv for batch_evaluator
        original_argv = sys.argv
        sys.argv = [sys.argv[0]] + [batch_input] + ([batch_context] if batch_context else [])
        batch_evaluator_main()
        sys.argv = original_argv

if __name__ == "__main__":
    main()
