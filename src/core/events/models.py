"""Event models for the event-driven architecture."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from dataclasses import dataclass, field
from bson import ObjectId


class EventType(str, Enum):
    """Core event types for the Eva system."""
    
    # Eva Core Events
    TASK_QUEUED = "task.queued"
    TASK_STARTED = "task.started"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    WORKFLOW_INITIATED = "workflow.initiated"
    USER_REQUEST_RECEIVED = "user.request.received"
    
    # Tool Execution Events
    TOOL_EXECUTION_REQUESTED = "tool.execution.requested"
    TOOL_EXECUTION_STARTED = "tool.execution.started"
    TOOL_EXECUTION_COMPLETED = "tool.execution.completed"
    TOOL_EXECUTION_FAILED = "tool.execution.failed"
    
    # Memory Events
    MEMORY_UPDATE_QUEUED = "memory.update.queued"
    MEMORY_INDEXED = "memory.indexed"
    MEMORY_RETRIEVED = "memory.retrieved"
    MEMORY_ANALYZED = "memory.analyzed"
    
    # Integration Events
    SLACK_MESSAGE_RECEIVED = "slack.message.received"
    SLACK_COMMAND_RECEIVED = "slack.command.received"
    SLACK_RESPONSE_READY = "slack.response.ready"
    WEBHOOK_RECEIVED = "webhook.received"
    INTEGRATION_EVENT = "integration.event"
    
    # Connector Events
    CONNECTOR_EVENT = "connector.event"
    EMAIL_EVENT = "email.event"
    CALENDAR_EVENT = "calendar.event"
    TASK_EVENT = "task.event"


class Priority(str, Enum):
    """Event processing priority levels."""
    
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class EventStatus(str, Enum):
    """Event processing status."""
    
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class Event:
    """Core event model for the event-driven system."""
    
    event_type: EventType
    source: str  # Source system (eva_core, slack, connector_name, etc)
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    event_id: str = field(default_factory=lambda: str(ObjectId()))
    correlation_id: Optional[str] = None  # Links related events
    priority: Priority = Priority.MEDIUM
    status: EventStatus = EventStatus.PENDING
    retry_count: int = 0
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for MongoDB storage."""
        return {
            "_id": self.event_id,
            "event_type": self.event_type.value,
            "source": self.source,
            "data": self.data,
            "timestamp": self.timestamp,
            "correlation_id": self.correlation_id,
            "priority": self.priority.value,
            "status": self.status.value,
            "retry_count": self.retry_count,
            "error": self.error,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Event":
        """Create event from MongoDB document."""
        return cls(
            event_id=data.get("_id", str(ObjectId())),
            event_type=EventType(data["event_type"]),
            source=data["source"],
            data=data["data"],
            timestamp=data.get("timestamp", datetime.utcnow()),
            correlation_id=data.get("correlation_id"),
            priority=Priority(data.get("priority", Priority.MEDIUM.value)),
            status=EventStatus(data.get("status", EventStatus.PENDING.value)),
            retry_count=data.get("retry_count", 0),
            error=data.get("error"),
            metadata=data.get("metadata", {})
        )


@dataclass
class TaskEvent(Event):
    """Specialized event for task queue operations."""
    
    def __init__(self, task_type: str, task_data: Dict[str, Any], **kwargs):
        super().__init__(
            event_type=EventType.TASK_QUEUED,
            source="task_queue",
            data={
                "task_type": task_type,
                "task_data": task_data
            },
            **kwargs
        )


@dataclass
class WorkflowEvent(Event):
    """Specialized event for workflow orchestration."""
    
    def __init__(self, workflow_id: str, workflow_type: str, steps: list, **kwargs):
        super().__init__(
            event_type=EventType.WORKFLOW_INITIATED,
            source="workflow_engine",
            data={
                "workflow_id": workflow_id,
                "workflow_type": workflow_type,
                "steps": steps,
                "current_step": 0
            },
            correlation_id=workflow_id,
            **kwargs
        )