"""
Tests for BaseConnector core component.
"""
import pytest
from unittest.mock import Mock, AsyncMock
from typing import Dict, Any, List

from core.base_connector import BaseConnector
from core.models import (
    ToolDefinition, ToolResult, ToolContent,
    PromptDefinition, PromptResult
)
from core.resource_models import ResourceDefinition, ResourceResult


class ConcreteConnector(BaseConnector):
    """Concrete implementation of BaseConnector for testing."""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.tools_executed = []
        self.resources_read = []
        self.prompts_executed = []
    
    def get_tools(self) -> List[ToolDefinition]:
        return [
            ToolDefinition(
                name="test_tool",
                description="A test tool",
                input_schema={
                    "type": "object",
                    "properties": {
                        "message": {"type": "string", "description": "Test message"}
                    },
                    "required": ["message"]
                }
            ),
            ToolDefinition(
                name="error_tool",
                description="A tool that demonstrates error handling",
                input_schema={
                    "type": "object",
                    "properties": {
                        "should_fail": {"type": "boolean", "description": "Whether to fail"}
                    }
                }
            )
        ]
    
    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> ToolResult:
        self.tools_executed.append((tool_name, arguments))
        
        if tool_name == "test_tool":
            message = arguments.get("message", "No message")
            return ToolResult(
                content=[ToolContent(type="text", text=f"Processed: {message}")],
                is_error=False
            )
        elif tool_name == "error_tool":
            if arguments.get("should_fail", False):
                return ToolResult(
                    content=[ToolContent(type="text", text="Tool failed as requested")],
                    is_error=True,
                    error_message="Intentional failure"
                )
            else:
                return ToolResult(
                    content=[ToolContent(type="text", text="Tool succeeded")],
                    is_error=False
                )
        else:
            return await super().execute_tool(tool_name, arguments)
    
    def get_resources(self) -> List[ResourceDefinition]:
        return [
            ResourceDefinition(
                uri="test://config",
                name="Test Configuration",
                description="Test connector configuration",
                mimeType="application/json"
            )
        ]
    
    async def read_resource(self, uri: str) -> ResourceResult:
        self.resources_read.append(uri)
        
        if uri == "test://config":
            return ResourceResult(
                content='{"test": "value"}',
                mimeType="application/json"
            )
        else:
            return await super().read_resource(uri)
    
    def get_prompts(self) -> List[PromptDefinition]:
        return [
            self._create_prompt_definition(
                name="test_prompt",
                description="A test prompt",
                arguments=[
                    {
                        "name": "context",
                        "description": "Context for the prompt",
                        "required": False,
                        "type": "string"
                    }
                ]
            )
        ]
    
    async def execute_prompt(self, prompt_name: str, arguments: Dict[str, Any]) -> PromptResult:
        self.prompts_executed.append((prompt_name, arguments))
        
        if prompt_name == "test_prompt":
            context = arguments.get("context", "default")
            return PromptResult(
                content=f"Test prompt with context: {context}",
                metadata={"connector": self.name, "prompt": prompt_name}
            )
        else:
            return await super().execute_prompt(prompt_name, arguments)


