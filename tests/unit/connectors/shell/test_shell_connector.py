"""
Tests for Shell connector.
"""
import asyncio
import os
import json
import platform
import pytest
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path

from connectors.shell.connector import ShellConnector
from core.models import ToolResult, ToolContent, PromptResult
from core.resource_models import ResourceResult


@pytest.mark.connector
class TestShellConnector:
    """Test Shell connector functionality."""
    
    @pytest.fixture
    def connector(self):
        """Create Shell connector instance."""
        config = {
            "allowed_commands": ["ls", "echo", "cat"],
            "working_directory": "/tmp",
            "timeout": 10,
            "max_output_length": 1000
        }
        return ShellConnector("shell", config)
    
    @pytest.fixture
    def safe_connector(self, tmp_path):
        """Create Shell connector with safe configuration for testing."""
        config = {
            "working_directory": str(tmp_path),
            "timeout": 5,
            "max_output_length": 500
        }
        return ShellConnector("test_shell", config)
    
    def test_connector_initialization(self, connector):
        """Test connector initializes correctly."""
        assert connector.name == "shell"
        assert connector.working_directory == "/tmp"
        assert connector.timeout == 10
        assert connector.max_output_length == 1000
        assert connector.allowed_commands == ["ls", "echo", "cat"]
    
    def test_connector_initialization_defaults(self):
        """Test connector with default configuration."""
        connector = ShellConnector("shell", {})
        assert connector.allowed_commands == []
        assert connector.working_directory == os.getcwd()
        assert connector.timeout == 30
        assert connector.max_output_length == 10000
    
    def test_get_tools(self, connector):
        """Test getting tools from Shell connector."""
        tools = connector.get_tools()
        
        assert len(tools) == 3
        tool_names = [tool.name for tool in tools]
        assert "execute_command" in tool_names
        assert "list_directory" in tool_names
        assert "get_system_info" in tool_names
        
        # Test execute_command tool schema
        exec_tool = next(tool for tool in tools if tool.name == "execute_command")
        assert exec_tool.description == "Execute a shell command safely"
        assert "command" in exec_tool.input_schema["properties"]
        assert "working_dir" in exec_tool.input_schema["properties"]
        assert "timeout" in exec_tool.input_schema["properties"]
        assert exec_tool.input_schema["required"] == ["command"]
    
    @pytest.mark.asyncio
    async def test_execute_command_success(self, safe_connector):
        """Test successful command execution."""
        result = await safe_connector.execute_tool("execute_command", {
            "command": "echo 'Hello World'"
        })
        
        assert isinstance(result, ToolResult)
        assert not result.is_error
        assert len(result.content) == 1
        
        content = result.content[0].text
        assert "Command: echo 'Hello World'" in content
        assert "Exit Code: 0" in content
        assert "Hello World" in content
    
    @pytest.mark.asyncio
    async def test_execute_command_with_working_dir(self, safe_connector, tmp_path):
        """Test command execution with custom working directory."""
        # Create a test file in tmp_path
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        
        result = await safe_connector.execute_tool("execute_command", {
            "command": "ls test.txt",
            "working_dir": str(tmp_path)
        })
        
        assert isinstance(result, ToolResult)
        assert not result.is_error
        assert "test.txt" in result.content[0].text
        assert f"Working Directory: {tmp_path}" in result.content[0].text
    
    @pytest.mark.asyncio
    async def test_execute_command_timeout(self, safe_connector):
        """Test command execution timeout."""
        result = await safe_connector.execute_tool("execute_command", {
            "command": "sleep 10",
            "timeout": 1
        })
        
        assert isinstance(result, ToolResult)
        assert result.is_error
        assert "timed out" in result.content[0].text.lower()
    
    @pytest.mark.asyncio
    async def test_execute_command_dangerous_patterns(self, safe_connector):
        """Test blocking of dangerous command patterns."""
        dangerous_commands = [
            "rm -rf /",
            "sudo rm important_file",
            "format C:",
            "del /s important_dir",
            "echo test > /dev/null",
            "dd if=/dev/zero of=/dev/sda"
        ]
        
        for dangerous_cmd in dangerous_commands:
            result = await safe_connector.execute_tool("execute_command", {
                "command": dangerous_cmd
            })
            
            assert isinstance(result, ToolResult)
            assert result.is_error
            assert "dangerous" in result.content[0].text.lower()
    
    @pytest.mark.asyncio
    async def test_execute_command_empty_command(self, safe_connector):
        """Test execution with empty command."""
        result = await safe_connector.execute_tool("execute_command", {
            "command": ""
        })
        
        assert isinstance(result, ToolResult)
        assert result.is_error
        assert "No command provided" in result.content[0].text
    
    @pytest.mark.asyncio
    async def test_execute_command_max_timeout(self, safe_connector):
        """Test that timeout is capped at maximum value."""
        result = await safe_connector.execute_tool("execute_command", {
            "command": "echo 'test'",
            "timeout": 120  # Should be capped to 60
        })
        
        # Should succeed (not timeout) since echo is fast
        assert isinstance(result, ToolResult)
        assert not result.is_error
    
    @pytest.mark.asyncio
    async def test_execute_command_output_truncation(self, safe_connector):
        """Test output truncation for long output."""
        # Generate output longer than max_output_length (500)
        long_text = "A" * 600
        result = await safe_connector.execute_tool("execute_command", {
            "command": f"echo '{long_text}'"
        })
        
        assert isinstance(result, ToolResult)
        assert not result.is_error
        
        content = result.content[0].text
        if "truncated" in content:
            # Output was truncated
            assert len(content) < len(long_text) + 200  # Allow for metadata
    
    @pytest.mark.asyncio
    async def test_execute_command_stderr_output(self, safe_connector):
        """Test command that produces stderr output."""
        result = await safe_connector.execute_tool("execute_command", {
            "command": "ls /nonexistent_directory"
        })
        
        assert isinstance(result, ToolResult)
        # Command should complete but may have non-zero exit code
        content = result.content[0].text
        assert "Exit Code:" in content
        # Should include stderr if present
        if "STDERR:" in content:
            assert "nonexistent" in content.lower() or "not found" in content.lower()
    
    @pytest.mark.asyncio
    async def test_list_directory_current(self, safe_connector, tmp_path):
        """Test listing current directory."""
        # Create some test files
        (tmp_path / "file1.txt").write_text("content1")
        (tmp_path / "file2.txt").write_text("content2")
        (tmp_path / "subdir").mkdir()
        
        # Change working directory for connector
        safe_connector.working_directory = str(tmp_path)
        
        result = await safe_connector.execute_tool("list_directory", {})
        
        assert isinstance(result, ToolResult)
        assert not result.is_error
        
        content = result.content[0].text
        assert "file1.txt" in content
        assert "file2.txt" in content
        assert "subdir" in content
        assert "DIR" in content  # Directory marker
        assert "FILE" in content  # File marker
    
    @pytest.mark.asyncio
    async def test_list_directory_specific_path(self, safe_connector, tmp_path):
        """Test listing specific directory path."""
        # Create test structure
        test_dir = tmp_path / "testdir"
        test_dir.mkdir()
        (test_dir / "test_file.txt").write_text("test")
        
        result = await safe_connector.execute_tool("list_directory", {
            "path": str(test_dir)
        })
        
        assert isinstance(result, ToolResult)
        assert not result.is_error
        
        content = result.content[0].text
        assert "test_file.txt" in content
        assert str(test_dir) in content
    
    @pytest.mark.asyncio
    async def test_list_directory_hidden_files(self, safe_connector, tmp_path):
        """Test listing directory with hidden files."""
        # Create hidden file
        (tmp_path / ".hidden_file").write_text("hidden content")
        (tmp_path / "normal_file.txt").write_text("normal content")
        
        # List without hidden files
        result = await safe_connector.execute_tool("list_directory", {
            "path": str(tmp_path),
            "show_hidden": False
        })
        
        content = result.content[0].text
        assert "normal_file.txt" in content
        assert ".hidden_file" not in content
        
        # List with hidden files
        result = await safe_connector.execute_tool("list_directory", {
            "path": str(tmp_path),
            "show_hidden": True
        })
        
        content = result.content[0].text
        assert "normal_file.txt" in content
        assert ".hidden_file" in content
    
    @pytest.mark.asyncio
    async def test_list_directory_nonexistent(self, safe_connector):
        """Test listing non-existent directory."""
        result = await safe_connector.execute_tool("list_directory", {
            "path": "/nonexistent/directory"
        })
        
        assert isinstance(result, ToolResult)
        assert result.is_error
        assert "does not exist" in result.content[0].text
    
    @pytest.mark.asyncio
    async def test_list_directory_file_instead_of_dir(self, safe_connector, tmp_path):
        """Test listing a file instead of directory."""
        test_file = tmp_path / "test_file.txt"
        test_file.write_text("test content")
        
        result = await safe_connector.execute_tool("list_directory", {
            "path": str(test_file)
        })
        
        assert isinstance(result, ToolResult)
        assert result.is_error
        assert "not a directory" in result.content[0].text
    
    @pytest.mark.asyncio
    async def test_get_system_info(self, safe_connector):
        """Test getting system information."""
        result = await safe_connector.execute_tool("get_system_info", {})
        
        assert isinstance(result, ToolResult)
        assert not result.is_error
        
        content = result.content[0].text
        assert "System Information" in content
        assert "System:" in content
        assert "Release:" in content
        assert "Python Version:" in content
        assert "Current Directory:" in content
        assert "User:" in content
        
        # Should contain actual system info
        assert platform.system() in content
    
    @pytest.mark.asyncio
    async def test_execute_unknown_tool(self, safe_connector):
        """Test executing unknown tool."""
        result = await safe_connector.execute_tool("unknown_tool", {})
        
        assert isinstance(result, ToolResult)
        assert result.is_error
        assert "Unknown tool" in result.content[0].text
    
    def test_get_resources(self, connector):
        """Test getting resources from Shell connector."""
        resources = connector.get_resources()
        
        assert len(resources) == 2
        resource_uris = [resource.uri for resource in resources]
        assert "shell://env" in resource_uris
        assert "shell://cwd" in resource_uris
        
        # Test env resource details
        env_resource = next(r for r in resources if r.uri == "shell://env")
        assert env_resource.name == "Environment Variables"
        assert env_resource.mimeType == "application/json"
    
    @pytest.mark.asyncio
    async def test_read_env_resource(self, connector):
        """Test reading environment variables resource."""
        result = await connector.read_resource("shell://env")
        
        assert isinstance(result, ResourceResult)
        assert result.mimeType == "application/json"
        
        env_data = json.loads(result.content)
        assert isinstance(env_data, dict)
        
        # Should contain some environment variables
        assert len(env_data) > 0
        
        # Should not contain sensitive variables
        sensitive_keys = ['password', 'secret', 'key', 'token', 'auth']
        for key in env_data.keys():
            assert not any(sensitive in key.lower() for sensitive in sensitive_keys)
    
    @pytest.mark.asyncio
    async def test_read_cwd_resource(self, connector):
        """Test reading current working directory resource."""
        result = await connector.read_resource("shell://cwd")
        
        assert isinstance(result, ResourceResult)
        assert result.mimeType == "application/json"
        
        cwd_data = json.loads(result.content)
        assert "current_directory" in cwd_data
        assert "absolute_path" in cwd_data
        assert "exists" in cwd_data
        assert "is_writable" in cwd_data
        assert "parent_directory" in cwd_data
        
        assert cwd_data["exists"] is True
        assert isinstance(cwd_data["is_writable"], bool)
    
    @pytest.mark.asyncio
    async def test_read_unknown_resource(self, connector):
        """Test reading unknown resource."""
        with pytest.raises(ValueError, match="Resource not found"):
            await connector.read_resource("shell://unknown")
    
    def test_get_prompts(self, connector):
        """Test getting prompts from Shell connector."""
        prompts = connector.get_prompts()
        
        assert len(prompts) == 3
        prompt_names = [prompt.name for prompt in prompts]
        assert "shell_help" in prompt_names
        assert "system_analysis" in prompt_names
        assert "user_scripts_guide" in prompt_names
        
        # Test shell_help prompt details
        help_prompt = next(p for p in prompts if p.name == "shell_help")
        assert help_prompt.description == "Get help with shell commands and safety guidelines"
        assert len(help_prompt.arguments) == 0
    
    @pytest.mark.asyncio
    async def test_execute_shell_help_prompt(self, connector):
        """Test executing shell_help prompt."""
        result = await connector.execute_prompt("shell_help", {})
        
        assert isinstance(result, PromptResult)
        assert "Shell Connector Help" in result.content
        assert "AVAILABLE TOOLS:" in result.content
        assert "execute_command" in result.content
        assert "list_directory" in result.content
        assert "get_system_info" in result.content
        assert "SAFETY FEATURES:" in result.content
    
    @pytest.mark.asyncio
    async def test_execute_system_analysis_prompt(self, connector):
        """Test executing system_analysis prompt."""
        result = await connector.execute_prompt("system_analysis", {})
        
        assert isinstance(result, PromptResult)
        assert "Perform basic system analysis" in result.content
        assert "get_system_info" in result.content
        assert "list_directory" in result.content
        assert "ps aux" in result.content
        assert "df -h" in result.content
    
    @pytest.mark.asyncio
    async def test_execute_user_scripts_guide_prompt(self, connector):
        """Test executing user_scripts_guide prompt."""
        result = await connector.execute_prompt("user_scripts_guide", {})
        
        assert isinstance(result, PromptResult)
        assert "User Scripts Management System" in result.content
        assert "DIRECTORY STRUCTURE:" in result.content
        assert "user-scripts/" in result.content
        assert "manage.py" in result.content
        assert "EXECUTING USER SCRIPTS:" in result.content
    
    @pytest.mark.asyncio
    async def test_execute_unknown_prompt(self, connector):
        """Test executing unknown prompt."""
        with pytest.raises(ValueError, match="Prompt not found"):
            await connector.execute_prompt("unknown_prompt", {})
    
    @patch('asyncio.create_subprocess_shell')
    @pytest.mark.asyncio
    async def test_command_execution_exception_handling(self, mock_subprocess, safe_connector):
        """Test handling of subprocess creation exceptions."""
        mock_subprocess.side_effect = Exception("Subprocess creation failed")
        
        result = await safe_connector.execute_tool("execute_command", {
            "command": "echo test"
        })
        
        assert isinstance(result, ToolResult)
        assert result.is_error
        assert "Error executing command" in result.content[0].text
    
    @pytest.mark.asyncio
    async def test_directory_listing_permission_error(self, safe_connector):
        """Test handling of permission errors in directory listing."""
        # Try to list a directory that may not be accessible
        result = await safe_connector.execute_tool("list_directory", {
            "path": "/root"  # Typically not accessible to regular users
        })
        
        # Should handle gracefully - either succeed or fail with proper error
        assert isinstance(result, ToolResult)
        if result.is_error:
            assert "exist" in result.content[0].text or "permission" in result.content[0].text.lower()
    
    @pytest.mark.asyncio
    async def test_concurrent_command_execution(self, safe_connector):
        """Test concurrent command execution."""
        # Execute multiple commands concurrently
        tasks = [
            safe_connector.execute_tool("execute_command", {"command": f"echo 'test{i}'"})
            for i in range(3)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # All should succeed
        assert len(results) == 3
        for i, result in enumerate(results):
            assert isinstance(result, ToolResult)
            assert not result.is_error
            assert f"test{i}" in result.content[0].text
    
    def test_working_directory_expansion(self, tmp_path):
        """Test working directory path expansion."""
        # Test with tilde expansion
        with patch('os.path.expanduser') as mock_expanduser:
            mock_expanduser.return_value = str(tmp_path)
            connector = ShellConnector("shell", {"working_directory": "~/test"})
            # The actual expansion happens during command execution
    
    @pytest.mark.asyncio
    async def test_output_encoding_handling(self, safe_connector):
        """Test handling of different output encodings."""
        # Test with command that might produce non-ASCII output
        result = await safe_connector.execute_tool("execute_command", {
            "command": "echo 'Test with ñ special chars'"
        })
        
        assert isinstance(result, ToolResult)
        # Should handle encoding gracefully without crashing
        assert len(result.content) == 1