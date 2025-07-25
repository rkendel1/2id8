"""
LLM call handler utilities for managing AI interactions and API calls.
"""

import asyncio
import time
from typing import Dict, List, Any, Optional, Callable, Union
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
from app.core.config import settings
from app.core.logging import logger
import json


class CallPriority(Enum):
    """Priority levels for LLM calls."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class CallStatus(Enum):
    """Status of LLM calls."""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


@dataclass
class LLMCall:
    """Data class representing an LLM call."""
    id: str
    prompt: str
    model: str
    temperature: float
    max_tokens: int
    priority: CallPriority
    user_id: int
    created_at: datetime
    timeout_seconds: int = 300
    retry_count: int = 0
    max_retries: int = 3
    status: CallStatus = CallStatus.QUEUED
    result: Optional[str] = None
    error: Optional[str] = None
    response_time_ms: Optional[int] = None
    tokens_used: Optional[int] = None
    cost: Optional[float] = None
    metadata: Dict[str, Any] = None


class RateLimiter:
    """Rate limiter for API calls."""
    
    def __init__(self, calls_per_minute: int = 60, calls_per_hour: int = 1000):
        self.calls_per_minute = calls_per_minute
        self.calls_per_hour = calls_per_hour
        self.minute_calls: List[datetime] = []
        self.hour_calls: List[datetime] = []
        self._lock = asyncio.Lock()
    
    async def can_make_call(self) -> bool:
        """Check if a call can be made within rate limits."""
        async with self._lock:
            now = datetime.utcnow()
            minute_ago = now - timedelta(minutes=1)
            hour_ago = now - timedelta(hours=1)
            
            # Clean old entries
            self.minute_calls = [call_time for call_time in self.minute_calls if call_time > minute_ago]
            self.hour_calls = [call_time for call_time in self.hour_calls if call_time > hour_ago]
            
            return (len(self.minute_calls) < self.calls_per_minute and 
                    len(self.hour_calls) < self.calls_per_hour)
    
    async def record_call(self):
        """Record a call for rate limiting."""
        async with self._lock:
            now = datetime.utcnow()
            self.minute_calls.append(now)
            self.hour_calls.append(now)


class CallQueue:
    """Queue for managing LLM calls with priority."""
    
    def __init__(self, max_concurrent_calls: int = 5):
        self.max_concurrent_calls = max_concurrent_calls
        self.queues = {
            CallPriority.CRITICAL: [],
            CallPriority.HIGH: [],
            CallPriority.NORMAL: [],
            CallPriority.LOW: []
        }
        self.active_calls: Dict[str, LLMCall] = {}
        self._lock = asyncio.Lock()
    
    async def enqueue(self, call: LLMCall):
        """Add a call to the appropriate priority queue."""
        async with self._lock:
            self.queues[call.priority].append(call)
            logger.debug(f"Enqueued call {call.id} with priority {call.priority.value}")
    
    async def dequeue(self) -> Optional[LLMCall]:
        """Get the next call to process based on priority."""
        async with self._lock:
            # Check if we have capacity
            if len(self.active_calls) >= self.max_concurrent_calls:
                return None
            
            # Get highest priority call
            for priority in [CallPriority.CRITICAL, CallPriority.HIGH, CallPriority.NORMAL, CallPriority.LOW]:
                if self.queues[priority]:
                    call = self.queues[priority].pop(0)
                    self.active_calls[call.id] = call
                    call.status = CallStatus.PROCESSING
                    logger.debug(f"Dequeued call {call.id}")
                    return call
            
            return None
    
    async def complete_call(self, call_id: str):
        """Mark a call as completed and remove from active calls."""
        async with self._lock:
            if call_id in self.active_calls:
                del self.active_calls[call_id]
                logger.debug(f"Completed call {call_id}")
    
    async def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        async with self._lock:
            return {
                "active_calls": len(self.active_calls),
                "queued_calls": {
                    priority.value: len(queue) 
                    for priority, queue in self.queues.items()
                },
                "total_queued": sum(len(queue) for queue in self.queues.values()),
                "capacity_used": len(self.active_calls) / self.max_concurrent_calls
            }


class LLMCallHandler:
    """Main handler for managing LLM calls with queueing, rate limiting, and retry logic."""
    
    def __init__(self):
        self.rate_limiter = RateLimiter(
            calls_per_minute=60,
            calls_per_hour=1000
        )
        self.call_queue = CallQueue(max_concurrent_calls=5)
        self.call_history: Dict[str, LLMCall] = {}
        self.processing_task: Optional[asyncio.Task] = None
        self._shutdown = False
    
    async def start_processing(self):
        """Start the background task for processing calls."""
        if self.processing_task is None or self.processing_task.done():
            self.processing_task = asyncio.create_task(self._process_calls())
            logger.info("Started LLM call processing")
    
    async def stop_processing(self):
        """Stop the background processing task."""
        self._shutdown = True
        if self.processing_task:
            self.processing_task.cancel()
            try:
                await self.processing_task
            except asyncio.CancelledError:
                pass
        logger.info("Stopped LLM call processing")
    
    async def submit_call(
        self,
        prompt: str,
        user_id: int,
        model: str = None,
        temperature: float = None,
        max_tokens: int = None,
        priority: CallPriority = CallPriority.NORMAL,
        timeout_seconds: int = 300,
        metadata: Dict[str, Any] = None
    ) -> str:
        """
        Submit an LLM call for processing.
        
        Args:
            prompt: The prompt to send
            user_id: ID of the user making the call
            model: Model to use (defaults to config)
            temperature: Temperature setting
            max_tokens: Maximum tokens
            priority: Call priority
            timeout_seconds: Timeout for the call
            metadata: Additional metadata
            
        Returns:
            Call ID for tracking
        """
        call_id = f"call_{int(time.time() * 1000)}_{user_id}"
        
        call = LLMCall(
            id=call_id,
            prompt=prompt,
            model=model or settings.openai_model,
            temperature=temperature or settings.openai_temperature,
            max_tokens=max_tokens or settings.max_tokens,
            priority=priority,
            user_id=user_id,
            created_at=datetime.utcnow(),
            timeout_seconds=timeout_seconds,
            metadata=metadata or {}
        )
        
        await self.call_queue.enqueue(call)
        self.call_history[call_id] = call
        
        # Ensure processing is running
        await self.start_processing()
        
        logger.info(f"Submitted LLM call {call_id} for user {user_id}")
        return call_id
    
    async def get_call_status(self, call_id: str) -> Optional[CallPriority]:
        """Get the status of a call."""
        call = self.call_history.get(call_id)
        return call.status if call else None
    
    async def get_call_result(self, call_id: str) -> Optional[LLMCall]:
        """Get the result of a completed call."""
        return self.call_history.get(call_id)
    
    async def wait_for_call(self, call_id: str, timeout_seconds: int = 300) -> Optional[str]:
        """
        Wait for a call to complete and return the result.
        
        Args:
            call_id: ID of the call to wait for
            timeout_seconds: Maximum time to wait
            
        Returns:
            Call result or None if timeout/error
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout_seconds:
            call = self.call_history.get(call_id)
            if not call:
                return None
            
            if call.status == CallStatus.COMPLETED:
                return call.result
            elif call.status in [CallStatus.FAILED, CallStatus.TIMEOUT, CallStatus.CANCELLED]:
                logger.error(f"Call {call_id} failed with status {call.status.value}: {call.error}")
                return None
            
            await asyncio.sleep(0.5)  # Check every 500ms
        
        logger.warning(f"Timeout waiting for call {call_id}")
        return None
    
    async def cancel_call(self, call_id: str) -> bool:
        """Cancel a queued or processing call."""
        call = self.call_history.get(call_id)
        if not call:
            return False
        
        if call.status in [CallStatus.QUEUED, CallStatus.PROCESSING]:
            call.status = CallStatus.CANCELLED
            await self.call_queue.complete_call(call_id)
            logger.info(f"Cancelled call {call_id}")
            return True
        
        return False
    
    async def get_user_call_stats(self, user_id: int, hours: int = 24) -> Dict[str, Any]:
        """Get call statistics for a user."""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        user_calls = [
            call for call in self.call_history.values()
            if call.user_id == user_id and call.created_at >= cutoff_time
        ]
        
        if not user_calls:
            return {
                "total_calls": 0,
                "successful_calls": 0,
                "failed_calls": 0,
                "average_response_time_ms": 0,
                "total_tokens_used": 0,
                "total_cost": 0.0
            }
        
        successful_calls = [call for call in user_calls if call.status == CallStatus.COMPLETED]
        failed_calls = [call for call in user_calls if call.status == CallStatus.FAILED]
        
        response_times = [call.response_time_ms for call in successful_calls if call.response_time_ms]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        return {
            "total_calls": len(user_calls),
            "successful_calls": len(successful_calls),
            "failed_calls": len(failed_calls),
            "average_response_time_ms": avg_response_time,
            "total_tokens_used": sum(call.tokens_used or 0 for call in user_calls),
            "total_cost": sum(call.cost or 0 for call in user_calls)
        }
    
    async def get_system_stats(self) -> Dict[str, Any]:
        """Get system-wide call statistics."""
        queue_stats = await self.call_queue.get_queue_stats()
        
        recent_calls = [
            call for call in self.call_history.values()
            if call.created_at >= datetime.utcnow() - timedelta(hours=1)
        ]
        
        return {
            "queue_stats": queue_stats,
            "recent_hour_calls": len(recent_calls),
            "total_historical_calls": len(self.call_history),
            "success_rate": len([
                call for call in recent_calls if call.status == CallStatus.COMPLETED
            ]) / len(recent_calls) if recent_calls else 0
        }
    
    async def _process_calls(self):
        """Background task to process calls from the queue."""
        logger.info("Starting LLM call processor")
        
        while not self._shutdown:
            try:
                # Check rate limits
                if not await self.rate_limiter.can_make_call():
                    await asyncio.sleep(1)  # Wait before checking again
                    continue
                
                # Get next call
                call = await self.call_queue.dequeue()
                if not call:
                    await asyncio.sleep(0.1)  # No calls available
                    continue
                
                # Process the call
                await self._process_single_call(call)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in call processor: {e}")
                await asyncio.sleep(1)
        
        logger.info("LLM call processor stopped")
    
    async def _process_single_call(self, call: LLMCall):
        """Process a single LLM call."""
        try:
            start_time = time.time()
            
            # Record rate limit
            await self.rate_limiter.record_call()
            
            # Make the actual API call (simplified - integrate with pydantic-ai)
            result = await self._make_api_call(call)
            
            # Calculate metrics
            response_time_ms = int((time.time() - start_time) * 1000)
            
            # Update call with success
            call.status = CallStatus.COMPLETED
            call.result = result
            call.response_time_ms = response_time_ms
            call.tokens_used = self._estimate_tokens(call.prompt, result)
            call.cost = self._estimate_cost(call.tokens_used)
            
            logger.info(f"Completed call {call.id} in {response_time_ms}ms")
            
        except asyncio.TimeoutError:
            call.status = CallStatus.TIMEOUT
            call.error = "Request timed out"
            logger.warning(f"Call {call.id} timed out")
            
        except Exception as e:
            call.status = CallStatus.FAILED
            call.error = str(e)
            logger.error(f"Call {call.id} failed: {e}")
            
            # Retry logic
            if call.retry_count < call.max_retries:
                call.retry_count += 1
                call.status = CallStatus.QUEUED
                await self.call_queue.enqueue(call)
                logger.info(f"Retrying call {call.id} (attempt {call.retry_count}/{call.max_retries})")
                return
        
        finally:
            await self.call_queue.complete_call(call.id)
    
    async def _make_api_call(self, call: LLMCall) -> str:
        """
        Make the actual API call to the LLM service.
        This is a simplified implementation - in practice, integrate with pydantic-ai.
        """
        # Simulate API call delay
        await asyncio.sleep(0.5)
        
        # Simulate response based on call type
        if "generate" in call.prompt.lower():
            return "Generated response with multiple ideas and detailed analysis."
        elif "evaluate" in call.prompt.lower():
            return "Evaluation response with scores, strengths, and recommendations."
        elif "iterate" in call.prompt.lower():
            return "Iteration response with improved version and changes made."
        else:
            return f"Response to prompt: {call.prompt[:100]}..."
    
    def _estimate_tokens(self, prompt: str, response: str) -> int:
        """Estimate token usage (rough approximation)."""
        return int((len(prompt) + len(response)) / 4)  # Rough estimate
    
    def _estimate_cost(self, tokens: int) -> float:
        """Estimate cost based on token usage."""
        # GPT-4 pricing (approximate)
        return tokens * 0.00003  # $0.03 per 1K tokens


