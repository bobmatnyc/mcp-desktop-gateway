"""
Core models for MCP Bridge
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ToolResultType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    RESOURCE = "resource"


class ToolContent(BaseModel):
    """Content returned by a tool"""

    type: ToolResultType
    text: Optional[str] = None
    data: Optional[str] = None
    mimeType: Optional[str] = None


class UsageStats(BaseModel):
    """Token usage and cost statistics"""

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: float = 0.0
    api_calls: int = 0

    def add(self, other: "UsageStats") -> "UsageStats":
        """Add another UsageStats to this one"""
        return UsageStats(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            total_tokens=self.total_tokens + other.total_tokens,
            estimated_cost=self.estimated_cost + other.estimated_cost,
            api_calls=self.api_calls + other.api_calls,
        )


class ToolResult(BaseModel):
    """Result from a tool execution"""

    content: List[ToolContent]
    is_error: bool = False
    error_message: Optional[str] = None
    usage: Optional[UsageStats] = None


class ToolDefinition(BaseModel):
    """Definition of a tool that can be called"""

    name: str = Field(..., description="Unique name for the tool")
    description: str = Field(..., description="Human-readable description")
    input_schema: Dict[str, Any] = Field(..., description="JSON schema for input parameters")


class MCPRequest(BaseModel):
    """MCP protocol request"""

    jsonrpc: str = "2.0"
    id: Optional[Any] = None
    method: str
    params: Optional[Dict[str, Any]] = None


class MCPError(BaseModel):
    """MCP protocol error"""

    code: int
    message: str
    data: Optional[Any] = None


class MCPResponse(BaseModel):
    """MCP protocol response"""

    jsonrpc: str = "2.0"
    id: Optional[Any] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[MCPError] = None


class ConnectorConfig(BaseModel):
    """Configuration for a connector"""

    name: str
    enabled: bool = True
    config: Dict[str, Any] = Field(default_factory=dict)


class ServerConfig(BaseModel):
    """Server configuration"""

    name: str = "mcp-bridge"
    version: str = "1.0.0"
    log_level: str = "INFO"


class BridgeConfig(BaseModel):
    """Complete bridge configuration"""

    server: ServerConfig = Field(default_factory=ServerConfig)
    connectors: List[ConnectorConfig] = Field(default_factory=list)


# MCP Prompt Support Models
from typing import List

class PromptArgument(BaseModel):
    """Argument definition for MCP prompts"""
    name: str = Field(..., description="Argument name")
    description: str = Field(..., description="Argument description")
    required: bool = Field(default=False, description="Whether argument is required")
    type: str = Field(default="string", description="Argument type")

class PromptDefinition(BaseModel):
    """MCP Prompt Definition"""
    name: str = Field(..., description="Prompt name")
    description: str = Field(..., description="Prompt description")
    arguments: List[PromptArgument] = Field(default_factory=list, description="Prompt arguments")

class PromptResult(BaseModel):
    """Result from prompt execution"""
    content: str = Field(..., description="Prompt result content")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")
    timestamp: Optional[str] = Field(default=None, description="Execution timestamp")
