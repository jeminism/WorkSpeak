"""
Slack Input Field Monitor for WorkSpeak Overlay.
Monitors the Slack message input field for text changes.
"""

import asyncio
import logging
from typing import Optional, Callable, Dict, Any


logger = logging.getLogger("workspeak.overlay.monitor")


class InputMonitor:
    """Monitors Slack input field for text changes."""
    
    def __init__(self, input_selector: str = "#message-input"):
        self.input_selector = input_selector
        self.current_text: Optional[str] = None
        self.observation_task: Optional[asyncio.Task] = None
        self._running = False
        self._on_text_change_callback: Optional[Callable] = None
        self._on_enter_press_callback: Optional[Callable] = None
        
    def set_on_text_change_callback(self, callback: Callable[[str, str], None]):
        """
        Set callback for text change events.
        
        Args:
            callback: Function(text_change_type, new_text)
        """
        self._on_text_change_callback = callback
    
    def set_on_enter_press_callback(self, callback: Callable[[], None]):
        """
        Set callback for Enter key press.
        """
        self._on_enter_press_callback = callback
    
    async def start(self, cdp_client):
        """
        Start monitoring the input field.
        
        Args:
            cdp_client: DevToolsConnection instance
        """
        self.cdp_client = cdp_client
        self._running = True
        
        # Find the input element
        self.input_element = await self._find_input_element()
        
        if not self.input_element:
            logger.error("Could not find input element. Trying alternative selectors...")
            await self._find_alternative_input()
        
        if not self.input_element:
            logger.error("Failed to find any input element. Starting with generic monitor.")
            self.generic_mode = True
        else:
            self.generic_mode = False
            logger.info(f"Using input selector: {self.input_element.get('selector', 'unknown')}")
        
        # Start observation
        self.observation_task = asyncio.create_task(self._observe_input())
        logger.info("Input monitor started")
    
    async def stop(self):
        """Stop monitoring."""
        self._running = False
        
        if self.observation_task:
            self.observation_task.cancel()
            try:
                await self.observation_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Input monitor stopped")
    
    async def _find_input_element(self) -> Optional[Dict]:
        """Find the input element using CDP."""
        from overlay.devtools_client import DOMAPI
        
        dom = DOMAPI(self.cdp_client)
        return await dom.find_input_element()
    
    async def _find_alternative_input(self):
        """Try alternative selectors if default fails."""
        from overlay.devtools_client import DOMAPI
        
        dom = DOMAPI(self.cdp_client)
        
        # Try different selectors
        alt_selectors = [
            'textarea[data-testid="message_input"]',
            '#slack-input',
            'div[contenteditable="true"]',
            '[role="textbox"]',
        ]
        
        root = await self.cdp_client.send_command("DOM.getDocument", {})
        
        if not root or "root" not in root:
            return
        
        root_id = root["root"]["nodeId"]
        
        for selector in alt_selectors:
            result = await self.cdp_client.send_command(
                "DOM.querySelector",
                {
                    "nodeId": root_id,
                    "selector": selector
                }
            )
            
            if result and "nodeId" in result:
                describe = await self.cdp_client.send_command(
                    "DOM.describeNode",
                    {"nodeId": result["nodeId"]}
                )
                
                self.input_element = {
                    "nodeId": result["nodeId"],
                    "selector": selector,
                    "description": describe
                }
                logger.info(f"Found alternative input element: {selector}")
                return
    
    async def _observe_input(self):
        """Main observation loop for input text changes."""
        last_text = None
        debounce_timer = None
        
        while self._running:
            try:
                # Get current input text
                current = await self._get_input_text()
                
                # Debounce: only fire if text has changed and stayed changed for 100ms
                if current != last_text:
                    last_text = current
                    
                    if self._on_text_change_callback:
                        try:
                            await self._on_text_change_callback("change", current)
                        except Exception as e:
                            logger.error(f"Error in text change callback: {e}")
                
                # Check for Enter key press
                await self._check_enter_key()
                
                # Wait before next check
                await asyncio.sleep(0.1)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                if self._running:
                    logger.error(f"Error in input observation: {e}")
                await asyncio.sleep(0.5)
    
    async def _get_input_text(self) -> Optional[str]:
        """Get current text from input field."""
        if self.generic_mode:
            # Generic fallback: evaluate JavaScript
            text = await self.cdp_client.send_command(
                "Runtime.evaluate",
                {
                    "expression": """
                    var el = document.querySelector('[contenteditable="true"]') || 
                             document.querySelector('textarea') ||
                             document.querySelector('[role="textbox"]');
                    return el ? (el.textContent || el.value || "") : "";
                    """
                }
            )
            return text if text else None
        
        # Use element-specific method
        if self.input_element:
            selector = self.input_element.get("selector", "")
            try:
                text = await self.cdp_client.send_command(
                    "Runtime.evaluate",
                    {
                        "expression": f"""
                        var el = document.querySelector({json.dumps(selector)});
                        el ? (el.textContent || el.value || "") : "";
                        """
                    }
                )
                return text
            except Exception as e:
                logger.warning(f"Error getting input text: {e}")
                return None
        
        return None
    
    async def _check_enter_key(self):
        """Check if Enter key is being pressed."""
        if not self._on_enter_press_callback:
            return
        
        try:
            result = await self.cdp_client.send_command(
                "Runtime.evaluate",
                {
                    "expression": """
                    (function() {
                        // Track last key pressed
                        if (!window.lastKey) window.lastKey = null;
                        var key = window.lastKey;
                        
                        // Listen for keydown
                        document.addEventListener('keydown', function(e) {
                            if (e.key === 'Enter') {
                                window.lastKey = 'Enter';
                                e.preventDefault();
                            } else {
                                window.lastKey = null;
                            }
                        });
                        
                        return key === 'Enter';
                    })();
                    """
                }
            )
            
            if result:
                if self._on_enter_press_callback:
                    try:
                        await self._on_enter_press_callback()
                    except Exception as e:
                        logger.error(f"Error in Enter callback: {e}")
                        
        except Exception as e:
            logger.warning(f"Error checking Enter key: {e}")
    
    def _on_dom_node_updated(self, params: Dict[str, Any]):
        """Handle DOM node update event."""
        node_id = params.get("nodes", [{}])[0].get("nodeId")
        logger.debug(f"DOM node updated: {node_id}")


import json
