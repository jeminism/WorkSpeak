"""
Chrome DevTools Protocol (CDP) client for WorkSpeak Overlay.
Connects to Slack's Chromium-based WebView to monitor and manipulate the input field.
"""

import asyncio
import json
import logging
import uuid
from typing import Optional, Callable, Dict, Any, List


logger = logging.getLogger("workspeak.overlay.cdp")


class DevToolsConnection:
    """Chrome DevTools Protocol connection to a browser instance (Slack)."""
    
    def __init__(self, host: str = "localhost", port: int = 9229):
        self.host = host
        self.port = port
        self.websocket = None
        self.session_id: Optional[str] = None
        self.pending_requests: Dict[str, asyncio.Future] = {}
        self._message_counter = 0
        self._running = False
        self._listener_task: Optional[asyncio.Task] = None
        
    async def start_session(self) -> str:
        """
        Connect to the CDP endpoint and start a new debugging session.
        
        Returns:
            Page target URL
            
        Raises:
            ConnectionError if connection fails
        """
        import aiohttp
        
        try:
            async with aiohttp.ClientSession() as session:
                # Discover targets (pages)
                async with session.ws_connect(
                    f"ws://{self.host}:{self.port}/json/version"
                ) as ws:
                    response = await ws.receive_json()
                    logger.info(f"Connected to CDP. Browser: {response.get('Browser', 'Unknown')}")
                
                # List targets
                async with session.ws_connect(
                    f"ws://{self.host}:{self.port}/json"
                ) as ws:
                    # Find the first available page
                    async with session.get(f"http://{self.host}:{self.port}/json/list") as resp:
                        targets = await resp.json()
                        
                        if not targets:
                            raise ConnectionError("No targets found on port 9229")
                        
                        # Use the first target (should be Slack main page)
                        target = targets[0]
                        webSocketURL = target.get('webSocketDebuggerUrl')
                        
                        if not webSocketURL:
                            raise ConnectionError("No WebSocket debugger URL found")
                        
                        logger.info(f"Connecting to target: {target.get('description', 'unknown')}")
                        logger.info(f"WebSocket URL: {webSocketURL}")
                        
                        # Connect to target
                        self.websocket = await aiohttp.ClientSession().ws_connect(webSocketURL)
                        self._running = True
                        
                        # Start listener
                        self._listener_task = asyncio.create_task(self._listen())
                        
                        # Get default session ID
                        self.session_id = await self.send_command("Page.enable")
                        
                        return target.get('url', '')
                        
        except Exception as e:
            logger.error(f"Failed to start CDP session: {e}")
            raise ConnectionError(f"Could not connect to Chrome DevTools: {e}")
    
    async def send_command(
        self, 
        method: str, 
        params: Optional[Dict[str, Any]] = None,
        timeout: float = 30.0
    ) -> Any:
        """
        Send a CDP command and wait for response.
        
        Args:
            method: CDP method name (e.g., "Runtime.evaluate")
            params: Command parameters
            timeout: Time to wait for response
            
        Returns:
            Command response or None
        """
        request_id = self._message_counter
        self._message_counter += 1
        
        message = {
            "id": request_id,
            "method": method,
            "params": params or {}
        }
        
        # Create future for response
        future = asyncio.get_event_loop().create_future()
        self.pending_requests[str(request_id)] = future
        
        # Send message
        if self.websocket:
            await self.websocket.send_json(message)
        
        # Wait for response
        try:
            result = await asyncio.wait_for(future, timeout=timeout)
            return result
        except asyncio.TimeoutError:
            logger.warning(f"Timeout waiting for {method}")
            return None
        finally:
            self.pending_requests.pop(str(request_id), None)
    
    async def _listen(self):
        """Listen for CDP events and responses."""
        while self._running:
            try:
                msg = await self.websocket.receive()
                
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    
                    # Handle response
                    if "id" in data:
                        request_id = str(data["id"])
                        if request_id in self.pending_requests:
                            future = self.pending_requests[request_id]
                            if not future.done():
                                # Check for error
                                if "error" in data:
                                    future.set_exception(Exception(data["error"].get("message", "Unknown error")))
                                else:
                                    future.set_result(data.get("result", {}))
                    
                    # Handle event (no id field)
                    elif "method" in data:
                        event_handler = getattr(self, f"_on_{data['method']}", None)
                        if event_handler:
                            await event_handler(data.get("params", {}))
                            
            except asyncio.CancelledError:
                break
            except Exception as e:
                if self._running:
                    logger.error(f"WebSocket error: {e}")
                await asyncio.sleep(0.1)
    
    async def close(self):
        """Close the CDP connection."""
        self._running = False
        
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
        
        if self.websocket and not self.websocket.closed:
            await self.websocket.close()