# Global instance
llm_call_handler = LLMCallHandler()


class BatchCallHandler:
    """Handler for batch processing of multiple LLM calls."""
    
    def __init__(self, handler: LLMCallHandler):
        self.handler = handler
    
    async def submit_batch(
        self,
        calls: List[Dict[str, Any]],
        user_id: int,
        batch_priority: CallPriority = CallPriority.NORMAL
    ) -> List[str]:
        """
        Submit a batch of calls for processing.
        
        Args:
            calls: List of call specifications
            user_id: User ID
            batch_priority: Priority for all calls in batch
            
        Returns:
            List of call IDs
        """
        call_ids = []
        
        for call_spec in calls:
            call_id = await self.handler.submit_call(
                prompt=call_spec.get("prompt", ""),
                user_id=user_id,
                model=call_spec.get("model"),
                temperature=call_spec.get("temperature"),
                max_tokens=call_spec.get("max_tokens"),
                priority=batch_priority,
                metadata=call_spec.get("metadata", {})
            )
            call_ids.append(call_id)
        
        logger.info(f"Submitted batch of {len(call_ids)} calls for user {user_id}")
        return call_ids
    
    async def wait_for_batch(
        self,
        call_ids: List[str],
        timeout_seconds: int = 600
    ) -> List[Optional[str]]:
        """
        Wait for all calls in a batch to complete.
        
        Args:
            call_ids: List of call IDs to wait for
            timeout_seconds: Maximum time to wait for all calls
            
        Returns:
            List of results (None for failed calls)
        """
        tasks = [
            self.handler.wait_for_call(call_id, timeout_seconds)
            for call_id in call_ids
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to None
        return [
            result if not isinstance(result, Exception) else None
            for result in results
        ]