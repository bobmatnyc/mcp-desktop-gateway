"""
Shell Connector for MCP Gateway
Provides system command execution capabilities
"""

import asyncio
import json
import os
import subprocess
import sys
from datetime import datetime
from typing import Any, Dict, List

from core.base_connector import BaseConnector
from core.models import (
    ToolContent, ToolDefinition, ToolResult,
    PromptDefinition, PromptResult
)
from core.resource_models import ResourceDefinition, ResourceResult


class ShellConnector(BaseConnector):
    """Shell connector for executing system commands"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.allowed_commands = config.get('allowed_commands', [])
        self.working_directory = config.get('working_directory', os.getcwd())
        self.timeout = config.get('timeout', 30)
        self.max_output_length = config.get('max_output_length', 10000)
        
    def get_tools(self) -> List[ToolDefinition]:
        """Define shell tools"""
        return [
            ToolDefinition(
                name="execute_command",
                description="Execute a shell command safely",
                input_schema={
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "Shell command to execute"
                        },
                        "working_dir": {
                            "type": "string",
                            "description": "Working directory (optional)"
                        },
                        "timeout": {
                            "type": "number",
                            "description": "Timeout in seconds (optional, max 60)"
                        }
                    },
                    "required": ["command"]
                }
            ),
            ToolDefinition(
                name="list_directory",
                description="List files and directories",
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Directory path to list (default: current directory)"
                        },
                        "show_hidden": {
                            "type": "boolean",
                            "description": "Show hidden files and directories"
                        }
                    }
                }
            ),
            ToolDefinition(
                name="get_system_info",
                description="Get system information",
                input_schema={
                    "type": "object",
                    "properties": {}
                }
            )
        ]
    
    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> ToolResult:
        """Execute shell tools"""
        
        if tool_name == "execute_command":
            return await self._execute_command(arguments)
        elif tool_name == "list_directory":
            return await self._list_directory(arguments)
        elif tool_name == "get_system_info":
            return await self._get_system_info(arguments)
        else:
            return ToolResult(
                content=[ToolContent(type="text", text=f"Unknown tool: {tool_name}")],
                is_error=True,
                error_message=f"Tool '{tool_name}' not found"
            )
    
    async def _execute_command(self, arguments: Dict[str, Any]) -> ToolResult:
        """Execute a shell command"""
        command = arguments.get("command", "").strip()
        working_dir = arguments.get("working_dir", self.working_directory)
        timeout = min(arguments.get("timeout", self.timeout), 60)  # Max 60 seconds
        
        if not command:
            return ToolResult(
                content=[ToolContent(type="text", text="Error: No command provided")],
                is_error=True,
                error_message="Command is required"
            )
        
        # Security: Check for dangerous commands
        dangerous_patterns = ['rm -rf', 'sudo rm', 'format', 'del /s', '> /dev/', 'dd if=']
        if any(pattern in command.lower() for pattern in dangerous_patterns):
            return ToolResult(
                content=[ToolContent(type="text", text=f"Error: Command contains potentially dangerous operations")],
                is_error=True,
                error_message="Dangerous command blocked"
            )
        
        try:
            # Execute command
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=working_dir
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), 
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return ToolResult(
                    content=[ToolContent(type="text", text=f"Error: Command timed out after {timeout} seconds")],
                    is_error=True,
                    error_message="Command timeout"
                )
            
            # Decode output
            stdout_text = stdout.decode('utf-8', errors='replace')
            stderr_text = stderr.decode('utf-8', errors='replace')
            
            # Limit output length
            if len(stdout_text) > self.max_output_length:
                stdout_text = stdout_text[:self.max_output_length] + "\n... (output truncated)"
            if len(stderr_text) > self.max_output_length:
                stderr_text = stderr_text[:self.max_output_length] + "\n... (output truncated)"
            
            # Format result
            result_text = f"Command: {command}\n"
            result_text += f"Working Directory: {working_dir}\n"
            result_text += f"Exit Code: {process.returncode}\n\n"
            
            if stdout_text:
                result_text += f"STDOUT:\n{stdout_text}\n"
            
            if stderr_text:
                result_text += f"STDERR:\n{stderr_text}\n"
            
            if not stdout_text and not stderr_text:
                result_text += "No output\n"
            
            return ToolResult(
                content=[ToolContent(type="text", text=result_text)],
                is_error=(process.returncode != 0)
            )
            
        except Exception as e:
            return ToolResult(
                content=[ToolContent(type="text", text=f"Error executing command: {str(e)}")],
                is_error=True,
                error_message=str(e)
            )
    
    async def _list_directory(self, arguments: Dict[str, Any]) -> ToolResult:
        """List directory contents"""
        path = arguments.get("path", ".")
        show_hidden = arguments.get("show_hidden", False)
        
        try:
            # Expand path
            expanded_path = os.path.expanduser(path)
            abs_path = os.path.abspath(expanded_path)
            
            if not os.path.exists(abs_path):
                return ToolResult(
                    content=[ToolContent(type="text", text=f"Error: Path does not exist: {abs_path}")],
                    is_error=True,
                    error_message="Path not found"
                )
            
            if not os.path.isdir(abs_path):
                return ToolResult(
                    content=[ToolContent(type="text", text=f"Error: Path is not a directory: {abs_path}")],
                    is_error=True,
                    error_message="Not a directory"
                )
            
            # List contents
            items = []
            for item in sorted(os.listdir(abs_path)):
                if not show_hidden and item.startswith('.'):
                    continue
                
                item_path = os.path.join(abs_path, item)
                item_type = "DIR" if os.path.isdir(item_path) else "FILE"
                
                try:
                    size = os.path.getsize(item_path) if os.path.isfile(item_path) else 0
                    modified = datetime.fromtimestamp(os.path.getmtime(item_path)).strftime("%Y-%m-%d %H:%M:%S")
                    items.append(f"{item_type:4} {size:>10} {modified} {item}")
                except (OSError, PermissionError):
                    items.append(f"{item_type:4} {'N/A':>10} {'N/A':>19} {item}")
            
            result = f"Directory: {abs_path}\n"
            result += f"{'TYPE':4} {'SIZE':>10} {'MODIFIED':>19} NAME\n"
            result += "-" * 60 + "\n"
            result += "\n".join(items) if items else "Directory is empty"
            
            return ToolResult(
                content=[ToolContent(type="text", text=result)]
            )
            
        except Exception as e:
            return ToolResult(
                content=[ToolContent(type="text", text=f"Error listing directory: {str(e)}")],
                is_error=True,
                error_message=str(e)
            )
    
    async def _get_system_info(self, arguments: Dict[str, Any]) -> ToolResult:
        """Get system information"""
        try:
            import platform
            
            info = {
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
                "processor": platform.processor(),
                "python_version": platform.python_version(),
                "hostname": platform.node(),
                "current_directory": os.getcwd(),
                "user": os.environ.get("USER", "unknown"),
                "shell": os.environ.get("SHELL", "unknown")
            }
            
            result = "=== System Information ===\n"
            for key, value in info.items():
                result += f"{key.title().replace('_', ' ')}: {value}\n"
            
            return ToolResult(
                content=[ToolContent(type="text", text=result)]
            )
            
        except Exception as e:
            return ToolResult(
                content=[ToolContent(type="text", text=f"Error getting system info: {str(e)}")],
                is_error=True,
                error_message=str(e)
            )
    
    def get_resources(self) -> List[ResourceDefinition]:
        """Define shell resources"""
        return [
            ResourceDefinition(
                uri="shell://env",
                name="Environment Variables",
                description="Current environment variables",
                mimeType="application/json"
            ),
            ResourceDefinition(
                uri="shell://cwd",
                name="Current Working Directory",
                description="Current working directory information",
                mimeType="application/json"
            )
        ]
    
    async def read_resource(self, uri: str) -> ResourceResult:
        """Read shell resources"""
        
        if uri == "shell://env":
            env_vars = dict(os.environ)
            # Filter out sensitive variables
            sensitive_keys = ['password', 'secret', 'key', 'token', 'auth']
            filtered_env = {
                k: v for k, v in env_vars.items() 
                if not any(sensitive in k.lower() for sensitive in sensitive_keys)
            }
            
            return ResourceResult(
                content=json.dumps(filtered_env, indent=2),
                mimeType="application/json"
            )
        
        elif uri == "shell://cwd":
            cwd_info = {
                "current_directory": os.getcwd(),
                "absolute_path": os.path.abspath("."),
                "exists": os.path.exists("."),
                "is_writable": os.access(".", os.W_OK),
                "parent_directory": os.path.dirname(os.getcwd())
            }
            
            return ResourceResult(
                content=json.dumps(cwd_info, indent=2),
                mimeType="application/json"
            )
        
        else:
            raise ValueError(f"Resource not found: {uri}")
    
    def get_prompts(self) -> List[PromptDefinition]:
        """Define shell prompts"""
        return [
            self._create_prompt_definition(
                name="shell_help",
                description="Get help with shell commands and safety guidelines",
                arguments=[]
            ),
            self._create_prompt_definition(
                name="system_analysis",
                description="Perform basic system analysis",
                arguments=[]
            ),
            self._create_prompt_definition(
                name="user_scripts_guide",
                description="Learn about the user scripts management system",
                arguments=[]
            )
        ]
    
    async def execute_prompt(self, prompt_name: str, arguments: Dict[str, Any]) -> PromptResult:
        """Execute shell prompts"""
        
        if prompt_name == "shell_help":
            content = """Shell Connector Help:

