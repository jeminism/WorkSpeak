"""Main entry point for WorkSpeak Bot."""
import os
import sys
from slack_message_bot.app import SlackMessageBot
from slack_message_bot.logging_config import configure_logging, get_logger

logger = get_logger(__name__)

def main():
    """Main entry point."""
    log_file = os.getenv("WORKSPEAK_LOG_FILE", "logs/workSpeak.log")
    configure_logging(
        log_level=os.getenv("WORKSPEAK_LOG_LEVEL", "INFO"),
        log_file=log_file
    )
    
    logger.info("Starting WorkSpeak Bot...")
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

if __name__ == "__main__":
    main()
