"""Integration helpers for transitioning to event-driven architecture."""

import asyncio
import logging
from typing import Any, Dict, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase

from .event_bus import EventBus
from .task_queue import TaskQueue
from .models import Event, EventType, Priority

logger = logging.getLogger(__name__)


class EventSystemManager:
    """
    Manages the event-driven system components and provides
    a unified interface for integration.
    """
    
    def __init__(self, database: AsyncIOMotorDatabase):
        self.db = database
        self.event_bus = EventBus(database)
        self.task_queue = TaskQueue(self.event_bus)
        self._initialized = False
        
    async def initialize(self):
        """Initialize the event system."""
        if self._initialized:
            return
            
        # Initialize event bus
        await self.event_bus.initialize()
        
        # Start components
        await self.event_bus.start()
        await self.task_queue.start()
        
        self._initialized = True
        logger.info("Event system initialized")
    
    async def shutdown(self):
        """Shutdown the event system gracefully."""
        if not self._initialized:
            return
            
        # Stop components
        await self.task_queue.stop()
        await self.event_bus.stop()
        
        self._initialized = False
        logger.info("Event system shut down")
    
    def get_event_bus(self) -> EventBus:
        """Get the event bus instance."""
        return self.event_bus
    
    def get_task_queue(self) -> TaskQueue:
        """Get the task queue instance."""
        return self.task_queue


class EventDrivenToolExecutor:
    """
    Wrapper to make existing tool executors event-driven.
    """
    
    def __init__(self, event_bus: EventBus, task_queue: TaskQueue):
        self.event_bus = event_bus
        self.task_queue = task_queue
        
    async def execute_tool(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        priority: Priority = Priority.MEDIUM,
        wait_for_result: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Execute a tool through the event system.
        
        Args:
            tool_name: Name of the tool to execute
            tool_args: Arguments for the tool
            priority: Execution priority
            wait_for_result: Whether to wait for the result
            
        Returns:
            Tool execution result if wait_for_result is True
        """
        # Queue the tool execution
        task_id = await self.task_queue.queue_task(
            task_type="tool_execution",
            task_data={
                "tool_name": tool_name,
                "tool_args": tool_args
            },
            priority=priority
        )
        
        if wait_for_result:
            # Wait for completion
            result = await self.task_queue.wait_for_task(task_id)
            return result.result
        
        return {"task_id": task_id}


class EventDrivenMemoryManager:
    """
    Wrapper to make memory operations event-driven.
    """
    
    def __init__(self, event_bus: EventBus, task_queue: TaskQueue):
        self.event_bus = event_bus
        self.task_queue = task_queue
        
    async def store_memory(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        wait_for_completion: bool = False
    ) -> Optional[str]:
        """
        Store memory through the event system.
        
        Args:
            content: Memory content to store
            metadata: Optional metadata
            wait_for_completion: Whether to wait for storage completion
            
        Returns:
            Task ID or None if waiting for completion
        """
        task_id = await self.task_queue.queue_task(
            task_type="memory_update",
            task_data={
                "operation": "store",
                "content": content,
                "metadata": metadata or {}
            },
            priority=Priority.LOW
        )
        
        if wait_for_completion:
            await self.task_queue.wait_for_task(task_id)
            return None
            
        return task_id
    
    async def retrieve_memories(
        self,
        query: str,
        limit: int = 5
    ) -> Dict[str, Any]:
        """
        Retrieve memories through the event system.
        
        Args:
            query: Query string
            limit: Maximum number of memories
            
        Returns:
            Retrieved memories
        """
        task_id = await self.task_queue.queue_task(
            task_type="memory_update",
            task_data={
                "operation": "retrieve",
                "query": query,
                "limit": limit
            },
            priority=Priority.HIGH
        )
        
        result = await self.task_queue.wait_for_task(task_id)
        return result.result


class SlackEventAdapter:
    """
    Adapter for converting Slack events to Eva events.
    """
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        
    async def handle_slack_message(self, slack_event: Dict[str, Any]):
        """Convert Slack message to Eva event."""
        await self.event_bus.publish(Event(
            event_type=EventType.SLACK_MESSAGE_RECEIVED,
            source="slack",
            data={
                "channel": slack_event.get("channel"),
                "user": slack_event.get("user"),
                "text": slack_event.get("text"),
                "ts": slack_event.get("ts"),
                "thread_ts": slack_event.get("thread_ts")
            },
            priority=Priority.MEDIUM
        ))
    
    async def handle_slack_command(self, command: str, args: Dict[str, Any]):
        """Convert Slack command to Eva event."""
        await self.event_bus.publish(Event(
            event_type=EventType.SLACK_COMMAND_RECEIVED,
            source="slack",
            data={
                "command": command,
                "args": args,
                "channel": args.get("channel_id"),
                "user": args.get("user_id")
            },
            priority=Priority.HIGH
        ))


def create_event_driven_wrapper(original_function):
    """
    Decorator to make synchronous functions event-driven.
    
    Usage:
        @create_event_driven_wrapper
        async def my_function(data):
            # Original function logic
            return result
    """
    async def wrapper(event_bus: EventBus, *args, **kwargs):
        # Create event for function call
        await event_bus.publish(Event(
            event_type=EventType.INTEGRATION_EVENT,
            source="wrapper",
            data={
                "function": original_function.__name__,
                "args": args,
                "kwargs": kwargs
            }
        ))
        
        # Call original function
        result = await original_function(*args, **kwargs)
        
        # Publish completion event
        await event_bus.publish(Event(
            event_type=EventType.INTEGRATION_EVENT,
            source="wrapper",
            data={
                "function": original_function.__name__,
                "status": "completed",
                "result": result
            }
        ))
        
        return result
    
    return wrapper