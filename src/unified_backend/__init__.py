"""
Unified Backend Server for MCP Bridge
Handles OAuth callbacks, Chrome extension requests, and other HTTP services
"""

from .server import UnifiedServer, create_app

__all__ = ['UnifiedServer', 'create_app']