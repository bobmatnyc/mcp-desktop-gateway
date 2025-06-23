"""
Automatic prompt training system that monitors feedback and triggers training
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from pathlib import Path
import logging
import statistics

from .feedback_collector import FeedbackCollector
from .prompt_manager import PromptManager
from .prompt_trainer import PromptTrainer
from .evaluation import PromptEvaluator
from .models import PromptVersion, FeedbackType

logger = logging.getLogger(__name__)


class AutomaticPromptTrainer:
    """Automatically trains prompts based on feedback thresholds and patterns"""
    
    def __init__(
        self,
        feedback_collector: FeedbackCollector,
        prompt_manager: PromptManager,
        openai_api_key: Optional[str] = None,
        config_path: Optional[str] = None
    ):
        self.feedback_collector = feedback_collector
        self.prompt_manager = prompt_manager
        self.prompt_trainer = PromptTrainer(
            feedback_collector, 
            prompt_manager,
            openai_api_key=openai_api_key
        )
        self.prompt_evaluator = PromptEvaluator(
            prompt_manager,
            openai_api_key=openai_api_key
        )
        
        # Load configuration
        self.config = self._load_config(config_path)
        
        # State tracking
        self.training_queue: Set[str] = set()
        self.last_training_time: Dict[str, datetime] = {}
        self.training_history: Dict[str, List[Dict[str, Any]]] = {}
        self._running = False
        
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Load auto-training configuration"""
        if config_path and Path(config_path).exists():
            with open(config_path, 'r') as f:
                return json.load(f)
                
        # Default configuration
        return {
            "enabled": True,
            "check_interval_seconds": 3600,  # Check every hour
            "min_feedback_for_training": 10,
            "min_hours_between_training": 24,
            "training_triggers": {
                "error_rate_threshold": 0.2,  # Train if >20% errors
                "low_rating_threshold": 0.6,  # Train if avg rating <0.6
                "feedback_count_threshold": 50,  # Train after 50 feedback items
                "improvement_suggestion_count": 3  # Train after 3 suggestions
            },
            "approach_selection": {
                "error_dominant": "adversarial",  # Use adversarial for high errors
                "low_rating": "reinforcement",  # Use reinforcement for low ratings
                "many_suggestions": "meta_prompt",  # Use meta-prompt for suggestions
                "default": "few_shot"  # Default to few-shot
            },
            "auto_deploy": {
                "enabled": False,  # Require manual deployment by default
                "min_improvement": 0.1,  # 10% improvement required
                "min_safety_score": 0.9,  # High safety requirement
                "require_human_review": True
            },
            "notification": {
                "log_training_events": True,
                "save_training_reports": True
            }
        }
        
    async def start(self):
        """Start the automatic training service"""
        if not self.config.get("enabled", True):
            logger.info("Automatic prompt training is disabled")
            return
            
        self._running = True
        logger.info("Starting automatic prompt trainer")
        
        # Start monitoring loop
        asyncio.create_task(self._monitoring_loop())
        
    async def stop(self):
        """Stop the automatic training service"""
        self._running = False
        logger.info("Stopping automatic prompt trainer")
        
    async def _monitoring_loop(self):
        """Main loop that monitors feedback and triggers training"""
        while self._running:
            try:
                await self._check_all_prompts()
                
                # Wait for next check interval
                await asyncio.sleep(self.config["check_interval_seconds"])
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(60)  # Wait a minute before retrying
                
    async def _check_all_prompts(self):
        """Check all prompts for training eligibility"""
        logger.debug("Checking all prompts for training eligibility")
        
        # Get all active prompts
        active_prompts = self.prompt_manager._active_prompts
        
        for prompt_id, version in active_prompts.items():
            try:
                # Check if prompt is eligible for training
                if await self._should_train_prompt(prompt_id, version):
                    # Add to training queue
                    self.training_queue.add(prompt_id)
                    
                    # Trigger training
                    asyncio.create_task(self._train_prompt(prompt_id))
                    
            except Exception as e:
                logger.error(f"Error checking prompt {prompt_id}: {e}")
                
    async def _should_train_prompt(self, prompt_id: str, version: PromptVersion) -> bool:
        """Determine if a prompt should be trained"""
        # Check if already in queue
        if prompt_id in self.training_queue:
            return False
            
        # Check minimum time between training
        last_training = self.last_training_time.get(prompt_id)
        if last_training:
            hours_since = (datetime.now() - last_training).total_seconds() / 3600
            if hours_since < self.config["min_hours_between_training"]:
                return False
                
        # Get feedback summary
        summary = await self.feedback_collector.get_feedback_summary(prompt_id)
        
        # Check if enough feedback
        if summary["total_feedback"] < self.config["min_feedback_for_training"]:
            return False
            
        # Check training triggers
        triggers = self.config["training_triggers"]
        
        # High error rate
        if summary["error_rate"] > triggers["error_rate_threshold"]:
            logger.info(f"Prompt {prompt_id} triggered training: high error rate ({summary['error_rate']:.1%})")
            return True
            
        # Low average rating
        if summary["average_rating"] and summary["average_rating"] < triggers["low_rating_threshold"]:
            logger.info(f"Prompt {prompt_id} triggered training: low rating ({summary['average_rating']:.2f})")
            return True
            
        # Many feedback items
        if summary["total_feedback"] >= triggers["feedback_count_threshold"]:
            logger.info(f"Prompt {prompt_id} triggered training: feedback count ({summary['total_feedback']})")
            return True
            
        # Many improvement suggestions
        suggestion_count = summary["feedback_types"].get(FeedbackType.IMPROVEMENT_SUGGESTION.value, 0)
        if suggestion_count >= triggers["improvement_suggestion_count"]:
            logger.info(f"Prompt {prompt_id} triggered training: suggestions ({suggestion_count})")
            return True
            
        return False
        
    async def _train_prompt(self, prompt_id: str):
        """Train a specific prompt"""
        try:
            logger.info(f"Starting automatic training for {prompt_id}")
            
            # Determine best training approach
            approach = await self._select_training_approach(prompt_id)
            
            # Run training
            training_result = await self.prompt_trainer.train_prompt(
                prompt_id=prompt_id,
                training_approach=approach,
                min_feedback_count=self.config["min_feedback_for_training"]
            )
            
            if not training_result or training_result.status != "completed":
                logger.error(f"Training failed for {prompt_id}")
                return
                
            # Get the new version
            new_version_id = training_result.new_version_id
            if not new_version_id:
                logger.error(f"No new version created for {prompt_id}")
                return
                
            # Find the new version
            versions = self.prompt_manager.get_all_versions(prompt_id)
            new_version = next((v for v in versions if v.id == new_version_id), None)
            
            if not new_version:
                logger.error(f"Could not find new version {new_version_id}")
                return
                
            # Evaluate the new version
            current_version = self.prompt_manager.get_active_prompt(prompt_id)
            evaluation_result = await self.prompt_evaluator.evaluate_version(
                new_version,
                baseline_version=current_version
            )
            
            # Create training report
            report = {
                "prompt_id": prompt_id,
                "timestamp": datetime.now().isoformat(),
                "training_approach": approach,
                "current_version": current_version.version,
                "new_version": new_version.version,
                "training_metrics": training_result.metrics,
                "evaluation": {
                    "recommendation": evaluation_result.recommendation,
                    "confidence": evaluation_result.confidence,
                    "improvement_delta": evaluation_result.improvement_delta,
                    "safety_score": evaluation_result.safety_score
                }
            }
            
            # Save training report
            if self.config["notification"]["save_training_reports"]:
                await self._save_training_report(prompt_id, report)
                
            # Check auto-deployment
            if await self._should_auto_deploy(evaluation_result, report):
                logger.info(f"Auto-deploying {prompt_id} v{new_version.version}")
                self.prompt_manager.deploy_version(prompt_id, new_version.version)
                report["auto_deployed"] = True
            else:
                logger.info(f"Manual review required for {prompt_id} v{new_version.version}")
                report["auto_deployed"] = False
                
            # Update tracking
            self.last_training_time[prompt_id] = datetime.now()
            
            # Add to history
            if prompt_id not in self.training_history:
                self.training_history[prompt_id] = []
            self.training_history[prompt_id].append(report)
            
            # Log summary
            logger.info(f"Training complete for {prompt_id}: "
                       f"v{current_version.version} -> v{new_version.version} "
                       f"({evaluation_result.recommendation})")
            
        except Exception as e:
            logger.error(f"Error training prompt {prompt_id}: {e}")
            
        finally:
            # Remove from queue
            self.training_queue.discard(prompt_id)
            
    async def _select_training_approach(self, prompt_id: str) -> str:
        """Select the best training approach based on feedback patterns"""
        # Get feedback summary
        summary = await self.feedback_collector.get_feedback_summary(prompt_id)
        
        approach_config = self.config["approach_selection"]
        
        # High error rate -> Adversarial training
        if summary["error_rate"] > 0.3:
            return approach_config["error_dominant"]
            
        # Low ratings -> Reinforcement learning
        if summary["average_rating"] and summary["average_rating"] < 0.5:
            return approach_config["low_rating"]
            
        # Many suggestions -> Meta-prompt optimization
        suggestion_count = summary["feedback_types"].get(
            FeedbackType.IMPROVEMENT_SUGGESTION.value, 0
        )
        if suggestion_count >= 5:
            return approach_config["many_suggestions"]
            
        # Default to few-shot learning
        return approach_config["default"]
        
    async def _should_auto_deploy(
        self,
        evaluation_result,
        training_report: Dict[str, Any]
    ) -> bool:
        """Determine if a new version should be auto-deployed"""
        auto_deploy_config = self.config["auto_deploy"]
        
        # Check if auto-deploy is enabled
        if not auto_deploy_config["enabled"]:
            return False
            
        # Check safety score
        if evaluation_result.safety_score < auto_deploy_config["min_safety_score"]:
            logger.info(f"Auto-deploy blocked: safety score too low "
                       f"({evaluation_result.safety_score:.2f} < {auto_deploy_config['min_safety_score']})")
            return False
            
        # Check improvement
        avg_improvement = 0.0
        if evaluation_result.improvement_delta:
            improvements = [v for k, v in evaluation_result.improvement_delta.items() 
                          if k != "latency_p50_delta"]  # Exclude latency
            if improvements:
                avg_improvement = statistics.mean(improvements)
                
        if avg_improvement < auto_deploy_config["min_improvement"]:
            logger.info(f"Auto-deploy blocked: insufficient improvement "
                       f"({avg_improvement:.1%} < {auto_deploy_config['min_improvement']:.1%})")
            return False
            
        # Check recommendation
        if evaluation_result.recommendation not in ["deploy", "test_more"]:
            logger.info(f"Auto-deploy blocked: recommendation is {evaluation_result.recommendation}")
            return False
            
        # Check human review requirement
        if auto_deploy_config["require_human_review"]:
            logger.info("Auto-deploy blocked: human review required")
            return False
            
        return True
        
    async def _save_training_report(self, prompt_id: str, report: Dict[str, Any]):
        """Save training report to disk"""
        reports_dir = Path("prompt_training/reports")
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = reports_dir / f"{prompt_id}_{timestamp}.json"
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
            
        logger.debug(f"Saved training report to {report_file}")
        
    def get_training_status(self) -> Dict[str, Any]:
        """Get current status of automatic training"""
        return {
            "enabled": self.config.get("enabled", True),
            "running": self._running,
            "training_queue": list(self.training_queue),
            "recent_training": {
                prompt_id: last_time.isoformat()
                for prompt_id, last_time in self.last_training_time.items()
            },
            "config": self.config
        }
        
    def get_prompt_training_history(self, prompt_id: str) -> List[Dict[str, Any]]:
        """Get training history for a specific prompt"""
        return self.training_history.get(prompt_id, [])
        
    async def trigger_manual_training(self, prompt_id: str, approach: Optional[str] = None):
        """Manually trigger training for a prompt"""
        if prompt_id in self.training_queue:
            logger.warning(f"Prompt {prompt_id} is already in training queue")
            return
            
        # Override approach if specified
        if approach:
            original_config = self.config["approach_selection"].copy()
            self.config["approach_selection"]["default"] = approach
            
        try:
            self.training_queue.add(prompt_id)
            await self._train_prompt(prompt_id)
        finally:
            # Restore original config
            if approach:
                self.config["approach_selection"] = original_config