"""Event-driven server integration for the unified backend."""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from fastapi import FastAPI, HTTPException, BackgroundTasks
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel

from src.core.events import (
    EventSystemManager, Event, EventType, Priority,
    EventBus, TaskQueue
)
from ..core.logging_config import logger

# Request/Response models
class EventRequest(BaseModel):
    """Request to publish an event."""
    event_type: str
    source: str
    data: Dict[str, Any]
    priority: str = "medium"
    correlation_id: Optional[str] = None


class TaskRequest(BaseModel):
    """Request to queue a task."""
    task_type: str
    task_data: Dict[str, Any]
    priority: str = "medium"
    correlation_id: Optional[str] = None


class EventResponse(BaseModel):
    """Response for event operations."""
    event_id: str
    status: str
    message: Optional[str] = None


class TaskResponse(BaseModel):
    """Response for task operations."""
    task_id: str
    status: str
    result: Optional[Dict[str, Any]] = None


class EventDrivenServer:
    """
    Adds event-driven capabilities to the unified backend server.
    """
    
    def __init__(self, app: FastAPI, mongo_uri: str = "mongodb://localhost:27017"):
        self.app = app
        self.mongo_uri = mongo_uri
        self.event_system: Optional[EventSystemManager] = None
        self.event_bus: Optional[EventBus] = None
        self.task_queue: Optional[TaskQueue] = None
        
        # Add startup/shutdown handlers
        app.add_event_handler("startup", self._startup)
        app.add_event_handler("shutdown", self._shutdown)
        
        # Register routes
        self._register_routes()
    
    async def _startup(self):
        """Initialize event system on server startup."""
        try:
            # Create MongoDB client
            client = AsyncIOMotorClient(self.mongo_uri)
            db = client["py_mcp_bridge_events"]
            
            # Initialize event system
            self.event_system = EventSystemManager(db)
            await self.event_system.initialize()
            
            self.event_bus = self.event_system.get_event_bus()
            self.task_queue = self.event_system.get_task_queue()
            
            logger.info("Event system initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize event system: {e}")
            raise
    
    async def _shutdown(self):
        """Cleanup event system on server shutdown."""
        if self.event_system:
            await self.event_system.shutdown()
            logger.info("Event system shut down")
    
    def _register_routes(self):
        """Register event-related API routes."""
        
        @self.app.post("/api/events", response_model=EventResponse)
        async def publish_event(request: EventRequest):
            """Publish an event to the event bus."""
            if not self.event_bus:
                raise HTTPException(status_code=503, detail="Event system not initialized")
            
            try:
                # Create event
                event = Event(
                    event_type=EventType(request.event_type),
                    source=request.source,
                    data=request.data,
                    priority=Priority(request.priority),
                    correlation_id=request.correlation_id
                )
                
                # Publish
                event_id = await self.event_bus.publish(event)
                
                return EventResponse(
                    event_id=event_id,
                    status="published",
                    message=f"Event {request.event_type} published successfully"
                )
                
            except Exception as e:
                logger.error(f"Failed to publish event: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/tasks", response_model=TaskResponse)
        async def queue_task(request: TaskRequest, background_tasks: BackgroundTasks):
            """Queue a task for asynchronous execution."""
            if not self.task_queue:
                raise HTTPException(status_code=503, detail="Task queue not initialized")
            
            try:
                # Queue task
                task_id = await self.task_queue.queue_task(
                    task_type=request.task_type,
                    task_data=request.task_data,
                    priority=Priority(request.priority),
                    correlation_id=request.correlation_id
                )
                
                return TaskResponse(
                    task_id=task_id,
                    status="queued"
                )
                
            except Exception as e:
                logger.error(f"Failed to queue task: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/tasks/{task_id}", response_model=TaskResponse)
        async def get_task_status(task_id: str):
            """Get the status of a task."""
            if not self.task_queue:
                raise HTTPException(status_code=503, detail="Task queue not initialized")
            
            try:
                # Check if task is in results
                if task_id in self.task_queue.task_results:
                    result = self.task_queue.task_results[task_id]
                    return TaskResponse(
                        task_id=task_id,
                        status="completed" if result.success else "failed",
                        result={"data": result.result} if result.success else {"error": result.error}
                    )
                
                # Check if task is active
                if task_id in self.task_queue.active_tasks:
                    return TaskResponse(
                        task_id=task_id,
                        status="processing"
                    )
                
                # Task not found
                raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Failed to get task status: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/events/stats")
        async def get_event_stats():
            """Get event system statistics."""
            if not self.event_bus:
                raise HTTPException(status_code=503, detail="Event system not initialized")
            
            try:
                stats = await self.event_bus.get_event_stats()
                queue_stats = self.task_queue.get_queue_stats()
                
                return {
                    "event_stats": stats,
                    "queue_stats": queue_stats,
                    "timestamp": datetime.utcnow()
                }
                
            except Exception as e:
                logger.error(f"Failed to get stats: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/events/recent")
        async def get_recent_events(limit: int = 100):
            """Get recent events."""
            if not self.event_bus:
                raise HTTPException(status_code=503, detail="Event system not initialized")
            
            try:
                events = await self.event_bus.query_events(limit=limit)
                
                return {
                    "events": [
                        {
                            "event_id": event.event_id,
                            "event_type": event.event_type.value,
                            "source": event.source,
                            "status": event.status.value,
                            "timestamp": event.timestamp,
                            "correlation_id": event.correlation_id
                        }
                        for event in events
                    ],
                    "count": len(events)
                }
                
            except Exception as e:
                logger.error(f"Failed to get recent events: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.websocket("/ws/events")
        async def event_stream(websocket):
            """WebSocket endpoint for real-time event streaming."""
            await websocket.accept()
            
            if not self.event_bus:
                await websocket.send_json({
                    "error": "Event system not initialized"
                })
                await websocket.close()
                return
            
            # Subscribe to all events
            event_queue = asyncio.Queue()
            
            async def event_handler(event: Event):
                await event_queue.put(event)
            
            self.event_bus.subscribe_all(event_handler)
            
            try:
                while True:
                    # Wait for events
                    event = await event_queue.get()
                    
                    # Send to websocket
                    await websocket.send_json({
                        "event_id": event.event_id,
                        "event_type": event.event_type.value,
                        "source": event.source,
                        "data": event.data,
                        "timestamp": event.timestamp.isoformat()
                    })
                    
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
            finally:
                await websocket.close()


def integrate_event_system(app: FastAPI, mongo_uri: str = "mongodb://localhost:27017"):
    """
    Integrate event system with an existing FastAPI app.
    
    Args:
        app: FastAPI application instance
        mongo_uri: MongoDB connection URI
        
    Returns:
        EventDrivenServer instance
    """
    return EventDrivenServer(app, mongo_uri)