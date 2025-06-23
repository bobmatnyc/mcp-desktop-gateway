"""
Feedback collection system for prompt training
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
import asyncio
from pathlib import Path
import logging

from .models import Feedback, FeedbackType, PromptType

logger = logging.getLogger(__name__)


class FeedbackCollector:
    """Collects and manages feedback for prompt improvement"""
    
    def __init__(self, storage_path: str = "prompt_training/feedback"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.feedback_queue: List[Feedback] = []
        self.batch_size = 10
        self._running = False
        
    async def start(self):
        """Start the feedback collection service"""
        self._running = True
        logger.info("Feedback collector started")
        
        # Start background task for processing feedback
        asyncio.create_task(self._process_feedback_queue())
        
    async def stop(self):
        """Stop the feedback collection service"""
        self._running = False
        await self._flush_queue()
        logger.info("Feedback collector stopped")
        
    async def collect_user_feedback(
        self,
        prompt_id: str,
        prompt_type: PromptType,
        rating: float,
        message: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Feedback:
        """Collect user feedback on a prompt"""
        feedback = Feedback(
            prompt_id=prompt_id,
            prompt_type=prompt_type,
            feedback_type=FeedbackType.USER_RATING,
            rating=rating,
            message=message,
            input_data=context.get("input", {}) if context else {},
            output_data=context.get("output", {}) if context else {},
            user_id=context.get("user_id") if context else None,
            session_id=context.get("session_id") if context else None,
            connector_name=context.get("connector_name") if context else None,
            tool_name=context.get("tool_name") if context else None
        )
        
        await self._add_feedback(feedback)
        return feedback
        
    async def collect_error(
        self,
        prompt_id: str,
        prompt_type: PromptType,
        error_details: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Feedback:
        """Collect error information for a prompt"""
        feedback = Feedback(
            prompt_id=prompt_id,
            prompt_type=prompt_type,
            feedback_type=FeedbackType.ERROR_REPORT,
            rating=0.0,  # Errors are negative signals
            error_details=error_details,
            message=error_details.get("error_message"),
            input_data=context.get("input", {}) if context else {},
            output_data=context.get("output", {}) if context else {},
            execution_time=context.get("execution_time") if context else None,
            connector_name=context.get("connector_name") if context else None,
            tool_name=context.get("tool_name") if context else None
        )
        
        await self._add_feedback(feedback)
        return feedback
        
    async def collect_success(
        self,
        prompt_id: str,
        prompt_type: PromptType,
        execution_time: float,
        context: Optional[Dict[str, Any]] = None
    ) -> Feedback:
        """Collect success metrics for a prompt"""
        feedback = Feedback(
            prompt_id=prompt_id,
            prompt_type=prompt_type,
            feedback_type=FeedbackType.SUCCESS_REPORT,
            rating=1.0,  # Success is a positive signal
            execution_time=execution_time,
            input_data=context.get("input", {}) if context else {},
            output_data=context.get("output", {}) if context else {},
            connector_name=context.get("connector_name") if context else None,
            tool_name=context.get("tool_name") if context else None
        )
        
        await self._add_feedback(feedback)
        return feedback
        
    async def collect_improvement_suggestion(
        self,
        prompt_id: str,
        prompt_type: PromptType,
        suggestion: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Feedback:
        """Collect improvement suggestions from users"""
        feedback = Feedback(
            prompt_id=prompt_id,
            prompt_type=prompt_type,
            feedback_type=FeedbackType.IMPROVEMENT_SUGGESTION,
            message=suggestion,
            input_data=context.get("input", {}) if context else {},
            user_id=context.get("user_id") if context else None,
            session_id=context.get("session_id") if context else None
        )
        
        await self._add_feedback(feedback)
        return feedback
        
    async def collect_automated_metric(
        self,
        prompt_id: str,
        prompt_type: PromptType,
        metric_name: str,
        metric_value: float,
        context: Optional[Dict[str, Any]] = None
    ) -> Feedback:
        """Collect automated metrics (e.g., from monitoring)"""
        feedback = Feedback(
            prompt_id=prompt_id,
            prompt_type=prompt_type,
            feedback_type=FeedbackType.AUTOMATED_METRIC,
            rating=metric_value,
            message=f"{metric_name}: {metric_value}",
            input_data={"metric_name": metric_name, "metric_value": metric_value},
            output_data=context or {}
        )
        
        await self._add_feedback(feedback)
        return feedback
        
    async def get_feedback_for_prompt(
        self,
        prompt_id: str,
        feedback_type: Optional[FeedbackType] = None,
        limit: int = 100
    ) -> List[Feedback]:
        """Retrieve feedback for a specific prompt"""
        feedback_dir = self.storage_path / prompt_id
        if not feedback_dir.exists():
            return []
            
        feedback_list = []
        for file_path in sorted(feedback_dir.glob("*.json"), reverse=True)[:limit]:
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    feedback = self._dict_to_feedback(data)
                    if feedback_type is None or feedback.feedback_type == feedback_type:
                        feedback_list.append(feedback)
            except Exception as e:
                logger.error(f"Error loading feedback from {file_path}: {e}")
                
        return feedback_list
        
    async def get_feedback_summary(self, prompt_id: str) -> Dict[str, Any]:
        """Get summary statistics for prompt feedback"""
        feedback_list = await self.get_feedback_for_prompt(prompt_id)
        
        if not feedback_list:
            return {
                "total_feedback": 0,
                "average_rating": None,
                "error_count": 0,
                "success_count": 0
            }
            
        ratings = [f.rating for f in feedback_list if f.rating is not None]
        errors = [f for f in feedback_list if f.feedback_type == FeedbackType.ERROR_REPORT]
        successes = [f for f in feedback_list if f.feedback_type == FeedbackType.SUCCESS_REPORT]
        
        return {
            "total_feedback": len(feedback_list),
            "average_rating": sum(ratings) / len(ratings) if ratings else None,
            "error_count": len(errors),
            "success_count": len(successes),
            "error_rate": len(errors) / len(feedback_list) if feedback_list else 0,
            "success_rate": len(successes) / len(feedback_list) if feedback_list else 0,
            "feedback_types": {
                ft.value: len([f for f in feedback_list if f.feedback_type == ft])
                for ft in FeedbackType
            }
        }
        
    async def _add_feedback(self, feedback: Feedback):
        """Add feedback to the processing queue"""
        self.feedback_queue.append(feedback)
        
        # Process immediately if queue is full
        if len(self.feedback_queue) >= self.batch_size:
            await self._flush_queue()
            
    async def _process_feedback_queue(self):
        """Background task to process feedback queue"""
        while self._running:
            try:
                if self.feedback_queue:
                    await self._flush_queue()
                await asyncio.sleep(5)  # Check every 5 seconds
            except Exception as e:
                logger.error(f"Error processing feedback queue: {e}")
                
    async def _flush_queue(self):
        """Save all queued feedback to disk"""
        if not self.feedback_queue:
            return
            
        feedback_to_save = self.feedback_queue.copy()
        self.feedback_queue.clear()
        
        for feedback in feedback_to_save:
            try:
                await self._save_feedback(feedback)
            except Exception as e:
                logger.error(f"Error saving feedback {feedback.id}: {e}")
                # Re-add to queue for retry
                self.feedback_queue.append(feedback)
                
    async def _save_feedback(self, feedback: Feedback):
        """Save feedback to disk"""
        # Create directory for prompt if it doesn't exist
        prompt_dir = self.storage_path / feedback.prompt_id
        prompt_dir.mkdir(parents=True, exist_ok=True)
        
        # Save feedback as JSON
        filename = f"{feedback.timestamp.isoformat()}_{feedback.id}.json"
        file_path = prompt_dir / filename
        
        with open(file_path, 'w') as f:
            json.dump(self._feedback_to_dict(feedback), f, indent=2)
            
        logger.debug(f"Saved feedback {feedback.id} to {file_path}")
        
    def _feedback_to_dict(self, feedback: Feedback) -> Dict[str, Any]:
        """Convert Feedback object to dictionary"""
        return {
            "id": feedback.id,
            "prompt_id": feedback.prompt_id,
            "prompt_type": feedback.prompt_type.value,
            "feedback_type": feedback.feedback_type.value,
            "timestamp": feedback.timestamp.isoformat(),
            "rating": feedback.rating,
            "message": feedback.message,
            "error_details": feedback.error_details,
            "input_data": feedback.input_data,
            "output_data": feedback.output_data,
            "execution_time": feedback.execution_time,
            "user_id": feedback.user_id,
            "session_id": feedback.session_id,
            "connector_name": feedback.connector_name,
            "tool_name": feedback.tool_name
        }
        
    def _dict_to_feedback(self, data: Dict[str, Any]) -> Feedback:
        """Convert dictionary to Feedback object"""
        return Feedback(
            id=data["id"],
            prompt_id=data["prompt_id"],
            prompt_type=PromptType(data["prompt_type"]),
            feedback_type=FeedbackType(data["feedback_type"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            rating=data.get("rating"),
            message=data.get("message"),
            error_details=data.get("error_details"),
            input_data=data.get("input_data", {}),
            output_data=data.get("output_data", {}),
            execution_time=data.get("execution_time"),
            user_id=data.get("user_id"),
            session_id=data.get("session_id"),
            connector_name=data.get("connector_name"),
            tool_name=data.get("tool_name")
        )