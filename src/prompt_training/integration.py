"""
Integration module for prompt training system with MCP Gateway
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
import logging

from core.base_connector import BaseConnector
from core.models import PromptResult, ToolResponse
from .feedback_collector import FeedbackCollector
from .prompt_manager import PromptManager
from .auto_trainer import AutomaticPromptTrainer
from .models import PromptType, FeedbackType

logger = logging.getLogger(__name__)


class PromptTrainingMiddleware:
    """Middleware to integrate prompt training with MCP Gateway"""
    
    def __init__(self, enabled: bool = True, config_path: Optional[str] = None, openai_api_key: Optional[str] = None):
        self.enabled = enabled
        self.feedback_collector = FeedbackCollector()
        self.prompt_manager = PromptManager()
        
        # Initialize automatic trainer
        self.auto_trainer = AutomaticPromptTrainer(
            feedback_collector=self.feedback_collector,
            prompt_manager=self.prompt_manager,
            openai_api_key=openai_api_key,
            config_path=config_path
        )
        
        # Load configuration
        self.config = self._load_config(config_path)
        
        # Session tracking
        self.session_id = str(datetime.now().timestamp())
        
        # Start services
        if self.enabled:
            asyncio.create_task(self.feedback_collector.start())
            asyncio.create_task(self.auto_trainer.start())
            
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Load training configuration"""
        if config_path and Path(config_path).exists():
            with open(config_path, 'r') as f:
                return json.load(f)
                
        # Default configuration
        return {
            "auto_collect": True,
            "collect_errors": True,
            "collect_success": True,
            "min_execution_time": 0.1,  # Only collect for operations > 100ms
            "prompt_improvement_enabled": True
        }
        
    async def intercept_prompt_execution(
        self,
        connector: BaseConnector,
        prompt_name: str,
        arguments: Dict[str, Any],
        execute_fn
    ) -> PromptResult:
        """Intercept prompt execution for training data collection"""
        if not self.enabled or not self.config.get("auto_collect", True):
            # Pass through without collection
            return await execute_fn(prompt_name, arguments)
            
        # Generate prompt ID
        prompt_id = f"{connector.name}_{prompt_name}"
        prompt_type = PromptType.CONNECTOR
        
        # Check if we have an improved version
        improved_prompt = None
        if self.config.get("prompt_improvement_enabled", True):
            active_version = self.prompt_manager.get_active_prompt(prompt_id)
            if active_version and active_version.is_active:
                # Temporarily override the prompt
                improved_prompt = active_version.content
                
        # Track execution
        start_time = datetime.now()
        error_occurred = False
        error_details = None
        
        try:
            # Execute the prompt
            if improved_prompt:
                # TODO: Implement prompt override mechanism
                # This would require modifying the connector's prompt execution
                result = await execute_fn(prompt_name, arguments)
            else:
                result = await execute_fn(prompt_name, arguments)
                
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Collect success feedback if execution was significant
            if self.config.get("collect_success", True) and execution_time > self.config.get("min_execution_time", 0.1):
                await self.feedback_collector.collect_success(
                    prompt_id=prompt_id,
                    prompt_type=prompt_type,
                    execution_time=execution_time,
                    context={
                        "connector_name": connector.name,
                        "prompt_name": prompt_name,
                        "input": arguments,
                        "output": {"content": result.content, "metadata": result.metadata},
                        "session_id": self.session_id
                    }
                )
                
            return result
            
        except Exception as e:
            error_occurred = True
            error_details = {
                "error_type": type(e).__name__,
                "error_message": str(e),
                "traceback": str(e.__traceback__) if hasattr(e, '__traceback__') else None
            }
            
            # Collect error feedback
            if self.config.get("collect_errors", True):
                await self.feedback_collector.collect_error(
                    prompt_id=prompt_id,
                    prompt_type=prompt_type,
                    error_details=error_details,
                    context={
                        "connector_name": connector.name,
                        "prompt_name": prompt_name,
                        "input": arguments,
                        "session_id": self.session_id
                    }
                )
                
            # Re-raise the exception
            raise
            
    async def intercept_tool_execution(
        self,
        connector: BaseConnector,
        tool_name: str,
        arguments: Dict[str, Any],
        execute_fn
    ) -> ToolResponse:
        """Intercept tool execution for training data collection"""
        if not self.enabled or not self.config.get("auto_collect", True):
            return await execute_fn(tool_name, arguments)
            
        # For tools, we primarily collect error data
        # Success data for tools is less useful for prompt training
        
        try:
            result = await execute_fn(tool_name, arguments)
            return result
            
        except Exception as e:
            # Collect error data for analysis
            if self.config.get("collect_errors", True):
                error_details = {
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "tool_name": tool_name,
                    "connector": connector.name
                }
                
                # Store as automated metric
                await self.feedback_collector.collect_automated_metric(
                    prompt_id=f"{connector.name}_tools",
                    prompt_type=PromptType.CONNECTOR,
                    metric_name="tool_error_rate",
                    metric_value=0.0,  # Error = 0 success
                    context={
                        "error_details": error_details,
                        "tool_name": tool_name,
                        "arguments": arguments,
                        "session_id": self.session_id
                    }
                )
                
            raise
            
    async def collect_user_feedback(
        self,
        prompt_id: str,
        rating: float,
        message: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """Manually collect user feedback"""
        prompt_type = PromptType.USER if not prompt_id.startswith("system_") else PromptType.SYSTEM
        
        await self.feedback_collector.collect_user_feedback(
            prompt_id=prompt_id,
            prompt_type=prompt_type,
            rating=rating,
            message=message,
            context={
                **(context or {}),
                "session_id": self.session_id
            }
        )
        
    async def suggest_improvement(
        self,
        prompt_id: str,
        suggestion: str,
        context: Optional[Dict[str, Any]] = None
    ):
        """Collect improvement suggestion"""
        prompt_type = PromptType.USER if not prompt_id.startswith("system_") else PromptType.SYSTEM
        
        await self.feedback_collector.collect_improvement_suggestion(
            prompt_id=prompt_id,
            prompt_type=prompt_type,
            suggestion=suggestion,
            context={
                **(context or {}),
                "session_id": self.session_id
            }
        )
        
    def get_active_prompts(self) -> Dict[str, str]:
        """Get all active improved prompts"""
        prompts = {}
        
        for prompt_id, version in self.prompt_manager._active_prompts.items():
            if version.is_active and not version.is_experimental:
                prompts[prompt_id] = version.content
                
        return prompts
        
    async def shutdown(self):
        """Shutdown the training middleware"""
        if self.enabled:
            await self.feedback_collector.stop()
            await self.auto_trainer.stop()


class PromptTrainingConnector(BaseConnector):
    """Connector that provides prompt training tools to users"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.middleware = PromptTrainingMiddleware(
            enabled=config.get("enabled", True),
            config_path=config.get("config_path")
        )
        
    def get_tools(self):
        """Provide user-facing training tools"""
        from core.models import ToolDefinition
        
        return [
            ToolDefinition(
                name="rate_response",
                description="Rate the quality of the last response",
                input_schema={
                    "type": "object",
                    "properties": {
                        "rating": {
                            "type": "number",
                            "description": "Rating from 0.0 (poor) to 1.0 (excellent)",
                            "minimum": 0.0,
                            "maximum": 1.0
                        },
                        "prompt_id": {
                            "type": "string",
                            "description": "ID of the prompt being rated"
                        },
                        "message": {
                            "type": "string",
                            "description": "Optional feedback message"
                        }
                    },
                    "required": ["rating", "prompt_id"]
                }
            ),
            ToolDefinition(
                name="suggest_improvement",
                description="Suggest an improvement for a prompt",
                input_schema={
                    "type": "object",
                    "properties": {
                        "prompt_id": {
                            "type": "string",
                            "description": "ID of the prompt to improve"
                        },
                        "suggestion": {
                            "type": "string",
                            "description": "Your improvement suggestion"
                        }
                    },
                    "required": ["prompt_id", "suggestion"]
                }
            ),
            ToolDefinition(
                name="report_issue",
                description="Report an issue with a response",
                input_schema={
                    "type": "object",
                    "properties": {
                        "prompt_id": {
                            "type": "string",
                            "description": "ID of the prompt with issues"
                        },
                        "issue_type": {
                            "type": "string",
                            "enum": ["incorrect", "unclear", "incomplete", "inappropriate", "other"],
                            "description": "Type of issue"
                        },
                        "description": {
                            "type": "string",
                            "description": "Description of the issue"
                        }
                    },
                    "required": ["prompt_id", "issue_type", "description"]
                }
            ),
            ToolDefinition(
                name="get_training_status",
                description="Get status of automatic prompt training",
                input_schema={
                    "type": "object",
                    "properties": {}
                }
            ),
            ToolDefinition(
                name="trigger_training",
                description="Manually trigger training for a prompt",
                input_schema={
                    "type": "object",
                    "properties": {
                        "prompt_id": {
                            "type": "string",
                            "description": "ID of the prompt to train"
                        },
                        "approach": {
                            "type": "string",
                            "enum": ["few_shot", "reinforcement", "meta_prompt", "adversarial"],
                            "description": "Training approach to use (optional)"
                        }
                    },
                    "required": ["prompt_id"]
                }
            ),
            ToolDefinition(
                name="get_training_history",
                description="Get training history for a prompt",
                input_schema={
                    "type": "object",
                    "properties": {
                        "prompt_id": {
                            "type": "string",
                            "description": "ID of the prompt"
                        }
                    },
                    "required": ["prompt_id"]
                }
            )
        ]
        
    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]):
        """Execute training tools"""
        from core.models import ToolResult, ToolContent
        
        try:
            if tool_name == "rate_response":
                await self.middleware.collect_user_feedback(
                    prompt_id=arguments["prompt_id"],
                    rating=arguments["rating"],
                    message=arguments.get("message")
                )
                
                return ToolResult(
                    content=[ToolContent(
                        type="text",
                        text=f"Thank you for your feedback! Rating of {arguments['rating']} has been recorded."
                    )]
                )
                
            elif tool_name == "suggest_improvement":
                await self.middleware.suggest_improvement(
                    prompt_id=arguments["prompt_id"],
                    suggestion=arguments["suggestion"]
                )
                
                return ToolResult(
                    content=[ToolContent(
                        type="text",
                        text="Thank you for your suggestion! It will be considered in future improvements."
                    )]
                )
                
            elif tool_name == "report_issue":
                # Convert issue report to feedback
                await self.middleware.collect_user_feedback(
                    prompt_id=arguments["prompt_id"],
                    rating=0.2,  # Issues indicate poor performance
                    message=f"{arguments['issue_type']}: {arguments['description']}"
                )
                
                return ToolResult(
                    content=[ToolContent(
                        type="text",
                        text="Issue reported. Thank you for helping improve the system!"
                    )]
                )
                
            elif tool_name == "get_training_status":
                status = self.middleware.auto_trainer.get_training_status()
                
                status_text = f"""Automatic Prompt Training Status:
                
Enabled: {status['enabled']}
Running: {status['running']}
Training Queue: {len(status['training_queue'])} prompts
Recent Training: {len(status['recent_training'])} prompts

Configuration:
- Check Interval: {status['config']['check_interval_seconds']}s
- Min Feedback: {status['config']['min_feedback_for_training']}
- Error Rate Threshold: {status['config']['training_triggers']['error_rate_threshold']:.1%}
- Low Rating Threshold: {status['config']['training_triggers']['low_rating_threshold']:.2f}
- Auto Deploy: {status['config']['auto_deploy']['enabled']}

{f"Queued for Training: {', '.join(status['training_queue'])}" if status['training_queue'] else "No prompts in training queue"}"""

                return ToolResult(
                    content=[ToolContent(type="text", text=status_text)]
                )
                
            elif tool_name == "trigger_training":
                prompt_id = arguments["prompt_id"]
                approach = arguments.get("approach")
                
                # Trigger manual training
                await self.middleware.auto_trainer.trigger_manual_training(prompt_id, approach)
                
                return ToolResult(
                    content=[ToolContent(
                        type="text",
                        text=f"Training triggered for {prompt_id}" + 
                             (f" using {approach} approach" if approach else "")
                    )]
                )
                
            elif tool_name == "get_training_history":
                prompt_id = arguments["prompt_id"]
                history = self.middleware.auto_trainer.get_prompt_training_history(prompt_id)
                
                if not history:
                    return ToolResult(
                        content=[ToolContent(
                            type="text",
                            text=f"No training history found for {prompt_id}"
                        )]
                    )
                    
                history_text = f"Training History for {prompt_id}:\n\n"
                for i, session in enumerate(history[-5:], 1):  # Show last 5 sessions
                    history_text += f"{i}. {session['timestamp'][:19]}\n"
                    history_text += f"   Approach: {session['training_approach']}\n"
                    history_text += f"   Version: v{session['current_version']} → v{session['new_version']}\n"
                    history_text += f"   Recommendation: {session['evaluation']['recommendation']}\n"
                    history_text += f"   Auto-deployed: {session.get('auto_deployed', 'N/A')}\n\n"
                    
                return ToolResult(
                    content=[ToolContent(type="text", text=history_text)]
                )
                
            else:
                return ToolResult(
                    content=[ToolContent(type="text", text=f"Unknown tool: {tool_name}")],
                    is_error=True
                )
                
        except Exception as e:
            return ToolResult(
                content=[ToolContent(type="text", text=f"Error: {str(e)}")],
                is_error=True
            )
            
    def get_prompts(self):
        """Provide prompts about the training system"""
        return [
            {
                "name": "training_help",
                "description": "Learn about the prompt training system",
                "prompt": """The MCP Desktop Gateway includes an advanced prompt training system that learns from user feedback and errors to continuously improve responses.

How you can help improve the system:

1. **Rate Responses**: Use the rate_response tool to rate any response from 0.0 (poor) to 1.0 (excellent)
   
2. **Suggest Improvements**: Use suggest_improvement to propose specific improvements to prompts

3. **Report Issues**: Use report_issue to report problems like:
   - Incorrect information
   - Unclear responses  
   - Incomplete answers
   - Inappropriate content

Your feedback is automatically collected and used to:
- Train improved versions of prompts
- Identify common error patterns
- Test new prompt variations
- Deploy better performing prompts

The system uses LangChain and machine learning to analyze feedback patterns and generate improved prompts that are thoroughly tested before deployment.

Would you like to provide feedback on a recent interaction?"""
            }
        ]