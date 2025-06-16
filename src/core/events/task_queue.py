"""Task Queue implementation for asynchronous task management."""

import asyncio
import logging
from typing import Any, Callable, Dict, Optional, Set
from datetime import datetime
from dataclasses import dataclass, field

from .event_bus import EventBus
from .models import Event, EventType, Priority, TaskEvent, EventStatus

logger = logging.getLogger(__name__)


@dataclass
class TaskResult:
    """Result of a task execution."""
    
    task_id: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    duration_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class TaskQueue:
    """
    Manages asynchronous task execution through the event system.
    
    Features:
    - Priority-based task scheduling
    - Concurrent task execution with limits
    - Task result tracking
    - Integration with EventBus
    """
    
    def __init__(
        self,
        event_bus: EventBus,
        max_concurrent_tasks: int = 10,
        task_timeout: float = 300.0  # 5 minutes default
    ):
        self.event_bus = event_bus
        self.max_concurrent = max_concurrent_tasks
        self.task_timeout = task_timeout
        self.task_handlers: Dict[str, Callable] = {}
        self.active_tasks: Set[str] = set()
        self.task_results: Dict[str, TaskResult] = {}
        self._running = False
        self._processor_task: Optional[asyncio.Task] = None
        
    def register_task_handler(self, task_type: str, handler: Callable) -> None:
        """
        Register a handler for a specific task type.
        
        Args:
            task_type: The type of task to handle
            handler: Async function to execute the task
        """
        self.task_handlers[task_type] = handler
        logger.info(f"Registered handler for task type: {task_type}")
    
    async def queue_task(
        self,
        task_type: str,
        task_data: Dict[str, Any],
        priority: Priority = Priority.MEDIUM,
        correlation_id: Optional[str] = None
    ) -> str:
        """
        Queue a task for asynchronous execution.
        
        Args:
            task_type: Type of task to execute
            task_data: Data for the task
            priority: Task priority
            correlation_id: Optional correlation ID for related tasks
            
        Returns:
            Task ID (event ID)
        """
        task_event = TaskEvent(
            task_type=task_type,
            task_data=task_data,
            priority=priority,
            correlation_id=correlation_id
        )
        
        task_id = await self.event_bus.publish(task_event)
        logger.info(f"Queued task {task_type} with ID {task_id}")
        
        return task_id
    
    async def start(self):
        """Start the task queue processor."""
        if self._running:
            logger.warning("Task queue is already running")
            return
            
        self._running = True
        
        # Subscribe to task events
        self.event_bus.subscribe(EventType.TASK_QUEUED, self._handle_task_event)
        
        # Start the processor
        self._processor_task = asyncio.create_task(self._process_tasks())
        
        logger.info("Task queue started")
    
    async def stop(self):
        """Stop the task queue processor."""
        self._running = False
        
        if self._processor_task:
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass
        
        # Wait for active tasks to complete
        if self.active_tasks:
            logger.info(f"Waiting for {len(self.active_tasks)} active tasks to complete")
            await asyncio.sleep(1)  # Give tasks a chance to complete
        
        logger.info("Task queue stopped")
    
    async def _handle_task_event(self, event: Event):
        """Handle incoming task events."""
        if event.event_type != EventType.TASK_QUEUED:
            return
            
        # Check if we can process this task
        if len(self.active_tasks) >= self.max_concurrent:
            # Re-queue the event with a delay
            logger.debug(f"Task queue full, delaying task {event.event_id}")
            await asyncio.sleep(0.1)
            return
        
        # Process the task
        asyncio.create_task(self._execute_task(event))
    
    async def _process_tasks(self):
        """Main task processing loop."""
        while self._running:
            try:
                # Clean up completed tasks
                completed_tasks = []
                for task_id in self.active_tasks:
                    if task_id in self.task_results:
                        completed_tasks.append(task_id)
                
                for task_id in completed_tasks:
                    self.active_tasks.remove(task_id)
                
                # Log queue status periodically
                if len(self.active_tasks) > 0:
                    logger.debug(f"Active tasks: {len(self.active_tasks)}/{self.max_concurrent}")
                
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error in task processor: {e}")
                await asyncio.sleep(5)
    
    async def _execute_task(self, event: Event):
        """Execute a single task."""
        task_id = event.event_id
        start_time = datetime.utcnow()
        
        # Mark task as active
        self.active_tasks.add(task_id)
        
        try:
            # Publish task started event
            await self.event_bus.publish(Event(
                event_type=EventType.TASK_STARTED,
                source="task_queue",
                data={
                    "task_id": task_id,
                    "task_type": event.data.get("task_type"),
                    "started_at": start_time
                },
                correlation_id=event.correlation_id
            ))
            
            # Get task handler
            task_type = event.data.get("task_type")
            handler = self.task_handlers.get(task_type)
            
            if not handler:
                raise ValueError(f"No handler registered for task type: {task_type}")
            
            # Execute with timeout
            task_data = event.data.get("task_data", {})
            result = await asyncio.wait_for(
                handler(task_data),
                timeout=self.task_timeout
            )
            
            # Calculate duration
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # Store result
            self.task_results[task_id] = TaskResult(
                task_id=task_id,
                success=True,
                result=result,
                duration_ms=duration_ms
            )
            
            # Publish completion event
            await self.event_bus.publish(Event(
                event_type=EventType.TASK_COMPLETED,
                source="task_queue",
                data={
                    "task_id": task_id,
                    "task_type": task_type,
                    "result": result,
                    "duration_ms": duration_ms
                },
                correlation_id=event.correlation_id
            ))
            
            logger.info(f"Task {task_id} completed successfully in {duration_ms:.2f}ms")
            
        except asyncio.TimeoutError:
            error_msg = f"Task timeout after {self.task_timeout}s"
            await self._handle_task_failure(event, error_msg)
            
        except Exception as e:
            error_msg = f"Task execution error: {str(e)}"
            await self._handle_task_failure(event, error_msg)
            
        finally:
            # Remove from active tasks
            self.active_tasks.discard(task_id)
    
    async def _handle_task_failure(self, event: Event, error: str):
        """Handle a failed task."""
        task_id = event.event_id
        
        # Store failure result
        self.task_results[task_id] = TaskResult(
            task_id=task_id,
            success=False,
            error=error
        )
        
        # Publish failure event
        await self.event_bus.publish(Event(
            event_type=EventType.TASK_FAILED,
            source="task_queue",
            data={
                "task_id": task_id,
                "task_type": event.data.get("task_type"),
                "error": error
            },
            correlation_id=event.correlation_id
        ))
        
        logger.error(f"Task {task_id} failed: {error}")
    
    async def wait_for_task(self, task_id: str, timeout: float = 60.0) -> TaskResult:
        """
        Wait for a task to complete and return its result.
        
        Args:
            task_id: The task ID to wait for
            timeout: Maximum time to wait in seconds
            
        Returns:
            TaskResult object
            
        Raises:
            TimeoutError: If task doesn't complete within timeout
        """
        start_time = datetime.utcnow()
        
        while (datetime.utcnow() - start_time).total_seconds() < timeout:
            if task_id in self.task_results:
                return self.task_results[task_id]
            
            await asyncio.sleep(0.1)
        
        raise TimeoutError(f"Task {task_id} did not complete within {timeout}s")
    
    async def wait_for_workflow(
        self,
        correlation_id: str,
        expected_tasks: int,
        timeout: float = 300.0
    ) -> Dict[str, TaskResult]:
        """
        Wait for all tasks in a workflow to complete.
        
        Args:
            correlation_id: Correlation ID of the workflow
            expected_tasks: Number of tasks expected in the workflow
            timeout: Maximum time to wait
            
        Returns:
            Dictionary of task results by task ID
        """
        # Query completed tasks for this workflow
        completed_events = await self.event_bus.query_events(
            event_type=EventType.TASK_COMPLETED,
            correlation_id=correlation_id
        )
        
        failed_events = await self.event_bus.query_events(
            event_type=EventType.TASK_FAILED,
            correlation_id=correlation_id
        )
        
        all_events = completed_events + failed_events
        
        if len(all_events) >= expected_tasks:
            # All tasks completed
            results = {}
            for event in all_events:
                task_id = event.data.get("task_id")
                if task_id in self.task_results:
                    results[task_id] = self.task_results[task_id]
            return results
        
        # Not all tasks completed yet
        await asyncio.sleep(0.5)
        
        # Recursive call with reduced timeout
        new_timeout = timeout - 0.5
        if new_timeout <= 0:
            raise TimeoutError(f"Workflow {correlation_id} did not complete within timeout")
        
        return await self.wait_for_workflow(correlation_id, expected_tasks, new_timeout)
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get current queue statistics."""
        return {
            "active_tasks": len(self.active_tasks),
            "max_concurrent": self.max_concurrent,
            "completed_tasks": len(self.task_results),
            "task_handlers": list(self.task_handlers.keys()),
            "queue_utilization": len(self.active_tasks) / self.max_concurrent
        }