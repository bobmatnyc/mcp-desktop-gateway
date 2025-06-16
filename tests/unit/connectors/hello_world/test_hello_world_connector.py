"""
Tests for HelloWorld connector.
"""
import pytest
import json
from unittest.mock import patch, Mock
from datetime import datetime

from connectors.hello_world.connector import HelloWorldConnector
from core.models import ToolResult, ToolContent, PromptResult
from core.resource_models import ResourceResult


@pytest.mark.connector
class TestHelloWorldConnector:
    """Test HelloWorld connector functionality."""
    
    @pytest.fixture
    def connector(self):
        """Create HelloWorld connector instance."""
        config = {
            "greeting": "Welcome to Test Gateway!",
            "enable_metrics": True
        }
        return HelloWorldConnector("hello_world", config)
    
    def test_connector_initialization(self, connector):
        """Test connector initializes correctly."""
        assert connector.name == "hello_world"
        assert connector.config["greeting"] == "Welcome to Test Gateway!"
        assert hasattr(connector, 'start_time')
        assert hasattr(connector, 'activity_log')
    
    def test_get_tools(self, connector):
        """Test getting tools from HelloWorld connector."""
        tools = connector.get_tools()
        
        assert len(tools) == 3
        tool_names = [tool.name for tool in tools]
        assert "hello_world" in tool_names
        assert "gateway_diagnostics" in tool_names
        assert "echo" in tool_names
        
        # Test hello_world tool schema
        hello_tool = next(tool for tool in tools if tool.name == "hello_world")
        assert hello_tool.description == "Greet the user with MCP Gateway information"
        assert "name" in hello_tool.input_schema["properties"]
        assert hello_tool.input_schema["properties"]["name"]["type"] == "string"
    
    @pytest.mark.asyncio
    async def test_execute_hello_world_tool_with_name(self, connector):
        """Test hello_world tool execution with name parameter."""
        result = await connector.execute_tool("hello_world", {"name": "Alice"})
        
        assert isinstance(result, ToolResult)
        assert not result.is_error
        assert len(result.content) == 1
        assert "Hello Alice!" in result.content[0].text
        assert "Welcome to Test Gateway!" in result.content[0].text
        assert "MCP Desktop Gateway" in result.content[0].text
    
    @pytest.mark.asyncio
    async def test_execute_hello_world_tool_without_name(self, connector):
        """Test hello_world tool execution without name parameter."""
        result = await connector.execute_tool("hello_world", {})
        
        assert isinstance(result, ToolResult)
        assert not result.is_error
        assert len(result.content) == 1
        assert "Hello!" in result.content[0].text
        assert "Welcome to Test Gateway!" in result.content[0].text
    
    @pytest.mark.asyncio
    async def test_execute_gateway_diagnostics_tool_basic(self, connector):
        """Test gateway_diagnostics tool execution (basic)."""
        result = await connector.execute_tool("gateway_diagnostics", {"verbose": False})
        
        assert isinstance(result, ToolResult)
        assert not result.is_error
        assert len(result.content) == 1
        
        content = result.content[0].text
        assert "MCP Desktop Gateway Diagnostics" in content
        assert "Status: HEALTHY" in content
        assert "Uptime:" in content
        assert "Activity Log:" in content
    
    @pytest.mark.asyncio
    async def test_execute_gateway_diagnostics_tool_verbose(self, connector):
        """Test gateway_diagnostics tool execution (verbose)."""
        result = await connector.execute_tool("gateway_diagnostics", {"verbose": True})
        
        assert isinstance(result, ToolResult)
        assert not result.is_error
        assert len(result.content) == 1
        
        content = result.content[0].text
        assert "MCP Desktop Gateway Diagnostics" in content
        assert "Detailed System Information:" in content
        assert "Python Version:" in content
        assert "Platform:" in content
        assert "Memory Usage:" in content
    
    @pytest.mark.asyncio
    async def test_execute_echo_tool(self, connector):
        """Test echo tool execution."""
        test_message = "Hello, echo test!"
        result = await connector.execute_tool("echo", {
            "message": test_message,
            "include_metadata": True
        })
        
        assert isinstance(result, ToolResult)
        assert not result.is_error
        assert len(result.content) == 1
        
        content = result.content[0].text
        assert test_message in content
        assert "Timestamp:" in content
        assert "Connector:" in content
        assert "hello_world" in content
    
    @pytest.mark.asyncio
    async def test_execute_echo_tool_without_metadata(self, connector):
        """Test echo tool execution without metadata."""
        test_message = "Simple echo test"
        result = await connector.execute_tool("echo", {
            "message": test_message,
            "include_metadata": False
        })
        
        assert isinstance(result, ToolResult)
        assert not result.is_error
        assert len(result.content) == 1
        assert result.content[0].text == test_message
    
    @pytest.mark.asyncio
    async def test_execute_unknown_tool(self, connector):
        """Test executing unknown tool."""
        result = await connector.execute_tool("unknown_tool", {})
        
        assert isinstance(result, ToolResult)
        assert result.is_error
        assert "Tool not found" in result.content[0].text
    
    def test_get_resources(self, connector):
        """Test getting resources from HelloWorld connector."""
        resources = connector.get_resources()
        
        assert len(resources) == 3
        resource_uris = [resource.uri for resource in resources]
        assert "gateway://hello/config" in resource_uris
        assert "gateway://hello/status" in resource_uris
        assert "gateway://hello/logs" in resource_uris
        
        # Test config resource details
        config_resource = next(r for r in resources if r.uri == "gateway://hello/config")
        assert config_resource.name == "Connector Configuration"
        assert config_resource.mimeType == "application/json"
    
    @pytest.mark.asyncio
    async def test_read_config_resource(self, connector):
        """Test reading config resource."""
        result = await connector.read_resource("gateway://hello/config")
        
        assert isinstance(result, ResourceResult)
        assert result.mimeType == "application/json"
        
        config_data = json.loads(result.content)
        assert config_data["name"] == "hello_world"
        assert config_data["config"]["greeting"] == "Welcome to Test Gateway!"
    
    @pytest.mark.asyncio
    async def test_read_status_resource(self, connector):
        """Test reading status resource."""
        result = await connector.read_resource("gateway://hello/status")
        
        assert isinstance(result, ResourceResult)
        assert result.mimeType == "application/json"
        
        status_data = json.loads(result.content)
        assert status_data["connector"] == "hello_world"
        assert status_data["status"] == "active"
        assert "uptime" in status_data
        assert "tools_available" in status_data
    
    @pytest.mark.asyncio
    async def test_read_logs_resource(self, connector):
        """Test reading logs resource."""
        # Add some activity first
        await connector.execute_tool("hello_world", {"name": "Test"})
        await connector.execute_tool("echo", {"message": "Test message"})
        
        result = await connector.read_resource("gateway://hello/logs")
        
        assert isinstance(result, ResourceResult)
        assert result.mimeType == "application/json"
        
        logs_data = json.loads(result.content)
        assert "activity_log" in logs_data
        assert len(logs_data["activity_log"]) >= 2
        
        # Check log entries have expected structure
        log_entry = logs_data["activity_log"][0]
        assert "timestamp" in log_entry
        assert "action" in log_entry
        assert "details" in log_entry
    
    @pytest.mark.asyncio
    async def test_read_unknown_resource(self, connector):
        """Test reading unknown resource."""
        with pytest.raises(ValueError, match="Resource not found"):
            await connector.read_resource("gateway://hello/unknown")
    
    def test_get_prompts(self, connector):
        """Test getting prompts from HelloWorld connector."""
        prompts = connector.get_prompts()
        
        assert len(prompts) == 3
        prompt_names = [prompt.name for prompt in prompts]
        assert "hello_world_help" in prompt_names
        assert "gateway_overview" in prompt_names
        assert "connector_testing" in prompt_names
        
        # Test hello_world_help prompt details
        help_prompt = next(p for p in prompts if p.name == "hello_world_help")
        assert help_prompt.description == "Get help with using the HelloWorld connector"
        assert len(help_prompt.arguments) == 0
    
    @pytest.mark.asyncio
    async def test_execute_hello_world_help_prompt(self, connector):
        """Test executing hello_world_help prompt."""
        result = await connector.execute_prompt("hello_world_help", {})
        
        assert isinstance(result, PromptResult)
        assert "HelloWorld Connector Help" in result.content
        assert "Available Tools:" in result.content
        assert "hello_world" in result.content
        assert "gateway_diagnostics" in result.content
        assert "echo" in result.content
    
    @pytest.mark.asyncio
    async def test_execute_gateway_overview_prompt(self, connector):
        """Test executing gateway_overview prompt."""
        result = await connector.execute_prompt("gateway_overview", {})
        
        assert isinstance(result, PromptResult)
        assert "MCP Desktop Gateway Overview" in result.content
        assert "connector framework" in result.content.lower()
        assert "Tools" in result.content
        assert "Resources" in result.content
        assert "Prompts" in result.content
    
    @pytest.mark.asyncio
    async def test_execute_connector_testing_prompt(self, connector):
        """Test executing connector_testing prompt."""
        result = await connector.execute_prompt("connector_testing", {"test_type": "basic"})
        
        assert isinstance(result, PromptResult)
        assert "Connector Testing Guide" in result.content
        assert "basic" in result.content.lower()
        assert "test" in result.content.lower()
    
    @pytest.mark.asyncio
    async def test_execute_unknown_prompt(self, connector):
        """Test executing unknown prompt."""
        with pytest.raises(ValueError, match="Prompt not found"):
            await connector.execute_prompt("unknown_prompt", {})
    
    def test_activity_logging(self, connector):
        """Test activity logging functionality."""
        # Initially empty
        assert len(connector.activity_log) == 0
        
        # Log an activity
        connector._log_activity("test_action", {"key": "value"})
        
        assert len(connector.activity_log) == 1
        log_entry = connector.activity_log[0]
        assert log_entry["action"] == "test_action"
        assert log_entry["details"] == {"key": "value"}
        assert "timestamp" in log_entry
    
    def test_activity_log_limit(self, connector):
        """Test activity log size limit."""
        # Add more than the limit
        for i in range(150):  # Assuming limit is 100
            connector._log_activity(f"action_{i}", {})
        
        # Should be limited to max size
        assert len(connector.activity_log) <= 100
        
        # Most recent should be kept
        assert connector.activity_log[-1]["action"] == "action_149"
    
    def test_get_uptime(self, connector):
        """Test uptime calculation."""
        uptime = connector._get_uptime()
        assert uptime >= 0
        assert isinstance(uptime, str)
        assert ":" in uptime  # Time format
    
    @patch('psutil.virtual_memory')
    def test_get_memory_usage(self, mock_memory, connector):
        """Test memory usage retrieval."""
        # Mock psutil memory info
        mock_memory.return_value = Mock(
            total=8000000000,  # 8GB
            available=4000000000,  # 4GB
            percent=50.0
        )
        
        memory_info = connector._get_memory_usage()
        
        assert "total" in memory_info
        assert "available" in memory_info
        assert "percent" in memory_info
        assert memory_info["percent"] == 50.0
    
    @patch('psutil.virtual_memory')
    def test_get_memory_usage_psutil_unavailable(self, mock_memory, connector):
        """Test memory usage when psutil is unavailable."""
        mock_memory.side_effect = ImportError("psutil not available")
        
        memory_info = connector._get_memory_usage()
        
        assert memory_info == {"error": "Memory information not available"}
    
    def test_format_diagnostics_basic(self, connector):
        """Test basic diagnostics formatting."""
        diagnostics = connector._format_diagnostics(verbose=False)
        
        assert "MCP Desktop Gateway Diagnostics" in diagnostics
        assert "Status: HEALTHY" in diagnostics
        assert "Uptime:" in diagnostics
        assert "Activity Log:" in diagnostics
        # Should not include detailed system info
        assert "Detailed System Information:" not in diagnostics
    
    def test_format_diagnostics_verbose(self, connector):
        """Test verbose diagnostics formatting."""
        diagnostics = connector._format_diagnostics(verbose=True)
        
        assert "MCP Desktop Gateway Diagnostics" in diagnostics
        assert "Detailed System Information:" in diagnostics
        assert "Python Version:" in diagnostics
        assert "Platform:" in diagnostics
    
    @pytest.mark.asyncio
    async def test_tool_execution_updates_activity_log(self, connector):
        """Test that tool execution updates activity log."""
        initial_count = len(connector.activity_log)
        
        await connector.execute_tool("hello_world", {"name": "Test"})
        
        assert len(connector.activity_log) == initial_count + 1
        latest_log = connector.activity_log[-1]
        assert latest_log["action"] == "tool_execution"
        assert latest_log["details"]["tool"] == "hello_world"
    
    def test_connector_with_different_config(self):
        """Test connector with different configuration."""
        custom_config = {
            "greeting": "Custom welcome message!",
            "enable_metrics": False
        }
        connector = HelloWorldConnector("custom_hello", custom_config)
        
        assert connector.name == "custom_hello"
        assert connector.config["greeting"] == "Custom welcome message!"
        assert connector.config["enable_metrics"] is False
    
    def test_connector_with_minimal_config(self):
        """Test connector with minimal configuration."""
        connector = HelloWorldConnector("minimal_hello", {})
        
        assert connector.name == "minimal_hello"
        # Should handle missing config gracefully
        assert isinstance(connector.config, dict)
    
    @pytest.mark.asyncio
    async def test_error_handling_in_tools(self, connector):
        """Test error handling in tool execution."""
        # Test with invalid arguments (missing required field)
        result = await connector.execute_tool("echo", {})  # Missing 'message' field
        
        # Should handle validation error gracefully
        assert isinstance(result, ToolResult)
        # Implementation should either succeed with default or fail gracefully
    
    @pytest.mark.asyncio
    async def test_concurrent_tool_execution(self, connector):
        """Test concurrent tool execution."""
        import asyncio
        
        # Execute multiple tools concurrently
        tasks = [
            connector.execute_tool("hello_world", {"name": f"User{i}"})
            for i in range(5)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # All should succeed
        assert len(results) == 5
        for result in results:
            assert isinstance(result, ToolResult)
            assert not result.is_error
        
        # Activity log should have all executions
        assert len(connector.activity_log) >= 5