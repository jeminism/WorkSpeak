"""
WorkSpeak Client Application

Entry point for starting the client-side rewriting agent.
"""

import logging
import sys
import argparse
from pathlib import Path

from .core import MessageInterceptor, ClientRewriter, MessagePreview
from .config import load_client_config, create_default_config
from .interfaces import SystemTrayIcon

logger = logging.getLogger(__name__)


def setup_logging(config):
    """Setup logging configuration"""
    Path("logs").mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=getattr(logging, config.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(config.log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )


def main():
    """Main application entry point"""
    parser = argparse.ArgumentParser(
        description="WorkSpeak Client - Message rewriting for Slack"
    )
    parser.add_argument(
        "--config",
        help="Path to configuration file"
    )
    parser.add_argument(
        "--create-config",
        action="store_true",
        help="Create default configuration file"
    )
    parser.add_argument(
        "--no-tray",
        action="store_true",
        help="Disable system tray icon"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run in test mode"
    )
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_client_config(args.config)
    setup_logging(config)
    
    logger.info("WorkSpeak Client starting...")
    
    # Handle config creation
    if args.create_config:
        create_default_config(args.config)
        logger.info("Configuration created. Please edit and restart.")
        sys.exit(0)
    
    # Test mode
    if args.test:
        logger.info("Running in test mode")
        
        # Test configuration
        logger.info(f"LLM Endpoint: {config.llm.endpoint}")
        logger.info(f"Auto-rewrite: {config.auto_rewrite}")
        logger.info(f"Preview enabled: {config.preview_enabled}")
        
        # Test interceptor
        interceptor = MessageInterceptor(
            on_message_detected=lambda m: logger.info(f"Message detected: {m.text[:50]}..."),
            on_send_detected=lambda m: logger.info(f"Send detected"),
            poll_interval=0.5
        )
        
        logger.info("Interceptor initialized (not started in test mode)")
        
        # Test rewriter
        rewriter = ClientRewriter()
        test_text = "hey guys lol omg meeting is super important"
        result = rewriter.rewrite(test_text, "channel")
        logger.info(f"Rewrite test:")
        logger.info(f"  Original: {test_text}")
        logger.info(f"  Rewritten: {result.rewritten_text}")
        logger.info(f"  Quality: {result.quality_score}")
        logger.info(f"  Decision: {result.decision}")
        
        sys.exit(0)
    
    # Main application
    try:
        # Create components
        interceptor = MessageInterceptor(
            on_message_detected=handle_message_detected,
            on_send_detected=handle_send_detected,
            poll_interval=0.5
        )
        
        rewriter = ClientRewriter()
        preview = MessagePreview()
        
        # Create tray icon
        if not args.no_tray:
            tray = SystemTrayIcon(
                on_toggle_rewrite=lambda enabled: config.set_auto_rewrite(enabled),
                on_quit=lambda: stop_application(interceptor, tray)
            )
            tray.create()
        else:
            tray = None
        
        # Start interceptor
        interceptor.start()
        logger.info("Interceptor started")
        
        # Start tray loop (if enabled)
        if tray:
            logger.info("System tray running (press Ctrl+C to quit)")
            tray.run()
        else:
            logger.info("Run in background (no tray)")
            while True:
                import time
                time.sleep(1)
                
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        stop_application(interceptor, tray)
    
    logger.info("WorkSpeak Client stopped")


def handle_message_detected(message_state):
    """Handle detected message composition"""
    logger.debug(f"Message detected in {message_state.channel_type}: {message_state.text[:50]}...")
    
    # Rewrite message
    result = rewriter.rewrite(message_state.text, message_state.channel_type)
    
    logger.info(f"Rewrite result: decision={result.decision}, quality={result.quality_score}")
    
    # Check if rewrite should be applied
    if rewriter.should_apply_rewrite(result.decision):
        # Apply rewrite to input field
        if rewriter.hook.inject_text("", result.rewritten_text):
            logger.info("Rewrite applied successfully")
        else:
            logger.warning("Failed to apply rewrite")


def handle_send_detected(message_state):
    """Handle detected message send"""
    logger.info(f"Message sent in {message_state.channel_type}")


def stop_application(interceptor, tray):
    """Stop application gracefully"""
    if interceptor:
        interceptor.stop()
        logger.info("Interceptor stopped")
    
    if tray:
        tray.stop()
        logger.info("Tray stopped")
    
    logger.info("Application shutdown complete")


if __name__ == "__main__":
    main()