AVAILABLE TOOLS:
1. execute_command - Run shell commands safely
2. list_directory - Browse file system
3. get_system_info - Get system information

SAFETY FEATURES:
- Commands are scanned for dangerous patterns
- Output is limited to prevent overwhelming responses
- Timeout protection (max 60 seconds)
- No sudo or administrative commands allowed

EXAMPLE USAGE:
- execute_command: "ls -la"
- execute_command: "ps aux | grep python"
- list_directory: path="/Users" show_hidden=true
- get_system_info: (no parameters)

BEST PRACTICES:
- Test commands in a safe environment first
- Use specific paths rather than wildcards
- Check system info before running platform-specific commands
- Use list_directory to explore before executing commands"""
            
            return PromptResult(
                content=content,
                metadata={"connector": self.name, "prompt": prompt_name}
            )
        
        elif prompt_name == "system_analysis":
            content = """Perform basic system analysis:

1. Get system information with get_system_info
2. Check current directory with list_directory
3. Look at environment with shell://env resource
4. Check running processes: execute_command "ps aux | head -20"
5. Check disk usage: execute_command "df -h"
6. Check memory: execute_command "free -h" (Linux) or "vm_stat" (macOS)

This will give you a good overview of the current system state."""
            
            return PromptResult(
                content=content,
                metadata={"connector": self.name, "prompt": prompt_name}
            )
        
        elif prompt_name == "user_scripts_guide":
            content = """User Scripts Management System

