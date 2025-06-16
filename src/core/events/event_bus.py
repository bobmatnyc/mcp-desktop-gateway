"""Event Bus implementation using MongoDB Change Streams."""

import asyncio
import logging
from typing import Callable, Dict, List, Optional, AsyncIterator
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING
from pymongo.errors import PyMongoError
from datetime import datetime, timedelta

from .models import Event, EventType, EventStatus, Priority

logger = logging.getLogger(__name__)


class EventBus:
    """
    Central event bus for the Eva system using MongoDB Change Streams.
    
    This class provides:
    - Event publishing to MongoDB
    - Real-time event subscription via Change Streams
    - Event filtering and routing
    - Resume token management for reliability
    """
    
    def __init__(
        self,
        database: AsyncIOMotorDatabase,
        collection_name: str = "events"
    ):
        self.db = database
        self.collection = database[collection_name]
        self.handlers: Dict[EventType, List[Callable]] = {}
        self.global_handlers: List[Callable] = []
        self.change_streams: List[asyncio.Task] = []
        self._resume_token = None
        self._running = False
        
    async def initialize(self):
        """Initialize the event bus and create necessary indexes."""
        try:
            # Create indexes for efficient querying
            await self.collection.create_index([("timestamp", ASCENDING)])
            await self.collection.create_index([("event_type", ASCENDING)])
            await self.collection.create_index([("status", ASCENDING)])
            await self.collection.create_index([("correlation_id", ASCENDING)])
            await self.collection.create_index([("priority", ASCENDING)])
            
            # Create TTL index for automatic cleanup (30 days)
            await self.collection.create_index(
                [("timestamp", ASCENDING)],
                expireAfterSeconds=30 * 24 * 60 * 60
            )
            
            logger.info("Event bus initialized successfully")
        except PyMongoError as e:
            logger.error(f"Failed to initialize event bus: {e}")
            raise
    
    async def publish(self, event: Event) -> str:
        """
        Publish an event to the event bus.
        
        Args:
            event: The event to publish
            
        Returns:
            The event ID
        """
        try:
            event_dict = event.to_dict()
            result = await self.collection.insert_one(event_dict)
            logger.debug(f"Published event {event.event_type} with ID {event.event_id}")
            return event.event_id
        except PyMongoError as e:
            logger.error(f"Failed to publish event: {e}")
            raise
    
    def subscribe(self, event_type: EventType, handler: Callable) -> None:
        """
        Subscribe to a specific event type.
        
        Args:
            event_type: The event type to subscribe to
            handler: Async function to handle the event
        """
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)
        logger.debug(f"Subscribed handler to {event_type}")
    
    def subscribe_all(self, handler: Callable) -> None:
        """
        Subscribe to all events.
        
        Args:
            handler: Async function to handle events
        """
        self.global_handlers.append(handler)
        logger.debug("Subscribed global handler")
    
    async def start(self):
        """Start the event bus and begin processing events."""
        if self._running:
            logger.warning("Event bus is already running")
            return
            
        self._running = True
        
        # Start change stream processing
        stream_task = asyncio.create_task(self._process_change_stream())
        self.change_streams.append(stream_task)
        
        # Start event processor for pending events
        processor_task = asyncio.create_task(self._process_pending_events())
        self.change_streams.append(processor_task)
        
        logger.info("Event bus started")
    
    async def stop(self):
        """Stop the event bus and clean up resources."""
        self._running = False
        
        # Cancel all change stream tasks
        for task in self.change_streams:
            task.cancel()
            
        # Wait for tasks to complete
        await asyncio.gather(*self.change_streams, return_exceptions=True)
        
        self.change_streams.clear()
        logger.info("Event bus stopped")
    
    async def _process_change_stream(self):
        """Process MongoDB change stream for real-time events."""
        pipeline = [
            {"$match": {
                "operationType": "insert",
                "fullDocument.event_type": {"$exists": True}
            }}
        ]
        
        while self._running:
            try:
                async with self.collection.watch(
                    pipeline=pipeline,
                    full_document='updateLookup',
                    resume_after=self._resume_token
                ) as stream:
                    async for change in stream:
                        if not self._running:
                            break
                            
                        # Save resume token
                        self._resume_token = change.get("_id")
                        
                        # Process the event
                        document = change.get("fullDocument")
                        if document:
                            event = Event.from_dict(document)
                            await self._dispatch_event(event)
                            
            except PyMongoError as e:
                logger.error(f"Change stream error: {e}")
                if self._running:
                    # Wait before retrying
                    await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"Unexpected error in change stream: {e}")
                if self._running:
                    await asyncio.sleep(5)
    
    async def _process_pending_events(self):
        """Process any pending events that weren't handled."""
        while self._running:
            try:
                # Find pending events
                cursor = self.collection.find({
                    "status": EventStatus.PENDING.value,
                    "timestamp": {"$lt": datetime.utcnow() - timedelta(seconds=5)}
                }).sort("priority", -1).limit(10)
                
                async for document in cursor:
                    event = Event.from_dict(document)
                    
                    # Update status to processing
                    await self.collection.update_one(
                        {"_id": event.event_id},
                        {"$set": {"status": EventStatus.PROCESSING.value}}
                    )
                    
                    # Dispatch the event
                    await self._dispatch_event(event)
                    
                # Wait before next check
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error processing pending events: {e}")
                await asyncio.sleep(5)
    
    async def _dispatch_event(self, event: Event):
        """
        Dispatch an event to registered handlers.
        
        Args:
            event: The event to dispatch
        """
        handlers = self.handlers.get(event.event_type, []) + self.global_handlers
        
        if not handlers:
            logger.debug(f"No handlers for event type {event.event_type}")
            return
        
        # Run handlers concurrently
        tasks = []
        for handler in handlers:
            task = asyncio.create_task(self._run_handler(handler, event))
            tasks.append(task)
        
        # Wait for all handlers to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check for failures
        failures = [r for r in results if isinstance(r, Exception)]
        
        if failures:
            logger.error(f"Event {event.event_id} had {len(failures)} handler failures")
            await self._handle_failed_event(event, str(failures[0]))
        else:
            await self._mark_event_completed(event)
    
    async def _run_handler(self, handler: Callable, event: Event):
        """
        Run a single event handler with error handling.
        
        Args:
            handler: The handler function
            event: The event to process
        """
        try:
            await handler(event)
        except Exception as e:
            logger.error(f"Handler error for event {event.event_id}: {e}")
            raise
    
    async def _mark_event_completed(self, event: Event):
        """Mark an event as completed."""
        try:
            await self.collection.update_one(
                {"_id": event.event_id},
                {"$set": {
                    "status": EventStatus.COMPLETED.value,
                    "completed_at": datetime.utcnow()
                }}
            )
        except PyMongoError as e:
            logger.error(f"Failed to mark event completed: {e}")
    
    async def _handle_failed_event(self, event: Event, error: str):
        """Handle a failed event with retry logic."""
        try:
            if event.retry_count < 3:
                # Retry the event
                await self.collection.update_one(
                    {"_id": event.event_id},
                    {"$set": {
                        "status": EventStatus.RETRYING.value,
                        "retry_count": event.retry_count + 1,
                        "error": error,
                        "retry_at": datetime.utcnow() + timedelta(seconds=5 * (event.retry_count + 1))
                    }}
                )
            else:
                # Mark as failed
                await self.collection.update_one(
                    {"_id": event.event_id},
                    {"$set": {
                        "status": EventStatus.FAILED.value,
                        "error": error,
                        "failed_at": datetime.utcnow()
                    }}
                )
        except PyMongoError as e:
            logger.error(f"Failed to handle failed event: {e}")
    
    async def query_events(
        self,
        event_type: Optional[EventType] = None,
        correlation_id: Optional[str] = None,
        status: Optional[EventStatus] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Event]:
        """
        Query historical events.
        
        Args:
            event_type: Filter by event type
            correlation_id: Filter by correlation ID
            status: Filter by status
            start_time: Filter by start time
            end_time: Filter by end time
            limit: Maximum number of events to return
            
        Returns:
            List of matching events
        """
        query = {}
        
        if event_type:
            query["event_type"] = event_type.value
        if correlation_id:
            query["correlation_id"] = correlation_id
        if status:
            query["status"] = status.value
        if start_time or end_time:
            timestamp_query = {}
            if start_time:
                timestamp_query["$gte"] = start_time
            if end_time:
                timestamp_query["$lte"] = end_time
            query["timestamp"] = timestamp_query
        
        events = []
        cursor = self.collection.find(query).sort("timestamp", -1).limit(limit)
        
        async for document in cursor:
            events.append(Event.from_dict(document))
        
        return events
    
    async def get_event_stats(self) -> Dict[str, any]:
        """Get statistics about events in the system."""
        pipeline = [
            {
                "$group": {
                    "_id": {
                        "event_type": "$event_type",
                        "status": "$status"
                    },
                    "count": {"$sum": 1}
                }
            }
        ]
        
        stats = {}
        async for result in self.collection.aggregate(pipeline):
            event_type = result["_id"]["event_type"]
            status = result["_id"]["status"]
            count = result["count"]
            
            if event_type not in stats:
                stats[event_type] = {}
            stats[event_type][status] = count
        
        return stats