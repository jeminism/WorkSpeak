"""
Background Rewrite Worker for WorkSpeak Overlay.
Handles rewrite requests asynchronously with the rewrite engine.
"""

import asyncio
import logging
from typing import Optional, Callable, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import time


logger = logging.getLogger("workspeak.overlay.worker")


class RewriteStatus(Enum):
    """Status of a rewrite operation."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


@dataclass
class RewriteRequest:
    """A request to rewrite text."""
    original_text: str
    channel_context: str = ""
    request_id: str = ""
    timestamp: float = 0.0


@dataclass  
class RewriteResult:
    """Result of a rewrite operation."""
    request: RewriteRequest
    rewritten_text: Optional[str] = None
    status: RewriteStatus = RewriteStatus.PENDING
    error: Optional[str] = None
    decision: str = ""
    latency_ms: float = 0.0


class RewriteWorker:
    """Background worker that processes rewrite requests."""
    
    def __init__(self):
        self.queue: asyncio.Queue = asyncio.Queue()
        self.pending_requests: Dict[str, RewriteResult] = {}
        self._running = False
        self._worker_task: Optional[asyncio.Task] = None
        self._on_result_callback: Optional[Callable[[RewriteResult], None]] = None
        self._on_status_callback: Optional[Callable[[str, RewriteStatus], None]] = None
        
        # Import rewrite library
        from core.rewriter import MessageRewriter
        from core.config import load_llm_config
        self.rewriter = MessageRewriter()
        
        # Load config - might be None if not configured
        try:
            self.config = load_llm_config()
        except Exception as e:
            logger.warning(f"Could not load LLM config: {e}")
            self.config = None
    
    def set_on_result_callback(self, callback: Callable[[RewriteResult], None]):
        """Set callback when rewrite result is ready."""
        self._on_result_callback = callback
    
    def set_on_status_callback(self, callback: Callable[[str, RewriteStatus], None]):
        """Set callback for status updates."""
        self._on_status_callback = callback
    
    def start(self):
        """Start the rewrite worker."""
        self._running = True
        self._worker_task = asyncio.create_task(self._process_queue())
        logger.info("Rewrite worker started")
    
    def stop(self):
        """Stop the rewrite worker."""
        self._running = False
        
        if self._worker_task:
            self._worker_task.cancel()
            try:
                asyncio.get_event_loop().run_until_complete(self._worker_task)
            except asyncio.CancelledError:
                pass
        
        logger.info("Rewrite worker stopped")
    
    async def queue_rewrite(self, request: RewriteRequest):
        """Queue a rewrite request."""
        await self.queue.put(request)
        
        # Create pending result
        result = RewriteResult(
            request=request,
            status=RewriteStatus.PENDING
        )
        self.pending_requests[request.request_id] = result
        
        logger.debug(f"Queued rewrite request: {request.request_id}")
    
    async def _process_queue(self):
        """Main processing loop."""
        while self._running:
            try:
                # Get request from queue
                request = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                
                # Update status
                if request.request_id in self.pending_requests:
                    self.pending_requests[request.request_id].status = RewriteStatus.PROCESSING
                
                # Process rewrite
                result = await self._process_rewrite(request)
                
                # Update pending with result
                self.pending_requests[request.request_id] = result
                
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing rewrite queue: {e}")
                await asyncio.sleep(0.1)
    
    async def _process_rewrite(self, request: RewriteRequest) -> RewriteResult:
        """Process a single rewrite request."""
        start_time = time.time()
        
        logger.info(f"Processing rewrite: {request.request_id[:8]}...")
        
        try:
            # Get rewritten text
            rewritten, decision = self.rewriter.rewrite(
                original_text=request.original_text,
                thread_context=request.channel_context,
                config=self.config
            )
            
            latency_ms = (time.time() - start_time) * 1000
            
            # Check if in test mode
            if "test_mode" in decision:
                logger.info(f"Test mode - no LLM call, original text: {request.original_text[:50]}...")
                return RewriteResult(
                    request=request,
                    rewritten_text=request.original_text,
                    status=RewriteStatus.COMPLETED,
                    decision="test_mode",
                    latency_ms=latency_ms
                )
            
            # Return rewrite result
            if rewritten and rewritten != request.original_text:
                return RewriteResult(
                    request=request,
                    rewritten_text=rewritten,
                    status=RewriteStatus.COMPLETED,
                    decision=decision,
                    latency_ms=latency_ms
                )
            else:
                return RewriteResult(
                    request=request,
                    rewritten_text=request.original_text,
                    status=RewriteStatus.COMPLETED,
                    decision=decision,
                    latency_ms=latency_ms
                )
                
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error(f"Error during rewrite: {e}")
            
            return RewriteResult(
                request=request,
                rewritten_text=request.original_text,
                status=RewriteStatus.FAILED,
                error=str(e),
                latency_ms=latency_ms
            )


class RewriteSession:
    """Manages a rewrite session for a single input field."""
    
    def __init__(self, worker: RewriteWorker):
        self.worker = worker
        self.current_request_id: Optional[str] = None
        self.current_text: Optional[str] = None
        self.last_rewrite_result: Optional[RewriteResult] = None
        self._running = False
        
    def start(self):
        """Start the session."""
        self._running = True
        self.worker.set_on_result_callback(self._on_rewrite_result)
        self.worker.start()
        logger.info("Rewrite session started")
    
    def stop(self):
        """Stop the session."""
        self._running = False
        self.worker.stop()
        logger.info("Rewrite session stopped")
    
    def _on_rewrite_result(self, result: RewriteResult):
        """Handle rewrite result from worker."""
        self.last_rewrite_result = result
        self.current_request_id = None
        
        logger.info(f"Rewrite complete: {result.status.value} - {result.decision}")
        
        # Callback for UI
        if self.worker._on_result_callback:
            # Chain to UI callback if set
            pass
        
        logger.info(f"  Original: {result.request.original_text[:60]}...")
        if result.rewritten_text and result.rewritten_text != result.request.original_text:
            logger.info(f"  Rewritten: {result.rewritten_text[:60]}...")
    
    async def send_rewrite_request(self, text: str, channel_context: str = "") -> Optional[RewriteResult]:
        """
        Send a rewrite request for the given text.
        
        Returns:
            RewriteResult if successful, None if session not running
        """
        if not self._running:
            logger.warning("Cannot send request - session not running")
            return None
        
        request_id = f"req_{len(self.worker.pending_requests)}_{int(time.time()*1000)}"
        
        request = RewriteRequest(
            original_text=text,
            channel_context=channel_context,
            request_id=request_id,
            timestamp=time.time()
        )
        
        await self.worker.queue_rewrite(request)
        self.current_request_id = request_id
        self.current_text = text
        
        return self.pending_requests.get(request_id)
    
    def get_pending_result(self) -> Optional[RewriteResult]:
        """Get the latest pending rewrite result."""
        return self.last_rewrite_result