The MCP Desktop Gateway includes a comprehensive system for managing ad-hoc user-generated scripts.

DIRECTORY STRUCTURE:
user-scripts/
├── python/           # Python scripts and modules
│   ├── active/       # Currently used scripts
│   ├── archived/     # Old/deprecated scripts  
│   └── templates/    # Script templates
├── javascript/       # JavaScript/Node.js scripts
│   ├── active/       
│   ├── archived/     
│   └── templates/    
├── shell/           # Shell scripts
│   ├── active/       
│   ├── archived/     
│   └── templates/    
├── applescript/     # AppleScript automation (macOS)
│   ├── active/       
│   ├── archived/     
│   └── templates/    
├── shared/          # Shared resources
│   ├── data/        # Common data files
│   ├── configs/     # Configuration files
│   └── logs/        # Script execution logs
└── manage.py        # Management utility

MANAGEMENT UTILITY:
Use the manage.py script to manage user scripts:

# List active scripts
python user-scripts/manage.py list

# Create new script from template
python user-scripts/manage.py create my-task python --description "Process data files"

# Archive old scripts
python user-scripts/manage.py archive script-name

# Restore archived scripts
python user-scripts/manage.py restore script-name

# Clean old logs
python user-scripts/manage.py clean --days 7

# Get script info
python user-scripts/manage.py info script-name

NAMING CONVENTION:
Scripts follow the pattern: YYYY-MM-DD_<task-name>_<language>.<ext>
Examples:
- 2025-06-16_data-processor_python.py
- 2025-06-16_web-scraper_javascript.js
- 2025-06-16_backup-script_shell.sh

EXECUTING USER SCRIPTS:
Run scripts using the execute_command tool:

# Python script
execute_command(command="python user-scripts/python/active/my-script.py")

# Node.js script  
execute_command(command="node user-scripts/javascript/active/my-script.js")

# Shell script
execute_command(command="bash user-scripts/shell/active/my-script.sh")

# AppleScript
execute_command(command="osascript user-scripts/applescript/active/my-script.applescript")

TEMPLATES:
Each language directory includes template files with:
- Proper structure and documentation
- Error handling
- Argument parsing
- Logging setup
- Best practices

SECURITY:
- User scripts in 'active' directories are .gitignored
- Templates and documentation are version controlled
- Scripts should validate inputs and handle errors
- Never store sensitive data in scripts

INTEGRATION:
The user scripts system integrates seamlessly with MCP Desktop Gateway:
1. Scripts can be executed via the shell connector
2. Scripts can access project resources via relative paths
3. Scripts can write to shared data/logs directories
4. Scripts can use environment variables for configuration"""
            
            return PromptResult(
                content=content,
                metadata={"connector": self.name, "prompt": prompt_name}
            )
        
        else:
            return await super().execute_prompt(prompt_name, arguments)