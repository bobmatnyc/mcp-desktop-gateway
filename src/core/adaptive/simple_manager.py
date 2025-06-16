"""
Simple MongoDB Adaptive Prompts Manager for py-mcp-bridge
Works with your existing MongoDB setup without additional dependencies
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, ConfigDict
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
import uuid
import time
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

class PromptExecution(BaseModel):
    """Document model for prompt executions"""
    execution_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    connector_name: str
    prompt_name: str
    version: str = "1.0"
    arguments: Dict[str, Any]
    result: Dict[str, Any]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    execution_time_ms: Optional[float] = None
    success: bool = True
    error: Optional[str] = None
    
    model_config = ConfigDict()

class UserFeedback(BaseModel):
    """Document model for user feedback"""
    feedback_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    execution_id: str
    feedback_type: str  # 'thumbs_up', 'thumbs_down', 'rating', 'text'
    rating: Optional[int] = Field(None, ge=1, le=5)
    text_feedback: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class SimpleAdaptiveManager:
    """Simple adaptive prompts manager using your existing MongoDB"""
    
    def __init__(
        self, 
        connection_string: str = "mongodb://localhost:27017",
        database_name: str = "eva_agent"
    ):
        self.connection_string = connection_string
        self.database_name = database_name
        self.client: Optional[AsyncIOMotorClient] = None
        self.db: Optional[AsyncIOMotorDatabase] = None
        self.executions = None
        self.feedback = None
        
    async def connect(self):
        """Connect to MongoDB"""
        try:
            self.client = AsyncIOMotorClient(self.connection_string)
            self.db = self.client[self.database_name]
            
            # Initialize collections
            self.executions = self.db["prompt_executions"]
            self.feedback = self.db["user_feedback"]
            
            # Test connection
            await self.client.admin.command("ping")
            
            # Create indexes
            await self.ensure_indexes()
            
            logger.info(f"Adaptive prompts connected to MongoDB: {self.database_name}")
            
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from MongoDB"""
        if self.client:
            self.client.close()
            
    async def ensure_indexes(self):
        """Create necessary indexes"""
        # Executions indexes
        await self.executions.create_index([
            ("connector_name", 1),
            ("prompt_name", 1),
            ("timestamp", -1)
        ])
        await self.executions.create_index("execution_id", unique=True)
        
        # Feedback indexes
        await self.feedback.create_index("execution_id")
        await self.feedback.create_index("timestamp")

    async def record_execution(
        self,
        connector_name: str,
        prompt_name: str,
        arguments: Dict[str, Any],
        result: Dict[str, Any],
        execution_time_ms: Optional[float] = None,
        success: bool = True,
        error: Optional[str] = None
    ) -> str:
        """Record a prompt execution"""
        execution = PromptExecution(
            connector_name=connector_name,
            prompt_name=prompt_name,
            arguments=arguments,
            result=result,
            execution_time_ms=execution_time_ms,
            success=success,
            error=error
        )
        
        await self.executions.insert_one(execution.dict())
        logger.info(f"Recorded execution {execution.execution_id[:8]} for {connector_name}.{prompt_name}")
        return execution.execution_id

    async def record_feedback(
        self,
        execution_id: str,
        feedback_type: str,
        rating: Optional[int] = None,
        text_feedback: Optional[str] = None
    ) -> str:
        """Record user feedback"""
        feedback = UserFeedback(
            execution_id=execution_id,
            feedback_type=feedback_type,
            rating=rating,
            text_feedback=text_feedback
        )
        
        await self.feedback.insert_one(feedback.dict())
        logger.info(f"Recorded feedback {feedback.feedback_id[:8]} for execution {execution_id[:8]}")
        return feedback.feedback_id

    async def get_stats(self) -> Dict[str, Any]:
        """Get basic statistics"""
        total_executions = await self.executions.count_documents({})
        total_feedback = await self.feedback.count_documents({})
        
        # Success rate
        successful = await self.executions.count_documents({"success": True})
        success_rate = successful / total_executions if total_executions > 0 else 0
        
        # Recent activity (last 7 days)
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        recent_executions = await self.executions.count_documents({
            "timestamp": {"$gte": week_ago}
        })
        
        return {
            "total_executions": total_executions,
            "total_feedback": total_feedback,
            "success_rate": success_rate,
            "recent_executions_7d": recent_executions
        }

# Simple connector mixin
class SimpleAdaptiveMixin:
    """Simple mixin to add adaptive capabilities to connectors"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.adaptive_manager: Optional[SimpleAdaptiveManager] = None
        self._adaptive_enabled = False
    
    async def _initialize_adaptive(self):
        """Initialize adaptive capabilities"""
        try:
            self.adaptive_manager = SimpleAdaptiveManager()
            await self.adaptive_manager.connect()
            self._adaptive_enabled = True
            # Suppress console output in chat mode or MCP mode
            import sys
            if os.environ.get("EVA_CHAT_MODE") != "true" and sys.stdin.isatty():
                print(f"✅ Adaptive tracking enabled for {self.name}")
        except Exception as e:
            import sys
            if os.environ.get("EVA_CHAT_MODE") != "true" and sys.stdin.isatty():
                print(f"⚠️  Failed to enable adaptive for {self.name}: {e}")
            self._adaptive_enabled = False
    
    async def _execute_with_tracking(
        self,
        prompt_name: str,
        arguments: Dict[str, Any],
        execution_func
    ) -> Dict[str, Any]:
        """Execute a tool with adaptive tracking"""
        start_time = time.time()
        
        try:
            # Execute the tool
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
                    success=True
                )
                
                # Add feedback instructions
                short_id = execution_id[:8]
                result["_adaptive_feedback"] = f"""
📝 Rate this response (ID: {short_id}):
• feedback {short_id} thumbs_up
• feedback {short_id} thumbs_down  
• feedback {short_id} rating 5
• feedback {short_id} text "your comment"
"""
            
            return result
            
        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            
            # Record failed execution
            if self._adaptive_enabled and self.adaptive_manager:
                await self.adaptive_manager.record_execution(
                    connector_name=self.name,
                    prompt_name=prompt_name,
                    arguments=arguments,
                    result={"error": str(e)},
                    execution_time_ms=execution_time_ms,
                    success=False,
                    error=str(e)
                )
            
            raise

# Feedback tool for MCP
class FeedbackTool:
    """Tool for recording user feedback"""
    
    def __init__(self, adaptive_manager: SimpleAdaptiveManager):
        self.adaptive_manager = adaptive_manager
    
    async def record_feedback(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """MCP tool to record feedback"""
        execution_id = arguments.get("execution_id")
        feedback_type = arguments.get("feedback_type")
        rating = arguments.get("rating")
        text_feedback = arguments.get("text_feedback")
        
        if not execution_id:
            return {"success": False, "error": "execution_id required"}
        
        try:
            feedback_id = await self.adaptive_manager.record_feedback(
                execution_id=execution_id,
                feedback_type=feedback_type,
                rating=rating,
                text_feedback=text_feedback
            )
            
            return {
                "success": True,
                "feedback_id": feedback_id,
                "message": f"✅ Feedback recorded for {execution_id[:8]}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"❌ Failed to record feedback: {e}"
            }
