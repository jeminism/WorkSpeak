import os
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_message_bot.llm_backend import get_backend
from slack_message_bot.rewriter import MessageRewriter
from slack_message_bot.config import load_llm_config
from slack_message_bot.logging_config import get_logger

logger = get_logger(__name__)

class SlackMessageBot:
    """Main Slack bot handler."""
    
    def __init__(self):
        self.config = load_llm_config()
        self.rewriter = MessageRewriter()
        
        bot_token = os.getenv("SLACK_BOT_TOKEN")
        signing_secret = os.getenv("SLACK_SIGNING_SECRET")
        
        if not bot_token:
            raise ValueError("SLACK_BOT_TOKEN environment variable not set")
        
        self.app = App(token=bot_token, signing_secret=signing_secret if signing_secret else None)
        
        # Store the client instance
        self.client = self.app.client
        
        # Set up event handlers
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Set up Bolt event handlers."""
        
        # Listen for message events
        @self.app.event("message")
        def handle_message(event, say, client):
            try:
                # Skip if it's a bot message or message edit
                if event.get("subtype") not in [None, "bot_message_thread"]:
                    return
                
                # Skip if it's the bot itself (we'll handle this by user ID check)
                # For now, we process all messages from the authenticated user
                # You should set BOT_USER_ID environment variable to your user ID
                
                bot_user_id = os.getenv("BOT_USER_ID")
                user_id = event.get("user")
                
                if bot_user_id and user_id != bot_user_id:
                    # Not our message, skip
                    return
                
                # Fetch thread context if available
                thread_ts = event.get("thread_ts") or event.get("ts")
                thread_context = self._fetch_thread_context(event["channel"], thread_ts)
                
                # Get original text
                original_text = event["message"]["text"]
                if not original_text:
                    return
                
                # Rewrite message
                rewritten, decision = self.rewriter.rewrite(
                    original_text, 
                    thread_context=thread_context,
                    config=self.config
                )
                
                # Log quality decision
                self._log_quality(original_text, rewritten, decision)
                
                # Edit the message if rewritten differently
                if rewritten != original_text:
                    try:
                        updated_text = f"{rewritten}\n\n--- edited by WorkSpeak Bot"
                        client.chat_update(
                            channel=event["channel"],
                            ts=event["ts"],
                            text=updated_text
                        )
                        logger.info(f"Successfully edited message ts={event['ts']}")
                    except Exception as edit_error:
                        logger.error(f"Failed to edit message: {edit_error}")
                        
            except Exception as e:
                logger.error(f"Error handling message event: {e}")
                import traceback
                logger.error(traceback.format_exc())
    
    def _fetch_thread_context(self, channel: str, ts: str, max_messages: int = 5) -> str:
        """Fetch recent messages in thread for context."""
        try:
            response = self.client.conversations_replies(
                channel=channel,
                ts=ts,
                limit=min(max_messages, 5)
            )
            
            if response.get("ok"):
                messages = response.get("messages", [])
                context_lines = []
                for msg in messages[:3]:
                    user = msg.get("user", "unknown")
                    text = msg.get("text", "")
                    context_lines.append(f"@{user}: {text}")
                return "\n".join(context_lines)
            else:
                logger.warning(f"Failed to fetch thread context: {response}")
                return ""
                
        except Exception as e:
            logger.warning(f"Error fetching thread context: {e}")
            return ""
    
    def _log_quality(self, original: str, rewritten: str, decision: str):
        """Log quality decision."""
        original_preview = original[:80] + "..." if len(original) > 80 else original
        rewritten_preview = rewritten[:80] + "..." if len(rewritten) > 80 else rewritten
        
        logger.info(f"[Quality] Decision: {decision}")
        logger.info(f"[Original] {original_preview}")
        logger.info(f"[Rewritten] {rewritten_preview}")
    
    def _log_error(self, error: str):
        """Log errors silently."""
        logger.error(f"[Error] {error}")
    
    def run(self):
        """Start the bot."""
        app_token = os.getenv("SLACK_APP_TOKEN")
        if not app_token:
            logger.error("SLACK_APP_TOKEN not set. Using test mode.")
            logger.info("To run with Socket Mode, set SLACK_APP_TOKEN")
            return
        
        mode_handler = SocketModeHandler(
            self.app,
            app_token
        )
        
        logger.info("Starting WorkSpeak Bot...")
        mode_handler.start()
