"""
Data models for the prompt training system
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
import uuid


class FeedbackType(Enum):
    """Types of feedback that can be collected"""
    USER_RATING = "user_rating"
    ERROR_REPORT = "error_report"
    SUCCESS_REPORT = "success_report"
    IMPROVEMENT_SUGGESTION = "improvement_suggestion"
    AUTOMATED_METRIC = "automated_metric"


class PromptType(Enum):
    """Types of prompts in the system"""
    SYSTEM = "system"  # System-level prompts
    USER = "user"      # End-user facing prompts
    CONNECTOR = "connector"  # Connector-specific prompts


@dataclass
class Feedback:
    """Represents feedback on a prompt execution"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    prompt_id: str = ""
    prompt_type: PromptType = PromptType.USER
    feedback_type: FeedbackType = FeedbackType.USER_RATING
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Feedback content
    rating: Optional[float] = None  # 0.0 to 1.0
    message: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    
    # Context
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    execution_time: Optional[float] = None
    
    # Metadata
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    connector_name: Optional[str] = None
    tool_name: Optional[str] = None


@dataclass
class PromptVersion:
    """Represents a version of a prompt"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    prompt_id: str = ""
    version: int = 1
    content: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Performance metrics
    avg_rating: float = 0.0
    success_rate: float = 0.0
    error_rate: float = 0.0
    usage_count: int = 0
    
    # Training info
    parent_version_id: Optional[str] = None
    training_data_ids: List[str] = field(default_factory=list)
    training_params: Dict[str, Any] = field(default_factory=dict)
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    deployed_at: Optional[datetime] = None
    retired_at: Optional[datetime] = None
    
    # Status
    is_active: bool = False
    is_experimental: bool = True


@dataclass
class TrainingRun:
    """Represents a training run for prompt improvement"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    prompt_id: str = ""
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    
    # Training configuration
    model_name: str = "gpt-4"
    training_approach: str = "few_shot"  # few_shot, fine_tuning, reinforcement
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    # Data
    feedback_ids: List[str] = field(default_factory=list)
    training_examples: List[Dict[str, Any]] = field(default_factory=list)
    validation_examples: List[Dict[str, Any]] = field(default_factory=list)
    
    # Results
    metrics: Dict[str, float] = field(default_factory=dict)
    new_version_id: Optional[str] = None
    status: str = "pending"  # pending, running, completed, failed
    error_message: Optional[str] = None


@dataclass
class EvaluationResult:
    """Results from evaluating a prompt version"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    prompt_version_id: str = ""
    evaluated_at: datetime = field(default_factory=datetime.now)
    
    # Test results
    test_cases_passed: int = 0
    test_cases_total: int = 0
    
    # Performance metrics
    latency_p50: float = 0.0
    latency_p95: float = 0.0
    token_usage_avg: int = 0
    
    # Quality metrics
    coherence_score: float = 0.0
    relevance_score: float = 0.0
    safety_score: float = 0.0
    
    # Comparison with baseline
    baseline_version_id: Optional[str] = None
    improvement_delta: Dict[str, float] = field(default_factory=dict)
    
    # Recommendation
    recommendation: str = "hold"  # deploy, test_more, hold, reject
    confidence: float = 0.0
    notes: Optional[str] = None