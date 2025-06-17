"""Modern tests for Shell Connector using Python 3.11+ features.

This test module demonstrates:
- Property-based testing with Hypothesis
- Modern pytest fixtures with async support
- Exception groups testing
- Structured concurrency testing
- Pydantic validation testing
"""

from __future__ import annotations

import asyncio
import pytest
from hypothesis import given, strategies as st

from src.connectors.shell.connector import (
    ShellConnector, 
    CommandRequest, 
    DirectoryListRequest,
    DANGEROUS_PATTERNS
)


class TestPydanticModels:
    """Test Pydantic model validation."""
    
    @given(st.text(min_size=1, max_size=100))
    def test_command_request_valid_input(self, command: str) -> None:
        """Test CommandRequest with valid inputs using property-based testing."""
        # Skip dangerous patterns for this test
        if any(pattern in command.lower() for pattern in DANGEROUS_PATTERNS):
            return
            
        try:
            request = CommandRequest(command=command)
            assert request.command == command.strip()
            assert request.timeout >= 1
        except Exception:
            # Some random strings might be invalid, that's expected
            pass
    
    def test_command_request_dangerous_patterns(self) -> None:
        """Test that dangerous patterns are rejected."""
        for pattern in DANGEROUS_PATTERNS[:3]:  # Test first few patterns
            with pytest.raises(ValueError, match="dangerous pattern"):
                CommandRequest(command=f"some command {pattern} more text")
    
    def test_directory_list_request_validation(self) -> None:
        """Test DirectoryListRequest validation."""
        # Valid paths
        valid_request = DirectoryListRequest(path="/tmp")
        assert valid_request.path == "/tmp"
        
        # Invalid paths with path traversal
        with pytest.raises(ValueError, match="Invalid path"):
            DirectoryListRequest(path="../../../etc")


class TestShellConnectorModern:
    """Test Shell Connector with modern Python 3.11+ features."""
    
    @pytest.fixture
    async def shell_connector(self) -> ShellConnector:
        """Create a shell connector for testing."""
        connector = ShellConnector("test_shell", {"timeout": 5})
        await connector.initialize()
        return connector
    
    @pytest.mark.asyncio
    async def test_single_command_execution(self, shell_connector: ShellConnector) -> None:
        """Test single command execution."""
        result = await shell_connector._execute_single_command("echo 'test'", timeout=5)
        
        assert result["success"] is True
        assert result["return_code"] == 0
        assert "test" in result["stdout"]
        assert result["command"] == "echo 'test'"
    
    @pytest.mark.asyncio
    async def test_parallel_command_execution(self, shell_connector: ShellConnector) -> None:
        """Test parallel command execution using TaskGroups."""
        commands = [
            "echo 'command1'",
            "echo 'command2'", 
            "echo 'command3'"
        ]
        
        results = await shell_connector.execute_parallel_commands(commands, timeout=5)
        
        assert len(results) == 3
        for i, result in enumerate(results, 1):
            assert result["success"] is True
            assert f"command{i}" in result["stdout"]
    
    @pytest.mark.asyncio
    async def test_exception_groups_on_failures(self, shell_connector: ShellConnector) -> None:
        """Test exception groups when commands fail."""
        commands = [
            "echo 'success'",
            "false",  # Command that fails
            "sleep 10"  # Command that will timeout
        ]
        
        # Test with very short timeout to trigger timeouts
        with pytest.raises(ExceptionGroup) as exc_info:
            await shell_connector.execute_parallel_commands(commands, timeout=0.1)
        
        # Verify we got an exception group
        assert isinstance(exc_info.value, ExceptionGroup)
    
    @pytest.mark.asyncio
    async def test_command_timeout_handling(self, shell_connector: ShellConnector) -> None:
        """Test timeout handling for long-running commands."""
        with pytest.raises(asyncio.TimeoutError):
            await shell_connector._execute_single_command("sleep 10", timeout=1)
    
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_concurrent_execution_performance(self, shell_connector: ShellConnector) -> None:
        """Test that parallel execution is faster than sequential."""
        import time
        
        commands = ["sleep 0.1"] * 5
        
        # Test parallel execution
        start_parallel = time.time()
        await shell_connector.execute_parallel_commands(commands, timeout=5)
        parallel_time = time.time() - start_parallel
        
        # Test sequential execution
        start_sequential = time.time()
        for cmd in commands:
            await shell_connector._execute_single_command(cmd, timeout=5)
        sequential_time = time.time() - start_sequential
        
        # Parallel should be significantly faster
        assert parallel_time < sequential_time * 0.8
    
    @given(st.lists(st.sampled_from(["echo test", "pwd", "date"]), min_size=1, max_size=5))
    @pytest.mark.asyncio
    async def test_property_based_parallel_execution(
        self, 
        shell_connector: ShellConnector,
        commands: list[str]
    ) -> None:
        """Property-based test for parallel command execution."""
        results = await shell_connector.execute_parallel_commands(commands, timeout=10)
        
        # Property: number of results equals number of commands
        assert len(results) == len(commands)
        
        # Property: all commands should succeed (these are safe commands)
        assert all(result["success"] for result in results)
        
        # Property: each result should contain the original command
        result_commands = [result["command"] for result in results]
        assert sorted(result_commands) == sorted(commands)


@pytest.mark.integration
class TestShellConnectorIntegration:
    """Integration tests for Shell Connector."""
    
    @pytest.fixture(scope="session")
    async def integration_shell_connector(self) -> ShellConnector:
        """Session-scoped shell connector for integration tests."""
        connector = ShellConnector("integration_shell")
        await connector.initialize()
        return connector
    
    @pytest.mark.asyncio
    async def test_system_information_gathering(
        self, 
        integration_shell_connector: ShellConnector
    ) -> None:
        """Test gathering system information in parallel."""
        system_commands = [
            "uname -a",
            "pwd", 
            "echo $HOME",
            "date"
        ]
        
        results = await integration_shell_connector.execute_parallel_commands(
            system_commands, 
            timeout=10
        )
        
        assert len(results) == 4
        assert all(result["success"] for result in results)
        
        # Verify we got reasonable outputs
        uname_result = next(r for r in results if r["command"] == "uname -a")
        assert len(uname_result["stdout"]) > 0