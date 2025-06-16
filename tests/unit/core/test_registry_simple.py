"""
Simplified tests for ConnectorRegistry core component.
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
        self.initialized = True
    
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
        return ToolResult(
            content=[ToolContent(type="text", text=f"Result from {self.name}")],
            is_error=False
        )
    
    def validate_tool_exists(self, tool_name: str) -> bool:
        """Check if this connector provides the given tool."""
        tool_names = [tool.name for tool in self.get_tools()]
        return tool_name in tool_names
    
    async def initialize(self):
        """Initialize the connector."""
        self.initialized = True
    
    async def shutdown(self):
        """Shutdown the connector."""
        pass


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
        """Test registering duplicate connector class (should overwrite)."""
        registry.register_connector_class("test", TestConnector)
        registry.register_connector_class("test", TestConnector)
        # Should not raise error, just overwrite
        assert "test" in registry._connector_classes
    
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
        
        connector = await registry.initialize_connector("test", {"param": "value"})
        
        assert "test" in registry._connectors
        assert isinstance(connector, TestConnector)
        assert connector.name == "test"
        assert connector.config == {"param": "value"}
    
    @pytest.mark.asyncio
    async def test_initialize_connector_not_registered(self, registry):
        """Test initializing unregistered connector raises error."""
        with pytest.raises(ValueError, match="Unknown connector"):
            await registry.initialize_connector("nonexistent", {})
    
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
    
    @pytest.mark.asyncio
    async def test_execute_tool_not_found(self, registry):
        """Test executing non-existent tool."""
        with pytest.raises(ValueError, match="Tool not found"):
            await registry.execute_tool("nonexistent_tool", {})
    
    def test_find_tool_owner(self, registry):
        """Test finding tool owner."""
        connector = TestConnector("test", {})
        registry._connectors["test"] = connector
        
        owner = registry.find_tool_owner("test_tool")
        assert owner == "test"
    
    def test_find_tool_owner_not_found(self, registry):
        """Test finding non-existent tool owner."""
        owner = registry.find_tool_owner("nonexistent_tool")
        assert owner is None
    
    def test_list_initialized_connectors(self, registry):
        """Test listing initialized connectors."""
        assert registry.list_initialized_connectors() == []
        
        connector1 = TestConnector("test1", {})
        connector2 = TestConnector("test2", {})
        registry._connectors["test1"] = connector1
        registry._connectors["test2"] = connector2
        
        initialized = registry.list_initialized_connectors()
        assert "test1" in initialized
        assert "test2" in initialized
        assert len(initialized) == 2
    
    def test_log_usage_stats(self, registry):
        """Test usage statistics logging."""
        # This method exists but doesn't return anything
        registry.log_all_usage_stats()
        # Should not raise any errors
    
    @pytest.mark.asyncio
    async def test_shutdown_all(self, registry):
        """Test shutting down all connectors."""
        connector = TestConnector("test", {})
        registry._connectors["test"] = connector
        
        await registry.shutdown_all()
        # Should not raise any errors
    
    def test_str_representation(self, registry):
        """Test string representation of registry."""
        str_repr = str(registry)
        assert "ConnectorRegistry" in str_repr
    
    def test_repr_representation(self, registry):
        """Test repr representation of registry."""
        repr_str = repr(registry)
        assert "ConnectorRegistry" in repr_str
    
    @patch('importlib.import_module')
    def test_auto_discover_connectors(self, mock_import, registry):
        """Test auto-discovery of connectors."""
        # Mock the import to avoid real file system dependencies
        mock_module = Mock()
        mock_module.HelloWorldConnector = TestConnector
        mock_import.return_value = mock_module
        
        with patch('pathlib.Path.iterdir') as mock_iterdir:
            mock_dir = Mock()
            mock_dir.is_dir.return_value = True
            mock_dir.name = "hello_world"
            mock_iterdir.return_value = [mock_dir]
            
            with patch('pathlib.Path.exists') as mock_exists:
                mock_exists.return_value = True
                registry.auto_discover_connectors()
                
                # Should have attempted to import the module
                mock_import.assert_called()