@pytest.mark.core
class TestBaseConnector:
    """Test BaseConnector functionality."""
    
    @pytest.fixture
    def connector(self):
        """Create a concrete connector instance."""
        return ConcreteConnector("test_connector", {"param": "value"})
    
    def test_connector_initialization(self, connector):
        """Test connector initializes correctly."""
        assert connector.name == "test_connector"
        assert connector.config == {"param": "value"}
        assert hasattr(connector, 'usage_stats')
        from core.models import UsageStats
        assert isinstance(connector.usage_stats, UsageStats)
    
    def test_get_tools(self, connector):
        """Test getting tools from connector."""
        tools = connector.get_tools()
        
        assert len(tools) == 2
        tool_names = [tool.name for tool in tools]
        assert "test_tool" in tool_names
        assert "error_tool" in tool_names
        
        test_tool = next(tool for tool in tools if tool.name == "test_tool")
        assert test_tool.description == "A test tool"
        assert "message" in test_tool.input_schema["properties"]
    
    @pytest.mark.asyncio
    async def test_execute_tool_success(self, connector):
        """Test successful tool execution."""
        result = await connector.execute_tool("test_tool", {"message": "Hello"})
        
        assert isinstance(result, ToolResult)
        assert not result.is_error
        assert len(result.content) == 1
        assert result.content[0].text == "Processed: Hello"
        
        # Check execution was tracked
        assert len(connector.tools_executed) == 1
        assert connector.tools_executed[0] == ("test_tool", {"message": "Hello"})
    
    @pytest.mark.asyncio
    async def test_execute_tool_error(self, connector):
        """Test tool execution that returns an error."""
        result = await connector.execute_tool("error_tool", {"should_fail": True})
        
        assert isinstance(result, ToolResult)
        assert result.is_error
        assert result.error_message == "Intentional failure"
        assert result.content[0].text == "Tool failed as requested"
    
    @pytest.mark.asyncio
    async def test_execute_tool_not_found(self, connector):
        """Test executing non-existent tool."""
        result = await connector.execute_tool("nonexistent_tool", {})
        
        assert isinstance(result, ToolResult)
        assert result.is_error
        assert "Tool not found" in result.content[0].text
        assert result.error_message == "Tool 'nonexistent_tool' not found"
    
    @pytest.mark.asyncio
    async def test_execute_tool_exception(self):
        """Test tool execution when implementation raises exception."""
        class ExceptionConnector(BaseConnector):
            def get_tools(self):
                return [ToolDefinition(
                    name="exception_tool",
                    description="Tool that raises exception",
                    input_schema={"type": "object"}
                )]
            
            async def execute_tool(self, tool_name, arguments):
                if tool_name == "exception_tool":
                    raise ValueError("Something went wrong")
                return await super().execute_tool(tool_name, arguments)
        
        connector = ExceptionConnector("exception_test", {})
        result = await connector.execute_tool("exception_tool", {})
        
        assert isinstance(result, ToolResult)
        assert result.is_error
        assert "Something went wrong" in result.content[0].text
    
    def test_get_resources(self, connector):
        """Test getting resources from connector."""
        resources = connector.get_resources()
        
        assert len(resources) == 1
        resource = resources[0]
        assert resource.uri == "test://config"
        assert resource.name == "Test Configuration"
        assert resource.mimeType == "application/json"
    
    @pytest.mark.asyncio
    async def test_read_resource_success(self, connector):
        """Test successful resource reading."""
        result = await connector.read_resource("test://config")
        
        assert isinstance(result, ResourceResult)
        assert result.content == '{"test": "value"}'
        assert result.mimeType == "application/json"
        
        # Check reading was tracked
        assert len(connector.resources_read) == 1
        assert connector.resources_read[0] == "test://config"
    
    @pytest.mark.asyncio
    async def test_read_resource_not_found(self, connector):
        """Test reading non-existent resource."""
        with pytest.raises(ValueError, match="Resource not found"):
            await connector.read_resource("test://nonexistent")
    
    def test_get_prompts(self, connector):
        """Test getting prompts from connector."""
        prompts = connector.get_prompts()
        
        assert len(prompts) == 1
        prompt = prompts[0]
        assert prompt.name == "test_prompt"
        assert prompt.description == "A test prompt"
        assert len(prompt.arguments) == 1
        assert prompt.arguments[0].name == "context"
    
    @pytest.mark.asyncio
    async def test_execute_prompt_success(self, connector):
        """Test successful prompt execution."""
        result = await connector.execute_prompt("test_prompt", {"context": "test_context"})
        
        assert isinstance(result, PromptResult)
        assert result.content == "Test prompt with context: test_context"
        assert result.metadata["connector"] == "test_connector"
        assert result.metadata["prompt"] == "test_prompt"
        
        # Check execution was tracked
        assert len(connector.prompts_executed) == 1
        assert connector.prompts_executed[0] == ("test_prompt", {"context": "test_context"})
    
    @pytest.mark.asyncio
    async def test_execute_prompt_not_found(self, connector):
        """Test executing non-existent prompt."""
        with pytest.raises(ValueError, match="Prompt not found"):
            await connector.execute_prompt("nonexistent_prompt", {})
    
    def test_create_prompt_definition(self, connector):
        """Test prompt definition creation helper."""
        prompt_def = connector._create_prompt_definition(
            name="helper_test",
            description="Test helper",
            arguments=[
                {"name": "arg1", "description": "First argument", "required": True, "type": "string"},
                {"name": "arg2", "description": "Second argument", "required": False, "type": "number"}
            ]
        )
        
        assert isinstance(prompt_def, PromptDefinition)
        assert prompt_def.name == "helper_test"
        assert prompt_def.description == "Test helper"
        assert len(prompt_def.arguments) == 2
        
        arg1 = prompt_def.arguments[0]
        assert arg1.name == "arg1"
        assert arg1.required is True
        
        arg2 = prompt_def.arguments[1]
        assert arg2.name == "arg2"
        assert arg2.required is False
    
    def test_create_error_result(self, connector):
        """Test error result creation helper."""
        result = connector._create_error_result("Test error message")
        
        assert isinstance(result, ToolResult)
        assert result.is_error is True
        assert result.error_message == "Test error message"
        assert len(result.content) == 1
        assert result.content[0].text == "Test error message"
    
    def test_create_success_result(self, connector):
        """Test success result creation helper."""
        result = connector._create_success_result("Success message")
        
        assert isinstance(result, ToolResult)
        assert result.is_error is False
        assert result.error_message is None
        assert len(result.content) == 1
        assert result.content[0].text == "Success message"
    
    def test_create_auth_result(self, connector):
        """Test authentication result creation."""
        auth_result = connector._create_auth_result(
            success=True,
            message="Authentication successful",
            user_info={"user": "testuser", "role": "admin"}
        )
        
        assert auth_result["success"] is True
        assert auth_result["message"] == "Authentication successful"
        assert auth_result["user_info"]["user"] == "testuser"
        assert auth_result["user_info"]["role"] == "admin"
        assert "timestamp" in auth_result
    
    def test_create_auth_result_failure(self, connector):
        """Test authentication failure result."""
        auth_result = connector._create_auth_result(
            success=False,
            message="Invalid credentials"
        )
        
        assert auth_result["success"] is False
        assert auth_result["message"] == "Invalid credentials"
        assert auth_result["user_info"] is None
        assert "timestamp" in auth_result
    
    def test_update_usage_stats(self, connector):
        """Test usage statistics tracking."""
        # Initially empty
        assert len(connector.usage_stats) == 0
        
        # Update stats
        connector._update_usage_stats("test_tool")
        assert "test_tool" in connector.usage_stats
        assert connector.usage_stats["test_tool"] == 1
        
        # Increment existing
        connector._update_usage_stats("test_tool")
        assert connector.usage_stats["test_tool"] == 2
        
        # Add different tool
        connector._update_usage_stats("other_tool")
        assert connector.usage_stats["other_tool"] == 1
        assert len(connector.usage_stats) == 2
    
    def test_get_usage_stats(self, connector):
        """Test getting usage statistics."""
        connector._update_usage_stats("tool1")
        connector._update_usage_stats("tool1")
        connector._update_usage_stats("tool2")
        
        stats = connector.get_usage_stats()
        assert stats["tool1"] == 2
        assert stats["tool2"] == 1
    
    def test_get_connector_info(self, connector):
        """Test getting connector information."""
        info = connector.get_connector_info()
        
        assert info["name"] == "test_connector"
        assert info["config"] == {"param": "value"}
        assert info["tool_count"] == 2
        assert info["resource_count"] == 1
        assert info["prompt_count"] == 1
        assert "created_at" in info
    
    def test_validate_tool_arguments_valid(self, connector):
        """Test tool argument validation with valid arguments."""
        tools = connector.get_tools()
        test_tool = next(tool for tool in tools if tool.name == "test_tool")
        
        # Valid arguments
        arguments = {"message": "Hello world"}
        is_valid, error = connector._validate_tool_arguments(test_tool, arguments)
        
        assert is_valid is True
        assert error is None
    
    def test_validate_tool_arguments_missing_required(self, connector):
        """Test tool argument validation with missing required field."""
        tools = connector.get_tools()
        test_tool = next(tool for tool in tools if tool.name == "test_tool")
        
        # Missing required field
        arguments = {}
        is_valid, error = connector._validate_tool_arguments(test_tool, arguments)
        
        assert is_valid is False
        assert "message" in error
        assert "required" in error.lower()
    
    def test_validate_tool_arguments_wrong_type(self, connector):
        """Test tool argument validation with wrong type."""
        tools = connector.get_tools()
        test_tool = next(tool for tool in tools if tool.name == "test_tool")
        
        # Wrong type (number instead of string)
        arguments = {"message": 123}
        is_valid, error = connector._validate_tool_arguments(test_tool, arguments)
        
        assert is_valid is False
        assert "type" in error.lower()
    
    def test_str_representation(self, connector):
        """Test string representation of connector."""
        str_repr = str(connector)
        assert "test_connector" in str_repr
        assert "ConcreteConnector" in str_repr
    
    def test_repr_representation(self, connector):
        """Test repr representation of connector."""
        repr_str = repr(connector)
        assert "ConcreteConnector" in repr_str
        assert "test_connector" in repr_str
        assert "param" in repr_str