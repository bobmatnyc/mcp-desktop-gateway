"""
Common test fixtures and configuration for MCP Desktop Gateway tests.
"""
import asyncio
import json
import tempfile
from pathlib import Path
from typing import Dict, Any, List
from unittest.mock import AsyncMock, MagicMock

import pytest
import yaml

from core.models import ToolDefinition, ToolResult, ToolContent
from core.base_connector import BaseConnector


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_config_dir():
    """Create a temporary directory for config files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_config():
    """Sample configuration for testing."""
    return {
        "server": {
            "name": "mcp-gateway-test",
            "version": "1.0.0",
            "log_level": "INFO"
        },
        "connectors": [
            {
                "name": "test_connector",
                "enabled": True,
                "config": {"test_param": "test_value"}
            },
            {
                "name": "disabled_connector", 
                "enabled": False,
                "config": {}
            }
        ]
    }


@pytest.fixture
def config_file(temp_config_dir, sample_config):
    """Create a temporary config file."""
    config_path = temp_config_dir / "config.yaml"
    with open(config_path, 'w') as f:
        yaml.dump(sample_config, f)
    return config_path


@pytest.fixture
def mock_tool_definition():
    """Mock tool definition for testing."""
    return ToolDefinition(
        name="test_tool",
        description="A test tool",
        input_schema={
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "Test message"}
            },
            "required": ["message"]
        }
    )


@pytest.fixture
def mock_tool_result():
    """Mock tool result for testing."""
    return ToolResult(
        content=[ToolContent(type="text", text="Test result")],
        is_error=False
    )


class MockConnector(BaseConnector):
    """Mock connector for testing."""
    
    def __init__(self, name: str = "mock_connector", config: Dict[str, Any] = None):
        super().__init__(name, config or {})
        self.tools_called = []
        self.resources_read = []
        self.prompts_executed = []
    
    def get_tools(self) -> List[ToolDefinition]:
        return [
            ToolDefinition(
                name="mock_tool",
                description="Mock tool for testing",
                input_schema={
                    "type": "object",
                    "properties": {
                        "input": {"type": "string"}
                    },
                    "required": ["input"]
                }
            )
        ]
    
    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> ToolResult:
        self.tools_called.append((tool_name, arguments))
        return ToolResult(
            content=[ToolContent(type="text", text=f"Mock result for {tool_name}")],
            is_error=False
        )


@pytest.fixture
def mock_connector():
    """Create a mock connector instance."""
    return MockConnector()


@pytest.fixture
def mock_multiple_connectors():
    """Create multiple mock connectors for testing."""
    return [
        MockConnector("connector1", {"param1": "value1"}),
        MockConnector("connector2", {"param2": "value2"}),
        MockConnector("connector3", {"param3": "value3"})
    ]


@pytest.fixture
def mock_registry():
    """Mock ConnectorRegistry for testing."""
    from core.registry import ConnectorRegistry
    registry = ConnectorRegistry()
    # Don't auto-discover in tests
    registry._registered_classes = {}
    return registry


@pytest.fixture
def sample_tool_call():
    """Sample tool call request."""
    return {
        "tool_name": "test_tool",
        "arguments": {
            "message": "Hello, test!"
        }
    }


@pytest.fixture
def sample_mcp_request():
    """Sample MCP request for integration testing."""
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list",
        "params": {}
    }


@pytest.fixture
def sample_mcp_initialize():
    """Sample MCP initialize request."""
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "test-client",
                "version": "1.0.0"
            }
        }
    }


# Async test helpers
async def async_mock_call(*args, **kwargs):
    """Helper for async mock calls."""
    return AsyncMock(*args, **kwargs)


def create_async_mock():
    """Create an async mock."""
    return AsyncMock()