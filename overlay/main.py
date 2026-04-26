#!/usr/bin/env python3
"""
WorkSpeak CDP Overlay Main Entry Point
Starts the Chrome DevTools Protocol-based Slack input monitor.
"""

import asyncio
import argparse
import logging
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from overlay.devtools_client import DevToolsConnection
from overlay.input_monitor import InputMonitor
from overlay.worker import RewriteWorker
from overlay.overlay_ui import OverlayUI
from overlay.wrapper import SlackWrapperGenerator
from core.config import load_llm_config, validate_config
from core.logging_config import setup_logging


async def main():
    """Main entry point for the CDP overlay."""
    
    # Parse arguments
    parser = argparse.ArgumentParser(
        description="WorkSpeak CDP Overlay - Chrome DevTools Protocol-based Slack input manipulation"
    )
    parser.add_argument(
        "--cdp-host",
        default="localhost",
        help="CDP host (default: localhost)"
    )
    parser.add_argument(
        "--cdp-port",
        type=int,
        default=9229,
        help="CDP port (default: 9229)"
    )
    parser.add_argument(
        "--wrapper",
        action="store_true",
        help="Generate Slack wrapper script and exit"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    parser.add_argument(
        "--config",
        help="Path to LLM config file"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logger = setup_logging(level=log_level)
    
    # Generate wrapper script if requested
    if args.wrapper:
        script_path = SlackWrapperGenerator.generate_and_install()
        print(f"Wrapper script installed: {script_path}")
        print()
        print("Now launch Slack with:")
        print(f"  {script_path}")
        print()
        print("Then run this overlay to start monitoring.")
        return 0
    
    # Load configuration
    if args.config:
        config = load_llm_config(args.config)
    else:
        config = load_llm_config()
    
    # Validate config
    if not config.endpoint or not config.api_key:
        print("WARNING: No LLM configuration found.")
        print()
        print("The overlay will run in TEST MODE (no actual rewrites).")
        print()
        print("To enable rewrites, set either:")
        print("  1. Environment variables:")
        print("       export LLM_ENDPOINT=https://api.example.com/v1/chat")
        print("       export LLM_API_KEY=your_key_here")
        print()
        print("  2. Config file:")
        print("       python -m overlay.main --config config/llm_config.yaml")
        print()
        print("Example llm_config.yaml:")
        print("""    endpoint: "https://api.openai.com/v1/chat/completions"
    api_key: "sk-..."
    model: "gpt-4o-mini"
    provider: "openai"
""")
        print("-" * 60)
        print()
    
    # Initialize components
    print("=" * 60)
    print("       WorkSpeak CDP Overlay v1.0")
    print("=" * 60)
    print()
    print(f"CDP Connection: {args.cdp_host}:{args.cdp_port}")
    
    # Wait for user to confirm Slack is running with CDP
    print()
    print("Before proceeding:")
    print("  1. Launch Slack with CDP enabled:")
    print(f"     slack --inspect={args.cdp_port} --remote-debugging-port={args.cdp_port}")
    print()
    print("  2. Press ENTER when Slack is ready...")
    print("-" * 60)
    input()
    
    # Start CDP connection
    print()
    print("Connecting to Slack CDP...")
    
    try:
        cdp = DevToolsConnection(host=args.cdp_host, port=args.cdp_port)
        page_url = await cdp.start_session()
        print(f"Connected to: {page_url}")
        
    except ConnectionError as e:
        print(f"ERROR: Could not connect to CDP endpoint")
        print(f"This usually means Slack is not running with CDP enabled.")
        print()
        print("Launch Slack with:")
        print(f"  slack --inspect={args.cdp_port} --remote-debugging-port={args.cdp_port}")
        return 1
    
    # Initialize other components
    print()
    print("Initializing components...")
    
    # Input monitor
    monitor = InputMonitor()
    
    # Rewrite worker
    worker = RewriteWorker()
    
    # Overlay UI
    overlay_ui = OverlayUI()
    async_overlay = OverlayUIAsync()
    
    # Set up callback chain
    async def handle_text_change(change_type: str, new_text: str):
        """Handle text change from input field."""
        if not new_text or len(new_text) < 3:
            return
        
        if not worker._running:
            return
        
        channel_context = await get_channel_context()
        
        logger.info(f"Text change detected: {len(new_text)} chars")
        
        # Send to worker
        from overlay.worker import RewriteRequest
        request = RewriteRequest(
            original_text=new_text,
            channel_context=channel_context,
            request_id=f"overlay_{int(time.time()*1000)}"
        )
        
        await worker.queue_rewrite(request)
    
    async def handle_enter_press():
        """Handle Enter key press."""
        logger.info("Enter key detected")
    
    async def handle_rewrite_result(result):
        """Handle rewrite result from worker."""
        if result.status.value == "completed" and result.rewritten_text:
            if result.rewritten_text != result.request.original_text:
                overlay_ui.show_suggestion(
                    result.request.original_text,
                    result.rewritten_text
                )
            else:
                overlay_ui.hide()
        elif result.status.value == "failed":
            overlay_ui.show_error(result.error or "Rewrite failed")
    
    async def handle_ui_action(action: str):
        """Handle UI user action."""
        logger.info(f"UI action: {action}")
        
        if action == "accept":
            # Get current rewritten text
            if overlay_ui.state.rewritten_text:
                await dom_api.set_input_text(
                    {"selector": "#message-input"},
                    overlay_ui.state.rewritten_text
                )
            overlay_ui.hide()
            
        elif action == "reject":
            overlay_ui.hide()
            
        elif action == "undo":
            # Clear input and hide
            await dom_api.set_input_text(
                {"selector": "#message-input"},
                ""
            )
            overlay_ui.hide()
    
    # Set callbacks
    monitor.set_on_text_change_callback(handle_text_change)
    monitor.set_on_enter_press_callback(handle_enter_press)
    worker.set_on_result_callback(handle_rewrite_result)
    
    # Get DOM API for input manipulation
    from overlay.devtools_client import DOMAPI
    dom_api = DOMAPI(cdp)
    
    # Find input element
    input_element = await dom_api.find_input_element()
    if not input_element:
        print("WARNING: Could not find input element. Generic mode enabled.")
        print("Text detection may not work optimally.")
    
    # Start all components
    print("Starting components...")
    
    await monitor.start(cdp)
    worker.start()
    await async_overlay.start()
    
    # Display welcome message
    print()
    print("-" * 60)
    print("WorkSpeak CDP Overlay is now RUNNING")
    print("-" * 60)
    print()
    
    if not config.endpoint:
        print("TEST MODE: No LLM configured")
        print("The overlay will display messages but won't rewrite them.")
        print()
    
    print("Keyboard shortcuts:")
    print("  [y]     Accept rewrite")
    print("  [n]     Reject rewrite")
    print("  [u]     Undo/Cancel")
    print("  [Ctrl+C] Quit")
    print()
    
    # Run main loop
    try:
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        print()
        print("Shutting down...")
        pass
    finally:
        # Cleanup
        print("Cleaning up...")
        await monitor.stop()
        worker.stop()
        await async_overlay.stop()
        await cdp.close()
        
        print("Goodbye!")
        return 0


async def get_channel_context():
    """Get current channel context."""
    from overlay.devtools_client import ChannelContextAPI
    channel_api = ChannelContextAPI(None)  # Will be set by actual running code
    return await channel_api.get_context_for_rewriter()


import time

if __name__ == "__main__":
    asyncio.run(main())
