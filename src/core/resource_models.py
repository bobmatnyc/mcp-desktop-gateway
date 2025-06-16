# src/core/resource_models.py
"""
Resource models for MCP Bridge - extends core models with resource support
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field
from datetime import datetime


class ResourceContentType(str, Enum):
    """Types of resource content"""
    TEXT = "text"
    JSON = "json"
    HTML = "html"
    MARKDOWN = "markdown"
    IMAGE = "image"
    BINARY = "binary"


class ResourceContent(BaseModel):
    """Content of a resource"""
    type: ResourceContentType
    data: Union[str, bytes, Dict[str, Any]]
    encoding: Optional[str] = None  # base64, utf-8, etc.
    mimeType: Optional[str] = None


class ResourceDefinition(BaseModel):
    """Definition of a resource that can be read"""
    uri: str = Field(..., description="Unique URI for the resource")
    name: str = Field(..., description="Human-readable name") 
    description: str = Field(..., description="Description of what this resource provides")
    mimeType: str = Field(..., description="MIME type of resource content")
    annotations: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")


class ResourceResult(BaseModel):
    """Result from reading a resource"""
    uri: str
    content: ResourceContent
    metadata: Optional[Dict[str, Any]] = None
    last_modified: Optional[datetime] = None
    size: Optional[int] = None


class ResourceError(BaseModel):
    """Error when reading a resource"""
    uri: str
    error_code: str
    error_message: str
    details: Optional[Dict[str, Any]] = None


# Gmail-specific resource data models
class GmailInboxSummary(BaseModel):
    """Gmail inbox summary data"""
    total_messages: int
    unread_count: int
    important_count: int
    starred_count: int
    spam_count: int
    trash_count: int
    last_sync: datetime
    storage_used_mb: float
    storage_limit_mb: float


class GmailFrequentContacts(BaseModel):
    """Gmail frequent contacts data"""
    contacts: List[Dict[str, Any]]
    last_updated: datetime
    analysis_period_days: int


class GmailUnreadSummary(BaseModel):
    """Gmail unread messages summary"""
    messages: List[Dict[str, Any]]
    total_count: int
    by_sender: Dict[str, int]
    by_label: Dict[str, int]
    oldest_unread: Optional[datetime]
    most_recent: Optional[datetime]


# Calendar-specific resource data models
class CalendarTodaySchedule(BaseModel):
    """Today's calendar schedule data"""
    date: str
    total_events: int
    total_duration_minutes: int
    schedule_density: float  # 0.0 to 1.0
    events: List[Dict[str, Any]]
    free_time_blocks: List[Dict[str, Any]]
    next_event: Optional[Dict[str, Any]]
    conflicts: List[Dict[str, Any]]


class CalendarUpcomingConflicts(BaseModel):
    """Upcoming calendar conflicts"""
    conflicts: List[Dict[str, Any]]
    total_conflicts: int
    date_range: Dict[str, str]
    resolution_suggestions: List[str]


class CalendarWeeklyOverview(BaseModel):
    """Weekly calendar overview"""
    week_start: str
    week_end: str
    total_events: int
    average_daily_hours: float
    busiest_day: str
    lightest_day: str
    daily_breakdown: Dict[str, Dict[str, Any]]
    recurring_patterns: List[Dict[str, Any]]
