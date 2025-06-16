"""
Tests for ConnectorRegistry core component.
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any, List

from core.registry import ConnectorRegistry
from core.models import ToolDefinition, ToolResult, ToolContent
from core.base_connector import BaseConnector


class TestConnector(BaseConnector):
    """Test connector for registry testing."""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.initialized = False
        self.tools_called = []
    
    def get_tools(self) -> List[ToolDefinition]:
        return [
            ToolDefinition(
                name=f"{self.name}_tool",
                description=f"Tool from {self.name}",
                input_schema={
                    "type": "object",
                    "properties": {"input": {"type": "string"}},
                    "required": ["input"]
                }
            )
        ]
    
    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> ToolResult:
        self.tools_called.append((tool_name, arguments))
        return ToolResult(
            content=[ToolContent(type="text", text=f"Result from {self.name}")],
            is_error=False
        )


class FailingTestConnector(BaseConnector):
    """Test connector that fails during initialization."""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        raise Exception("Initialization failed")
    
    def get_tools(self) -> List[ToolDefinition]:
        return []


@pytest.mark.core
class TestConnectorRegistry:
    """Test ConnectorRegistry functionality."""
    
    @pytest.fixture
    def registry(self):
        """Create a fresh registry instance."""
        return ConnectorRegistry()
    
    def test_registry_initialization(self, registry):
        """Test registry initializes correctly."""
        assert registry is not None
        assert isinstance(registry._connector_classes, dict)
        assert isinstance(registry._connectors, dict)
        assert hasattr(registry, 'logger')
    
    def test_register_connector_class(self, registry):
        """Test registering a connector class."""
        registry.register_connector_class("test", TestConnector)
        
        assert "test" in registry._connector_classes
        assert registry._connector_classes["test"] == TestConnector
    
    def test_register_duplicate_connector_class(self, registry):
        """Test registering duplicate connector class raises error."""
        registry.register_connector_class("test", TestConnector)
        
        with pytest.raises(ValueError, match="Connector class 'test' already registered"):
            registry.register_connector_class("test", TestConnector)
    
    def test_list_registered_classes(self, registry):
        """Test listing registered connector classes."""
        registry.register_connector_class("test1", TestConnector)
        registry.register_connector_class("test2", TestConnector)
        
        classes = registry.list_registered_classes()
        assert "test1" in classes
        assert "test2" in classes
        assert len(classes) == 2
    
    @pytest.mark.asyncio
    async def test_initialize_connector_success(self, registry):
        """Test successful connector initialization."""
        registry.register_connector_class("test", TestConnector)
        
        await registry.initialize_connector("test", {"param": "value"})
        
        assert "test" in registry._connectors
        connector = registry._connectors["test"]
        assert isinstance(connector, TestConnector)
        assert connector.name == "test"
        assert connector.config == {"param": "value"}
    
    @pytest.mark.asyncio
    async def test_initialize_connector_not_registered(self, registry):
        """Test initializing unregistered connector raises error."""
        with pytest.raises(ValueError, match="Connector class 'nonexistent' not registered"):
            await registry.initialize_connector("nonexistent", {})
    
    @pytest.mark.asyncio
    async def test_initialize_connector_failure(self, registry):
        """Test connector initialization failure handling."""
        registry.register_connector_class("failing", FailingTestConnector)
        
        with pytest.raises(Exception, match="Initialization failed"):
            await registry.initialize_connector("failing", {})
        
        # Ensure failed connector is not added to registry
        assert "failing" not in registry._connectors
    
    @pytest.mark.asyncio
    async def test_initialize_multiple_connectors(self, registry):
        """Test initializing multiple connectors."""
        registry.register_connector_class("test", TestConnector)
        
        await registry.initialize_connector("test1", {"param1": "value1"})
        await registry.initialize_connector("test2", {"param2": "value2"})
        
        assert len(registry._connectors) == 2
        assert "test1" in registry._connectors
        assert "test2" in registry._connectors
        assert registry._connectors["test1"].config == {"param1": "value1"}
        assert registry._connectors["test2"].config == {"param2": "value2"}
    
    def test_get_connector_exists(self, registry):
        """Test getting existing connector."""
        connector = TestConnector("test", {})
        registry._connectors["test"] = connector
        
        result = registry.get_connector("test")
        assert result == connector
    
    def test_get_connector_not_exists(self, registry):
        """Test getting non-existent connector returns None."""
        result = registry.get_connector("nonexistent")
        assert result is None
    
    def test_get_all_connectors(self, registry):
        """Test getting all connectors."""
        connector1 = TestConnector("test1", {})
        connector2 = TestConnector("test2", {})
        registry._connectors["test1"] = connector1
        registry._connectors["test2"] = connector2
        
        connectors = registry.get_all_connectors()
        assert len(connectors) == 2
        assert connector1 in connectors
        assert connector2 in connectors
    
    def test_get_all_tools(self, registry):
        """Test getting all tools from all connectors."""
        connector1 = TestConnector("test1", {})
        connector2 = TestConnector("test2", {})
        registry._connectors["test1"] = connector1
        registry._connectors["test2"] = connector2
        
        tools = registry.get_all_tools()
        assert len(tools) == 2
        
        tool_names = [tool.name for tool in tools]
        assert "test1_tool" in tool_names
        assert "test2_tool" in tool_names
    
    def test_get_all_tools_empty_registry(self, registry):
        """Test getting tools from empty registry."""
        tools = registry.get_all_tools()
        assert tools == []
    
    @pytest.mark.asyncio
    async def test_execute_tool_success(self, registry):
        """Test successful tool execution."""
        connector = TestConnector("test", {})
        registry._connectors["test"] = connector
        
        result = await registry.execute_tool("test_tool", {"input": "test"})
        
        assert isinstance(result, ToolResult)
        assert not result.is_error
        assert len(result.content) == 1
        assert result.content[0].text == "Result from test"
        
        # Check tool was called on connector
        assert len(connector.tools_called) == 1
        assert connector.tools_called[0] == ("test_tool", {"input": "test"})
    
    @pytest.mark.asyncio
    async def test_execute_tool_not_found(self, registry):
        """Test executing non-existent tool."""
        result = await registry.execute_tool("nonexistent_tool", {})
        
        assert isinstance(result, ToolResult)
        assert result.is_error
        assert "Tool not found" in result.content[0].text
    
    @pytest.mark.asyncio
    async def test_execute_tool_connector_error(self, registry):
        """Test tool execution when connector raises error."""
        # Create a connector that raises an error
        connector = TestConnector("test", {})
        
        async def failing_execute(tool_name, arguments):
            raise Exception("Tool execution failed")
        
        connector.execute_tool = failing_execute
        registry._connectors["test"] = connector
        
        result = await registry.execute_tool("test_tool", {"input": "test"})
        
        assert isinstance(result, ToolResult)
        assert result.is_error
        assert "Tool execution failed" in result.content[0].text
    
    def test_update_usage_stats(self, registry):
        """Test usage statistics tracking."""
        registry.update_usage_stats("test_connector", "test_tool")
        
        assert "test_connector" in registry._usage_stats
        assert "test_tool" in registry._usage_stats["test_connector"]
        assert registry._usage_stats["test_connector"]["test_tool"] == 1
        
        # Test incrementing
        registry.update_usage_stats("test_connector", "test_tool")
        assert registry._usage_stats["test_connector"]["test_tool"] == 2
        
        # Test different tool
        registry.update_usage_stats("test_connector", "other_tool")
        assert registry._usage_stats["test_connector"]["other_tool"] == 1
    
    def test_get_usage_stats(self, registry):
        """Test getting usage statistics."""
        registry.update_usage_stats("connector1", "tool1")
        registry.update_usage_stats("connector1", "tool2")
        registry.update_usage_stats("connector2", "tool1")
        
        stats = registry.get_usage_stats()
        
        assert "connector1" in stats
        assert "connector2" in stats
        assert stats["connector1"]["tool1"] == 1
        assert stats["connector1"]["tool2"] == 1
        assert stats["connector2"]["tool1"] == 1
    
    def test_get_usage_stats_empty(self, registry):
        """Test getting usage stats when none exist."""
        stats = registry.get_usage_stats()
        assert stats == {}
    
    def test_get_connector_count(self, registry):
        """Test getting connector count."""
        assert registry.get_connector_count() == 0
        
        connector1 = TestConnector("test1", {})
        connector2 = TestConnector("test2", {})
        registry._connectors["test1"] = connector1
        registry._connectors["test2"] = connector2
        
        assert registry.get_connector_count() == 2
    
    def test_get_tool_count(self, registry):
        """Test getting total tool count."""
        assert registry.get_tool_count() == 0
        
        connector1 = TestConnector("test1", {})
        connector2 = TestConnector("test2", {})
        registry._connectors["test1"] = connector1
        registry._connectors["test2"] = connector2
        
        # Each test connector provides 1 tool
        assert registry.get_tool_count() == 2
    
    @patch('importlib.util.spec_from_file_location')
    @patch('importlib.util.module_from_spec')
    def test_auto_discover_connectors(self, mock_module_from_spec, mock_spec_from_file, registry):
        """Test auto-discovery of connectors."""
        # This is a complex test that would require mocking the file system
        # For now, we'll test that the method exists and can be called
        with patch('pathlib.Path.glob') as mock_glob:
            mock_glob.return_value = []  # No connector files found
            registry.auto_discover_connectors()
            mock_glob.assert_called()
    
    def test_list_connector_names(self, registry):
        """Test listing connector names."""
        connector1 = TestConnector("test1", {})
        connector2 = TestConnector("test2", {})
        registry._connectors["test1"] = connector1
        registry._connectors["test2"] = connector2
        
        names = registry.list_connector_names()
        assert "test1" in names
        assert "test2" in names
        assert len(names) == 2
    
    def test_remove_connector(self, registry):
        """Test removing a connector."""
        connector = TestConnector("test", {})
        registry._connectors["test"] = connector
        
        assert "test" in registry._connectors
        
        removed = registry.remove_connector("test")
        assert removed == connector
        assert "test" not in registry._connectors
    
    def test_remove_connector_not_exists(self, registry):
        """Test removing non-existent connector returns None."""
        result = registry.remove_connector("nonexistent")
        assert result is None
    
    def test_clear_connectors(self, registry):
        """Test clearing all connectors."""
        connector1 = TestConnector("test1", {})
        connector2 = TestConnector("test2", {})
        registry._connectors["test1"] = connector1
        registry._connectors["test2"] = connector2
        
        assert len(registry._connectors) == 2
        
        registry.clear_connectors()
        assert len(registry._connectors) == 0
    
    def test_clear_usage_stats(self, registry):
        """Test clearing usage statistics."""
        registry.update_usage_stats("connector1", "tool1")
        registry.update_usage_stats("connector2", "tool2")
        
        assert len(registry._usage_stats) == 2
        
        registry.clear_usage_stats()
        assert len(registry._usage_stats) == 0