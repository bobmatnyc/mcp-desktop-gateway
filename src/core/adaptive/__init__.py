"""Adaptive prompts system for py-mcp-bridge"""

# Import simple manager by default (no dependencies)
from .simple_manager import SimpleAdaptiveManager, SimpleAdaptiveMixin, FeedbackTool

__all__ = ['SimpleAdaptiveManager', 'SimpleAdaptiveMixin', 'FeedbackTool']

# Advanced manager with full Eva integration available but not imported by default
# from .integrated_manager import IntegratedAdaptiveManager, AdaptiveConnectorMixin