class RuntimeAPI:
    """Runtime API wrapper for evaluating JavaScript in the target page."""
    
    def __init__(self, connection: DevToolsConnection):
        self.connection = connection
    
    async def evaluate(
        self, 
        expression: str, 
        return_by_value: bool = True
    ) -> Any:
        """
        Evaluate JavaScript expression in the target page.
        
        Args:
            expression: JavaScript code to evaluate
            return_by_value: If True, return primitive values directly
            
        Returns:
            Evaluation result or None
        """
        result = await self.connection.send_command(
            "Runtime.evaluate",
            {
                "expression": expression,
                "returnByValue": return_by_value,
                "throwExceptions": True
            }
        )
        
        if result and "result" in result:
            return result["result"].get("value")
        return None
    
    async def call_function(
        self,
        function_declaration: str,
        args: Optional[List[Any]] = None,
        return_by_value: bool = True
    ) -> Any:
        """
        Call a JavaScript function.
        
        Args:
            function_declaration: JavaScript function definition
            args: Arguments to pass to the function
            return_by_value: If True, return primitive values directly
            
        Returns:
            Function result or None
        """
        arg_values = args or []
        arg_expressions = [json.dumps(arg) for arg in arg_values]
        
        expression = f"({function_declaration})({', '.join(arg_expressions)})"
        
        result = await self.connection.send_command(
            "Runtime.evaluate",
            {
                "expression": expression,
                "returnByValue": return_by_value,
                "throwExceptions": True
            }
        )
        
        if result and "result" in result:
            return result["result"].get("value")
        return None
    
    async def get_dom_node_id(self, selector: str) -> Optional[str]:
        """Get DOM node ID from CSS selector."""
        result = await self.connection.send_command(
            "DOM.getDocument",
            {}
        )
        
        if not result or "root" not in result:
            return None
        
        root_id = result["root"].get("nodeId")
        
        # Query selector
        query_result = await self.connection.send_command(
            "DOM.querySelector",
            {
                "nodeId": root_id,
                "selector": selector
            }
        )
        
        if query_result and "nodeId" in query_result:
            return query_result["nodeId"]
        
        return None
    
    async def get_dom_node_property(self, node_id: str, property_name: str) -> Optional[Any]:
        """Get a property value from a DOM node."""
        result = await self.connection.send_command(
            "DOM.describeNode",
            {
                "nodeId": node_id
            }
        )
        
        if not result or "node" not in result:
            return None
        
        backend_node_id = result["node"].get("backendNodeId")
        
        # Call $0.property
        expression = f'$0["{property_name}"]'
        
        # Use DOM.resolveNode to get the DOM object
        resolve_result = await self.connection.send_command(
            "DOM.resolveNode",
            {
                "backendNodeId": backend_node_id
            }
        )
        
        # Then evaluate
        if resolve_result and "object" in resolve_result:
            object_id = resolve_result["object"].get("objectId")
            
            eval_result = await self.connection.send_command(
                "Runtime.getProperties",
                {
                    "objectId": object_id
                }
            )
            
            if eval_result:
                for prop in eval_result.get("result", []):
                    if prop.get("name") == property_name:
                        return prop.get("value", {}).get("value")
        
        return None


