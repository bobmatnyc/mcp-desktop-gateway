"""
Integrated MongoDB Adaptive Prompts System for py-mcp-bridge
Leverages your existing MongoDB infrastructure and configuration patterns
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, ConfigDict
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
import uuid
import time
import logging
from dataclasses import dataclass

# Import your existing config
from src.eva_agent.core.config import EvaConfig, get_config

logger = logging.getLogger(__name__)

class PromptExecution(BaseModel):
    """Document model for prompt executions - integrates with your existing MongoDB"""
    execution_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    connector_name: str
    prompt_name: str
    version: str = "1.0"
    arguments: Dict[str, Any]
    result: Dict[str, Any]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    user_context: Optional[Dict[str, Any]] = None
    performance_metrics: Optional[Dict[str, Any]] = None
    execution_time_ms: Optional[float] = None
    success: bool = True
    error: Optional[str] = None
    # Additional fields for integration
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    
    model_config = ConfigDict()

class UserFeedback(BaseModel):
    """Document model for user feedback"""
    feedback_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    execution_id: str
    feedback_type: str  # 'positive', 'negative', 'rating', 'text'
    rating: Optional[int] = Field(None, ge=1, le=5)
    text_feedback: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    
    model_config = ConfigDict()

@dataclass
class PerformanceMetrics:
    """Performance metrics for prompts"""
    total_executions: int
    success_rate: float
    avg_execution_time: float
    avg_rating: Optional[float]
    positive_feedback_ratio: float
    last_used: datetime

class IntegratedAdaptiveManager:
    """
    Adaptive prompts manager that integrates with your existing MongoDB setup
    Uses your existing connection patterns and configuration
    """
    
    def __init__(self, config: Optional[EvaConfig] = None):
        """Initialize with your existing configuration pattern"""
        self.config = config or get_config()
        self.client: Optional[AsyncIOMotorClient] = None
        self.db: Optional[AsyncIOMotorDatabase] = None
        
        # Use your existing MongoDB configuration
        self.connection_string = self.config.mongodb.uri
        self.database_name = self.config.mongodb.database
        
        # Adaptive prompts collections
        self.executions_collection_name = "prompt_executions"
        self.feedback_collection_name = "user_feedback"
        self.templates_collection_name = "prompt_templates"
        
        # Collection references (initialized in connect())
        self.executions = None
        self.feedback = None
        self.templates = None
        
    async def connect(self):
        """Connect using your existing pattern from WorkingMemory"""
        try:
            self.client = AsyncIOMotorClient(self.connection_string)
            self.db = self.client[self.database_name]
            
            # Initialize collections
            self.executions = self.db[self.executions_collection_name]
            self.feedback = self.db[self.feedback_collection_name]
            self.templates = self.db[self.templates_collection_name]
            
            # Test connection (same as your existing pattern)
            await self.client.admin.command("ping")
            
            # Create indexes
            await self.ensure_indexes()
            
            logger.info(
                "Adaptive prompts system connected to MongoDB",
                database=self.database_name,
                collections=[
                    self.executions_collection_name,
                    self.feedback_collection_name,
                    self.templates_collection_name
                ]
            )
            
        except Exception as e:
            logger.error("Failed to connect adaptive prompts to MongoDB", error_msg=str(e))
            raise
    
    async def disconnect(self):
        """Disconnect using your existing pattern"""
        if self.client:
            self.client.close()
            logger.info("Adaptive prompts disconnected from MongoDB")
    
    async def ensure_indexes(self):
        """Create necessary indexes for performance"""
        # Executions collection indexes
        await self.executions.create_index([
            ("connector_name", 1),
            ("prompt_name", 1),
            ("timestamp", -1)
        ])
        await self.executions.create_index("execution_id", unique=True)
        await self.executions.create_index("timestamp")
        await self.executions.create_index([("success", 1), ("timestamp", -1)])
        
        # Feedback collection indexes
        await self.feedback.create_index("execution_id")
        await self.feedback.create_index("timestamp")
        await self.feedback.create_index([
            ("feedback_type", 1),
            ("timestamp", -1)
        ])
        
        # Templates collection indexes (for future use)
        await self.templates.create_index([
            ("connector_name", 1),
            ("prompt_name", 1),
            ("version", 1)
        ], unique=True)
        
        logger.info("Created adaptive prompts indexes")

    async def record_execution(
        self,
        connector_name: str,
        prompt_name: str,
        arguments: Dict[str, Any],
        result: Dict[str, Any],
        execution_time_ms: Optional[float] = None,
        user_context: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> str:
        """Record a prompt execution"""
        execution = PromptExecution(
            connector_name=connector_name,
            prompt_name=prompt_name,
            arguments=arguments,
            result=result,
            execution_time_ms=execution_time_ms,
            user_context=user_context,
            success=success,
            error=error,
            user_id=user_id,
            session_id=session_id
        )
        
        await self.executions.insert_one(execution.dict())
        logger.info(
            "Recorded prompt execution",
            execution_id=execution.execution_id[:8],
            connector=connector_name,
            prompt=prompt_name,
            success=success
        )
        return execution.execution_id

    async def record_feedback(
        self,
        execution_id: str,
        feedback_type: str,
        rating: Optional[int] = None,
        text_feedback: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> str:
        """Record user feedback for an execution"""
        feedback = UserFeedback(
            execution_id=execution_id,
            feedback_type=feedback_type,
            rating=rating,
            text_feedback=text_feedback,
            user_id=user_id,
            session_id=session_id
        )
        
        await self.feedback.insert_one(feedback.dict())
        logger.info(
            "Recorded user feedback",
            feedback_id=feedback.feedback_id[:8],
            execution_id=execution_id[:8],
            type=feedback_type,
            rating=rating
        )
        return feedback.feedback_id

    async def get_connector_analytics(
        self,
        connector_name: Optional[str] = None,
        days_back: int = 7
    ) -> Dict[str, Any]:
        """Get analytics for connector(s) - similar to your memory stats pattern"""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_back)
        
        match_stage = {"timestamp": {"$gte": cutoff_date}}
        if connector_name:
            match_stage["connector_name"] = connector_name
        
        # Executions by connector
        exec_pipeline = [
            {"$match": match_stage},
            {
                "$group": {
                    "_id": "$connector_name",
                    "total_executions": {"$sum": 1},
                    "successful_executions": {"$sum": {"$cond": ["$success", 1, 0]}},
                    "avg_execution_time": {"$avg": "$execution_time_ms"}
                }
            }
        ]
        
        # Feedback summary
        feedback_pipeline = [
            {"$match": {"timestamp": {"$gte": cutoff_date}}},
            {
                "$group": {
                    "_id": "$feedback_type",
                    "count": {"$sum": 1}
                }
            }
        ]
        
        exec_results = await self.executions.aggregate(exec_pipeline).to_list(None)
        feedback_results = await self.feedback.aggregate(feedback_pipeline).to_list(None)
        
        # Format results similar to your existing stats methods
        connector_stats = {}
        for result in exec_results:
            connector = result["_id"]
            connector_stats[connector] = {
                "total_executions": result["total_executions"],
                "success_rate": result["successful_executions"] / result["total_executions"],
                "avg_execution_time_ms": result.get("avg_execution_time", 0)
            }
        
        feedback_summary = {result["_id"]: result["count"] for result in feedback_results}
        
        return {
            "period_days": days_back,
            "connector_stats": connector_stats,
            "feedback_summary": feedback_summary,
            "total_feedback": sum(feedback_summary.values())
        }

    async def cleanup_old_data(self, days_to_keep: int = 90):
        """Clean up old data - similar to your expired memory cleanup"""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
        
        # Delete old executions
        exec_result = await self.executions.delete_many({
            "timestamp": {"$lt": cutoff_date}
        })
        
        # Delete orphaned feedback
        feedback_result = await self.feedback.delete_many({
            "timestamp": {"$lt": cutoff_date}
        })
        
        logger.info(
            "Cleaned up old adaptive data",
            deleted_executions=exec_result.deleted_count,
            deleted_feedback=feedback_result.deleted_count,
            cutoff_date=cutoff_date.isoformat()
        )
        
        return {
            "deleted_executions": exec_result.deleted_count,
            "deleted_feedback": feedback_result.deleted_count
        }

# Enhanced BaseConnector Mixin for your existing connectors
class AdaptiveConnectorMixin:
    """
    Mixin to add adaptive capabilities to your existing connectors
    Integrates seamlessly with your BaseConnector pattern
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.adaptive_manager: Optional[IntegratedAdaptiveManager] = None
        self._adaptive_enabled = False
    
    async def _initialize_adaptive(self, config: Optional[EvaConfig] = None):
        """Initialize adaptive capabilities using your existing config"""
        try:
            self.adaptive_manager = IntegratedAdaptiveManager(config)
            await self.adaptive_manager.connect()
            self._adaptive_enabled = True
            logger.info(f"Adaptive capabilities initialized for {self.name}")
        except Exception as e:
            logger.warning(f"Failed to initialize adaptive for {self.name}", error_msg=str(e))
            self._adaptive_enabled = False
    
    async def _execute_with_adaptive_tracking(
        self,
        prompt_name: str,
        arguments: Dict[str, Any],
        execution_func,
        user_context: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute a tool with adaptive tracking"""
        start_time = time.time()
        execution_id = None
        
        try:
            # Execute the actual tool
            result = await execution_func(arguments)
            execution_time_ms = (time.time() - start_time) * 1000
            
            # Record successful execution
            if self._adaptive_enabled and self.adaptive_manager:
                execution_id = await self.adaptive_manager.record_execution(
                    connector_name=self.name,
                    prompt_name=prompt_name,
                    arguments=arguments,
                    result=result,
                    execution_time_ms=execution_time_ms,
                    user_context=user_context,
                    success=True,
                    user_id=user_id,
                    session_id=session_id
                )
            
            # Add feedback UI to result (following your existing patterns)
            if execution_id:
                result["_adaptive"] = {
                    "execution_id": execution_id,
                    "feedback_instructions": self._generate_feedback_ui(execution_id)
                }
            
            return result
            
        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            
            # Record failed execution
            if self._adaptive_enabled and self.adaptive_manager:
                execution_id = await self.adaptive_manager.record_execution(
                    connector_name=self.name,
                    prompt_name=prompt_name,
                    arguments=arguments,
                    result={"error": str(e)},
                    execution_time_ms=execution_time_ms,
                    user_context=user_context,
                    success=False,
                    error=str(e),
                    user_id=user_id,
                    session_id=session_id
                )
            
            raise
    
    def _generate_feedback_ui(self, execution_id: str) -> str:
        """Generate feedback UI instructions"""
        short_id = execution_id[:8]
        return f"""
        
📝 **Rate this response** (ID: {short_id}):
👍 Good: `feedback {short_id} thumbs_up`
👎 Poor: `feedback {short_id} thumbs_down`  
⭐ Rate 1-5: `feedback {short_id} rating X`
💬 Comment: `feedback {short_id} text "your comment"`
        """

# Global adaptive manager instance (following your global config pattern)
_adaptive_manager: Optional[IntegratedAdaptiveManager] = None

async def get_adaptive_manager() -> IntegratedAdaptiveManager:
    """Get global adaptive manager instance"""
    global _adaptive_manager
    if _adaptive_manager is None:
        _adaptive_manager = IntegratedAdaptiveManager()
        await _adaptive_manager.connect()
    return _adaptive_manager

async def initialize_adaptive_system(config: Optional[EvaConfig] = None) -> IntegratedAdaptiveManager:
    """Initialize the adaptive system with your existing config"""
    manager = IntegratedAdaptiveManager(config)
    await manager.connect()
    return manager
