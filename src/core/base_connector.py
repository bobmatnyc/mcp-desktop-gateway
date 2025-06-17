"""Base connector interface for MCP Bridge with Resource support.

Modern Python 3.11+ implementation with structured concurrency,
exception groups, and comprehensive type hints.
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, Final

from .models import ToolContent, ToolDefinition, ToolResult, ToolResultType, UsageStats
from .resource_models import ResourceDefinition, ResourceResult, ResourceError

logger = logging.getLogger(__name__)


class BaseConnector(ABC):
    """Base class for all MCP Bridge connectors with resource support.
    
    Modern Python 3.11+ implementation featuring:
    - Structured concurrency with TaskGroups
    - Exception groups for better error handling  
    - Comprehensive type hints
    - Pydantic validation
    """

    # Class constants
    DEFAULT_VERSION: Final[str] = "1.0.0"
    
    def __init__(self, name: str, config: dict[str, Any] | None = None) -> None:
        """Initialize the connector with modern Python patterns.
        
        Args:
            name: Unique connector identifier
            config: Optional configuration dictionary
        """
        self.name = name
        self.config = config or {}
        self.initialized = False
        self.logger = logging.getLogger(f"connector.{name}")
        self.usage_stats = UsageStats()  # Track cumulative usage
        self.version = self.DEFAULT_VERSION

    async def initialize(self) -> None:
        """Initialize the connector asynchronously.
        
        Override this method to implement connector-specific initialization.
        Uses Python 3.11+ structured concurrency when needed.
        """
        self.initialized = True
        self.logger.info("Connector %s initialized", self.name)

    # MCP Prompt Support Methods
    def get_prompts(self) -> List["PromptDefinition"]:
        """Override this method to provide connector-specific prompts"""
        return []
    
    async def execute_prompt(self, prompt_name: str, arguments: Dict[str, Any]) -> "PromptResult":
        """Override this method to handle prompt execution"""
        from .models import PromptResult
        import datetime
        
        content = f"Prompt {prompt_name} not implemented for connector {self.name}"
        return PromptResult(
            content=content,
            metadata={"connector": self.name, "prompt": prompt_name},
            timestamp=datetime.datetime.now().isoformat()
        )
    
    def _create_prompt_definition(self, name: str, description: str, arguments: List[Dict] = None) -> "PromptDefinition":
        """Helper to create prompt definitions"""
        from .models import PromptDefinition, PromptArgument
        
        prompt_args = []
        if arguments:
            for arg in arguments:
                prompt_args.append(PromptArgument(
                    name=arg.get("name", ""),
                    description=arg.get("description", ""),
                    required=arg.get("required", False),
                    type=arg.get("type", "string")
                ))
        
        return PromptDefinition(
            name=name,
            description=description,
            arguments=prompt_args
        )


    async def shutdown(self) -> None:
        """Cleanup resources (override if needed)"""
        self.logger.info(f"Connector {self.name} shutting down")

    # ===== TOOLS (Existing Implementation) =====
    @abstractmethod
    def get_tools(self) -> List[ToolDefinition]:
        """Return list of tools this connector provides"""
        pass

    @abstractmethod
    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> ToolResult:
        """Execute a specific tool with given arguments"""
        pass

    # ===== RESOURCES (New Implementation) =====
    def get_resources(self) -> List[ResourceDefinition]:
        """Return list of resources this connector provides (override if needed)"""
        return []  # Default: no resources

    async def read_resource(self, uri: str) -> ResourceResult:
        """Read a specific resource by URI (override if needed)"""
        raise NotImplementedError(f"Resource reading not implemented for {self.name}")

    def validate_resource_exists(self, uri: str) -> bool:
        """Check if a resource exists in this connector"""
        resources = self.get_resources()
        return any(resource.uri == uri for resource in resources)

    # ===== HELPER METHODS =====
    def validate_tool_exists(self, tool_name: str) -> bool:
        """Check if a tool exists in this connector"""
        tools = self.get_tools()
        return any(tool.name == tool_name for tool in tools)

    def create_text_result(self, text: str, is_error: bool = False) -> ToolResult:
        """Helper to create a text result"""
        return ToolResult(
            content=[ToolContent(type=ToolResultType.TEXT, text=text)], is_error=is_error
        )

    def create_error_result(self, error_message: str) -> ToolResult:
        """Helper to create an error result"""
        return ToolResult(
            content=[ToolContent(type=ToolResultType.TEXT, text=f"Error: {error_message}")],
            is_error=True,
            error_message=error_message,
        )
    
    def create_auth_required_result(
        self, 
        auth_url: str,
        service_name: Optional[str] = None,
        instructions: Optional[str] = None
    ) -> ToolResult:
        """Create an authentication required result
        
        Args:
            auth_url: OAuth authorization URL
            service_name: Name of service requiring auth
            instructions: Custom instructions for user
            
        Returns:
            ToolResult indicating authentication needed
        """
        if not service_name:
            service_name = self.name.title()
            
        if not instructions:
            instructions = (
                f"To use {service_name} tools, authentication is required:\n\n"
                f"1. Click the link below to authenticate\n"
                f"2. Sign in and authorize access\n"
                f"3. Return to Claude Desktop and try your request again\n"
            )
        
        return ToolResult(
            content=[
                ToolContent(
                    type=ToolResultType.TEXT, 
                    text=f"🔐 Authentication Required for {service_name}\n\n{instructions}\n\n🔗 Authentication URL:\n{auth_url}"
                )
            ],
            is_error=False  # Not an error, just needs auth
        )

    def create_resource_error(self, uri: str, error_code: str, error_message: str, 
                            details: Optional[Dict[str, Any]] = None) -> ResourceError:
        """Helper to create a resource error"""
        return ResourceError(
            uri=uri,
            error_code=error_code, 
            error_message=error_message,
            details=details
        )

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Get a configuration value with optional default"""
        return self.config.get(key, default)

    def track_usage(self, usage: UsageStats) -> None:
        """Track usage statistics from a tool execution"""
        if usage:
            self.usage_stats = self.usage_stats.add(usage)
            self.log_usage_stats(usage, cumulative=False)

    def log_usage_stats(self, usage: UsageStats, cumulative: bool = True) -> None:
        """Log usage statistics"""
        if cumulative:
            stats = self.usage_stats
            prefix = "Cumulative"
        else:
            stats = usage
            prefix = "Request"

        if stats.total_tokens > 0 or stats.api_calls > 0:
            self.logger.info(
                f"{prefix} usage for {self.name}: "
                f"Tokens: {stats.total_tokens} "
                f"(in: {stats.input_tokens}, out: {stats.output_tokens}) | "
                f"API calls: {stats.api_calls} | "
                f"Cost: ${stats.estimated_cost:.4f}"
            )

    def reset_usage_stats(self) -> None:
        """Reset usage statistics"""
        old_stats = self.usage_stats
        self.usage_stats = UsageStats()
        if old_stats.total_tokens > 0 or old_stats.api_calls > 0:
            self.logger.info(
                f"Reset usage stats for {self.name} (was: {old_stats.total_tokens} tokens, ${old_stats.estimated_cost:.4f})"
            )

    def __str__(self) -> str:
        return f"Connector({self.name})"

    def __repr__(self) -> str:
        return f"Connector(name='{self.name}', initialized={self.initialized})"
