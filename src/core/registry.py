"""
Connector registry for managing and discovering connectors
"""

import importlib
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from .base_connector import BaseConnector
from .models import ToolDefinition, ToolResult, UsageStats

logger = logging.getLogger(__name__)


class ConnectorRegistry:
    """Registry for managing tool connectors"""

    def __init__(self):
        self._connectors: Dict[str, BaseConnector] = {}
        self._connector_classes: Dict[str, Type[BaseConnector]] = {}
        self.logger = logging.getLogger(__name__)

    def register_connector_class(self, name: str, connector_class: Type[BaseConnector]) -> None:
        """Register a connector class"""
        if not issubclass(connector_class, BaseConnector):
            raise ValueError("Connector class must inherit from BaseConnector")

        self._connector_classes[name] = connector_class
        self.logger.info(f"Registered connector class: {name}")

    def auto_discover_connectors(self, base_path: str = "src/connectors") -> None:
        """Auto-discover connectors from the connectors directory"""
        # Get the absolute path relative to this file
        module_path = Path(__file__).parent.parent / "connectors"

        if not module_path.exists():
            self.logger.warning(f"Connectors directory not found: {module_path}")
            return

        # Find all subdirectories (potential connectors)
        for connector_dir in module_path.iterdir():
            if connector_dir.is_dir() and not connector_dir.name.startswith("_"):
                try:
                    # Try to import the connector module
                    module_name = f"src.connectors.{connector_dir.name}.connector"
                    self.logger.debug(f"Attempting to import {module_name}")

                    module = importlib.import_module(module_name)

                    # Look for a class that inherits from BaseConnector
                    for attr_name in dir(module):
                        if attr_name.startswith("_"):
                            continue

                        attr = getattr(module, attr_name)
                        if (
                            isinstance(attr, type)
                            and issubclass(attr, BaseConnector)
                            and attr is not BaseConnector
                        ):

                            # Found a connector class
                            self.register_connector_class(connector_dir.name, attr)
                            self.logger.info(
                                f"Auto-discovered connector: {connector_dir.name} ({attr.__name__})"
                            )
                            break

                except ImportError as e:
                    self.logger.debug(f"Failed to import connector {connector_dir.name}: {e}")
                except Exception as e:
                    self.logger.error(f"Error loading connector {connector_dir.name}: {e}")

    async def initialize_connector(self, name: str, config: Dict[str, Any]) -> BaseConnector:
        """Initialize a connector instance"""
        if name not in self._connector_classes:
            raise ValueError(f"Unknown connector: {name}")

        # Check if already initialized
        if name in self._connectors:
            self.logger.warning(f"Connector {name} already initialized, replacing...")
            await self._connectors[name].shutdown()

        # Create new instance
        connector_class = self._connector_classes[name]
        connector = connector_class(name=name, config=config)

        # Initialize it
        try:
            await connector.initialize()
            # Store it even if not fully authenticated - tools might still be available
            self._connectors[name] = connector
            self.logger.info(f"Initialized connector: {name}")
        except Exception as e:
            # Still register the connector so auth tools are available
            self._connectors[name] = connector
            self.logger.warning(f"Connector {name} partially initialized: {e}")
            # Mark as initialized so tools are available
            connector.initialized = True

        return connector

    def get_connector(self, name: str) -> Optional[BaseConnector]:
        """Get an initialized connector"""
        return self._connectors.get(name)

    def get_all_connectors(self) -> List[BaseConnector]:
        """Get all initialized connectors"""
        return list(self._connectors.values())

    def get_all_tools(self) -> List[ToolDefinition]:
        """Get all tools from all connectors"""
        tools = []
        for connector in self._connectors.values():
            connector_tools = connector.get_tools()
            tools.extend(connector_tools)
        return tools

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> ToolResult:
        """Execute a tool by finding the right connector"""
        # Find which connector owns this tool
        for connector in self._connectors.values():
            if connector.validate_tool_exists(tool_name):
                self.logger.debug(f"Executing tool {tool_name} via connector {connector.name}")
                result = await connector.execute_tool(tool_name, arguments)

                # Track usage if available
                if result.usage:
                    connector.track_usage(result.usage)

                return result

        # Tool not found
        raise ValueError(f"Tool not found: {tool_name}")

    def find_tool_owner(self, tool_name: str) -> Optional[str]:
        """Find which connector owns a specific tool"""
        for connector in self._connectors.values():
            if connector.validate_tool_exists(tool_name):
                return connector.name
        return None

    def log_all_usage_stats(self) -> None:
        """Log usage statistics for all connectors"""
        total_stats = None
        for connector in self._connectors.values():
            if connector.usage_stats.total_tokens > 0 or connector.usage_stats.api_calls > 0:
                connector.log_usage_stats(connector.usage_stats, cumulative=True)
                if total_stats is None:
                    total_stats = connector.usage_stats
                else:
                    total_stats = total_stats.add(connector.usage_stats)

        if total_stats and (total_stats.total_tokens > 0 or total_stats.api_calls > 0):
            self.logger.info(
                "Total usage across all connectors: "
                f"Tokens: {total_stats.total_tokens} | "
                f"API calls: {total_stats.api_calls} | "
                f"Cost: ${total_stats.estimated_cost:.4f}"
            )

    async def shutdown_all(self) -> None:
        """Shutdown all connectors"""
        self.logger.info("Shutting down all connectors...")

        # Log final usage stats before shutdown
        self.log_all_usage_stats()

        for name, connector in self._connectors.items():
            try:
                await connector.shutdown()
                self.logger.info(f"Shutdown connector: {name}")
            except Exception as e:
                self.logger.error(f"Error shutting down connector {name}: {e}")

        self._connectors.clear()

    def list_registered_classes(self) -> List[str]:
        """List all registered connector classes"""
        return list(self._connector_classes.keys())

    def list_initialized_connectors(self) -> List[str]:
        """List all initialized connectors"""
        return list(self._connectors.keys())

    def __str__(self) -> str:
        classes = len(self._connector_classes)
        initialized = len(self._connectors)
        return f"ConnectorRegistry(classes={classes}, initialized={initialized})"

    def __repr__(self) -> str:
        return (
            f"ConnectorRegistry(connector_classes={list(self._connector_classes.keys())}, "
            f"initialized={list(self._connectors.keys())})"
        )
