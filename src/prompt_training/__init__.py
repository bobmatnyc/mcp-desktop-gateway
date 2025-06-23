"""
Prompt Training System for MCP Desktop Gateway

This system learns from user feedback and process errors to improve prompts
using LangChain and machine learning techniques.
"""

from .feedback_collector import FeedbackCollector
from .prompt_trainer import PromptTrainer
from .prompt_manager import PromptManager
from .evaluation import PromptEvaluator
from .auto_trainer import AutomaticPromptTrainer

__all__ = [
    'FeedbackCollector',
    'PromptTrainer', 
    'PromptManager',
    'PromptEvaluator',
    'AutomaticPromptTrainer'
]