class DOMAPI:
    """DOM API wrapper for WorkSpeak overlay."""
    
    def __init__(self, connection: DevToolsConnection):
        self.connection = connection
        self.runtime = RuntimeAPI(connection)
    
    async def find_input_element(self) -> Optional[Dict]:
        """
        Find Slack's message input element.
        
        Returns:
            Dict with element info or None
        """
        # Try common selectors for Slack input
        selectors = [
            "#message-input",
            '#[placeholder*="Message"]',
            'textarea[placeholder*="Message"]',
            '[contenteditable="true"][data-testid="message_input"]',
            '#slack-input'
        ]
        
        root = await self.connection.send_command("DOM.getDocument", {})
        
        if not root or "root" not in root:
            logger.warning("Could not get DOM root")
            return None
        
        root_id = root["root"]["nodeId"]
        
        for selector in selectors:
            result = await self.connection.send_command(
                "DOM.querySelector",
                {
                    "nodeId": root_id,
                    "selector": selector
                }
            )
            
            if result and "nodeId" in result:
                # Get more details about the element
                describe = await self.connection.send_command(
                    "DOM.describeNode",
                    {
                        "nodeId": result["nodeId"]
                    }
                )
                
                logger.info(f"Found input element with selector: {selector}")
                return {
                    "nodeId": result["nodeId"],
                    "selector": selector,
                    "description": describe
                }
        
        logger.warning("Could not find Slack input element with common selectors")
        return None
    
    async def get_input_text(self, element: Dict) -> Optional[str]:
        """Get text content from input element."""
        if not element or "nodeId" not in element:
            return None
        
        # Try to get as textContent first
        text_result = await self.connection.send_command(
            "DOM.describeNode",
            {"nodeId": element["nodeId"]}
        )
        
        if text_result and "node" in text_result:
            node = text_result["node"]
            
            # It might be contenteditable
            if node.get("nodeType") == 11:  # DocumentFragment (contenteditable)
                # Evaluate to get textContent
                text = await self.runtime.evaluate(
                    f'document.getElementById("message-input").textContent || document.querySelector("#message-input")?.textContent || ""'
                )
                return text
            
            # Try to get value
            value = await self.runtime.evaluate(
                f'document.querySelector("{element["selector"]}")?.value || ""'
            )
            return value
    
    async def set_input_text(self, element: Dict, text: str) -> bool:
        """Set text in input element."""
        if not element or "selector" not in element:
            return False
        
        try:
            # Set the value
            await self.runtime.evaluate(
                f"""
                var el = document.querySelector("{element['selector']}");
                if (el) {{
                    el.value = {json.dumps(text)};
                    el.dispatchEvent(new Event('input', {{bubbles: true}}));
                    el.dispatchEvent(new Event('change', {{bubbles: true}}));
                }}
                """
            )
            return True
        except Exception as e:
            logger.error(f"Failed to set input text: {e}")
            return False
    
    async def simulate_keypress(self, key: str = "Enter"):
        """Simulate keypress event (e.g., Enter to send)."""
        key_map = {
            "Enter": 13,
            "Shift": 16,
            "Control": 17,
            "Alt": 18,
            "Escape": 27,
            "Backspace": 8,
            "Tab": 9,
            "ArrowUp": 38,
            "ArrowDown": 40
        }
        
        key_code = key_map.get(key, 13)  # Default to Enter
        
        await self.runtime.evaluate(f"""
            document.dispatchEvent(new KeyboardEvent('keydown', {{keyCode: {key_code}, key: '{key}'}}));
            document.dispatchEvent(new KeyboardEvent('keypress', {{keyCode: {key_code}, key: '{key}'}}));
            document.dispatchEvent(new KeyboardEvent('keyup', {{keyCode: {key_code}, key: '{key}'}}));
        """)


class ChannelContextAPI:
    """API for accessing Slack's channel context from Redux state."""
    
    def __init__(self, connection: DevToolsConnection):
        self.connection = connection
        self.runtime = RuntimeAPI(connection)
    
    async def get_active_channel(self) -> Optional[Dict]:
        """
        Get the currently active channel from Slack's internal state.
        
        Returns:
            Dict with channel info or None
        """
        # Try to access Slack's Redux store
        expressions = [
            """
            (function() {
                var store = window.Store || window.store;
                if (!store) return null;
                
                var channel =Store.Actions.channel.getActiveChannel();
                if (!channel) return null;
                
                return {
                    id: channel.id,
                    name: channel.name,
                    type: channel.isGroup || channel.isDirect ? 'dm' : 'channel'
                };
            })()
            """,
            """
            (function() {
                var state = window.App?.dispatch?.getState?.();
                if (!state) return null;
                return state?.channel?.active || null;
            })()
            """,
            """
            (function() {
                // Try to find Redux store
                var el = document.getElementById('__NEXT_DATA__');
                if (el) {
                    var data = JSON.parse(el.textContent || '{}');
                    return { id: data?.props?.pageProps?.currentChannelId };
                }
                return null;
            })()
            """
        ]
        
        for expr in expressions:
            try:
                result = await self.runtime.evaluate(expr)
                if result:
                    logger.info(f"Channel context: {result}")
                    return result
            except Exception as e:
                logger.debug(f"Channel context attempt failed: {e}")
                continue
        
        return None
    
    async def get_channel_name(self) -> Optional[str]:
        """Get the current channel name."""
        channel = await self.get_active_channel()
        if channel:
            return channel.get("name") or channel.get("id")
        return None
    
    async def get_context_for_rewriter(self) -> str:
        """
        Get context about the current channel for the rewriter.
        
        Returns:
            Context string to include in rewrite prompt
        """
        channel = await self.get_active_channel()
        
        if not channel:
            return ""
        
        channel_name = channel.get("name") or channel.get("id", "unknown")
        channel_type = channel.get("type", "unknown")
        
        return f"Current channel: #{channel_name} ({channel_type})"


class DevToolsConnectionException(Exception):
    """Custom exception for CDP connection errors."""
    pass
