"""
Overlay UI for WorkSpeak.
Displays rewrite suggestions with accept/reject buttons.
Simple terminal-based UI for testing,可扩展 to Tkinter/GTK later.
"""

import asyncio
import logging
from typing import Optional
from dataclasses import dataclass


logger = logging.getLogger("workspeak.overlay.ui")


@dataclass
class UIState:
    """Current state of the overlay UI."""
    visible: bool = False
    original_text: str = ""
    rewritten_text: str = ""
    action: str = ""  # "none", "accept", "reject", "undo"
    error_message: str = ""
    
    # Keyboard shortcut hints
    accept_key: str = "y"
    reject_key: str = "n"
    
    @property
    def has_suggestion(self) -> bool:
        """Check if there's an active rewrite suggestion."""
        return self.visible and bool(self.rewritten_text)
    
    @property
    def needs_action(self) -> bool:
        """Check if UI is waiting for user action."""
        return self.visible and not self.action


class OverlayUI:
    """Simple text-based overlay UI for showing rewrite suggestions."""
    
    def __init__(self):
        self.state = UIState()
        self._running = False
        self._on_action_callback: Optional[callable] = None
        
    def set_on_action_callback(self, callback: callable):
        """Set callback when user takes action."""
        self._on_action_callback = callback
    
    def show_suggestion(self, original: str, rewritten: str):
        """Show a rewrite suggestion."""
        self.state.original_text = original
        self.state.rewritten_text = rewritten
        self.state.visible = True
        self.state.action = ""
        
        self._render()
        logger.info(f"Suggestion shown: '{original[:40]}...' -> '{rewritten[:40]}...'")
    
    def hide(self):
        """Hide the overlay."""
        self.state.visible = False
        self.state.action = ""
        self.state.error_message = ""
        
        self._render()
        logger.info("Overlay hidden")
    
    def show_error(self, message: str):
        """Show an error message."""
        self.state.error_message = message
        self.state.action = ""
        
        self._render()
        logger.error(f"Error displayed: {message}")
    
    def clear_error(self):
        """Clear error message."""
        self.state.error_message = ""
        self._render()
    
    def accept(self):
        """User accepted the rewrite."""
        self.state.action = "accept"
        
        if self._on_action_callback:
            asyncio.create_task(self._on_action_callback("accept"))
        
        logger.info("User accepted rewrite")
    
    def reject(self):
        """User rejected the rewrite."""
        self.state.action = "reject"
        
        if self._on_action_callback:
            asyncio.create_task(self._on_action_callback("reject"))
        
        logger.info("User rejected rewrite")
    
    def undo(self):
        """User wants to undo (cancel current edit)."""
        self.state.action = "undo"
        
        if self._on_action_callback:
            asyncio.create_task(self._on_action_callback("undo"))
        
        logger.info("User requested undo")
    
    def _render(self):
        """Render the overlay to console."""
        # Clear screen (simple approach)
        print("\033[H\033[J", end="")
        
        print("=" * 60)
        print("                    WorkSpeak Overlay")
        print("=" * 60)
        
        if self.state.has_suggestion:
            print(f"\n[ORIGINAL]  \"\"\"{self.state.original_text}\"\"\"")
            print()
            print("▼ REWRITE ▼")
            print()
            print(f"[REWWRITTEN] \"\"\"{self.state.rewritten_text}\"\"\"")
            print()
            print()
            print("-" * 60)
            print()
            print(f"Keyboard: [{self.state.accept_key.upper()}] Accept  [{self.state.reject_key.upper()}] Reject")
            print()
            print("Waiting for input...")
            
        elif self.state.error_message:
            print()
            print(f"ERROR: {self.state.error_message}")
            print()
            print("Press ANY key to continue...")
            
        elif self.state.visible:
            print()
            print("WorkSpeak is processing your message...")
            print()
            
        else:
            print("WorkSpeak Overlay: Ready")
            print()
            print("Monitor running for Slack input changes")
            print()
        
        print("=" * 60)


class OverlayUIAsync:
    """Async version of OverlayUI that reads keyboard input."""
    
    def __init__(self):
        self.overlay = OverlayUI()
        self._user_input_task: Optional[asyncio.Task] = None
        
    async def start(self):
        """Start the async UI loop."""
        self._running = True
        self._user_input_task = asyncio.create_task(self._read_input())
        logger.info("Async UI started")
    
    async def stop(self):
        """Stop the async UI loop."""
        self._running = False
        
        if self._user_input_task:
            self._user_input_task.cancel()
            try:
                await self._user_input_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Async UI stopped")
    
    async def _read_input(self):
        """Read user input from keyboard."""
        import sys
        
        while self._running:
            try:
                # Non-blocking read attempt
                if sys.stdin in asyncio.as_completed([
                    asyncio.get_event_loop().run_in_executor(None, sys.stdin.read, 1)
                ]):
                    char = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.read, 1)
                    
                    if char and self.overlay.state.visible:
                        key = char.lower().strip()
                        
                        if key == self.overlay.state.accept_key:
                            self.overlay.accept()
                        elif key in (self.overlay.state.reject_key, 'n'):
                            self.overlay.reject()
                        elif key == 'u':
                            self.overlay.undo()
                        
                        # Clear input buffer
                        _ = sys.stdin.read(1)
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error reading input: {e}")
            
            await asyncio.sleep(0.1)
    
    async def show_suggestion(self, original: str, rewritten: str):
        """Show suggestion (async)."""
        self.overlay.show_suggestion(original, rewritten)
        
        # Re-render after showing suggestion
        await asyncio.sleep(0.1)

