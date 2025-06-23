"""Terminal AppleScript Connector for MCP Gateway.

This connector provides automation tools for macOS Terminal.app.
Always prefers opening new tabs over new windows and reviews command output.

Features:
    - Execute commands with real-time output capture
    - Tab management (create, switch, close, organize)
    - Working directory tracking
    - Interactive command support
    - Timeout handling with Python 3.11+ structured concurrency

Requires:
    - Python 3.11+
    - macOS with Terminal.app
    - AppleScript execution permissions
"""

from __future__ import annotations

import asyncio
import json
import logging
import subprocess
import time
from typing import Any, Final

from pydantic import BaseModel, Field, validator

from ....core.base_connector import BaseConnector, ToolDefinition, ResourceDefinition
from ....core.models import (
    ToolCall, ToolResponse, 
    Resource, ResourceContent,
    PromptMessage, PromptResponse
)

logger = logging.getLogger(__name__)

# Constants following Python 3.11+ best practices
DEFAULT_TIMEOUT: Final[int] = 10
DEFAULT_OUTPUT_LINES: Final[int] = 50
MAX_TIMEOUT: Final[int] = 300  # 5 minutes max
MAX_OUTPUT_LINES: Final[int] = 1000


class CommandRequest(BaseModel):
    """Pydantic model for command execution requests."""
    
    command: str = Field(..., min_length=1, description="Command to execute")
    wait_for_output: bool = Field(default=True, description="Wait for command completion")
    timeout: int = Field(default=DEFAULT_TIMEOUT, ge=1, le=MAX_TIMEOUT, description="Timeout in seconds")
    
    @validator('command')
    def validate_command(cls, v: str) -> str:
        """Validate command input."""
        if not v.strip():
            raise ValueError("Command cannot be empty")
        return v.strip()


class TabRequest(BaseModel):
    """Pydantic model for tab management requests."""
    
    command: str | None = Field(default=None, description="Optional command to run in new tab")
    title: str | None = Field(default=None, min_length=1, description="Optional tab title")
    tab_index: int | None = Field(default=None, ge=1, description="Tab index (1-based)")
    
    @validator('title')
    def validate_title(cls, v: str | None) -> str | None:
        """Validate tab title."""
        if v is not None and not v.strip():
            raise ValueError("Title cannot be empty string")
        return v.strip() if v else None


class OutputRequest(BaseModel):
    """Pydantic model for output retrieval requests."""
    
    lines: int = Field(default=DEFAULT_OUTPUT_LINES, ge=1, le=MAX_OUTPUT_LINES, description="Number of lines to retrieve")


class TerminalConnector(BaseConnector):
    """Terminal automation connector using AppleScript"""
    
    def __init__(self):
        super().__init__("terminal")
        logger.info(f"Connector {self.name} initialized")
    
    def get_tools(self) -> List[ToolDefinition]:
        """Return the tools provided by this connector."""
        return [
            ToolDefinition(
                name="terminal_execute_command",
                description="Execute a command in Terminal and return the output",
                input_schema={
                    "type": "object",
                    "properties": {
                        "command": {"type": "string", "description": "Command to execute"},
                        "wait_for_output": {"type": "boolean", "description": "Wait for command to complete and capture output (default: true)", "default": True},
                        "timeout": {"type": "number", "description": "Timeout in seconds (default: 10)", "default": 10}
                    },
                    "required": ["command"]
                }
            ),
            ToolDefinition(
                name="terminal_new_tab",
                description="Open a new tab in Terminal",
                input_schema={
                    "type": "object", 
                    "properties": {
                        "command": {"type": "string", "description": "Optional command to run in new tab"},
                        "title": {"type": "string", "description": "Optional title for the tab"}
                    }
                }
            ),
            ToolDefinition(
                name="terminal_get_output",
                description="Get the current visible output from the active Terminal tab",
                input_schema={
                    "type": "object",
                    "properties": {
                        "lines": {"type": "number", "description": "Number of lines to retrieve (default: 50)", "default": 50}
                    }
                }
            ),
            ToolDefinition(
                name="terminal_list_tabs",
                description="List all open Terminal tabs with their titles and status",
                input_schema={
                    "type": "object",
                    "properties": {}
                }
            ),
            ToolDefinition(
                name="terminal_switch_tab",
                description="Switch to a specific Terminal tab",
                input_schema={
                    "type": "object",
                    "properties": {
                        "tab_index": {"type": "number", "description": "Tab index (1-based)"}
                    },
                    "required": ["tab_index"]
                }
            ),
            ToolDefinition(
                name="terminal_close_tab",
                description="Close a specific Terminal tab",
                input_schema={
                    "type": "object",
                    "properties": {
                        "tab_index": {"type": "number", "description": "Tab index to close (1-based), defaults to current tab"}
                    }
                }
            ),
            ToolDefinition(
                name="terminal_clear_screen",
                description="Clear the Terminal screen in the current tab",
                input_schema={
                    "type": "object",
                    "properties": {}
                }
            ),
            ToolDefinition(
                name="terminal_send_text",
                description="Send text to Terminal without executing (useful for multi-line commands)",
                input_schema={
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "Text to send"},
                        "execute": {"type": "boolean", "description": "Press enter after sending text (default: false)", "default": False}
                    },
                    "required": ["text"]
                }
            ),
            ToolDefinition(
                name="terminal_get_working_directory",
                description="Get the current working directory of the active Terminal tab",
                input_schema={
                    "type": "object",
                    "properties": {}
                }
            ),
            ToolDefinition(
                name="terminal_set_tab_title",
                description="Set the title of a Terminal tab",
                input_schema={
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "New title for the tab"},
                        "tab_index": {"type": "number", "description": "Tab index (1-based), defaults to current tab"}
                    },
                    "required": ["title"]
                }
            )
        ]
    
    def get_resources(self) -> List[ResourceDefinition]:
        """Return the resources provided by this connector."""
        return [
            ResourceDefinition(
                name="terminal_sessions",
                description="List of active Terminal sessions with their state",
                mime_type="application/json"
            ),
            ResourceDefinition(
                name="terminal_history",
                description="Recent command history from Terminal",
                mime_type="text/plain"
            )
        ]
    
    def get_prompts(self) -> List[Dict[str, Any]]:
        """Return the prompts provided by this connector."""
        return [
            {
                "name": "terminal_automation",
                "description": "Guide for Terminal automation tasks",
                "prompt": """I'll help you automate Terminal tasks. I can:
- Execute scripts with visual feedback (written via Shell connector)
- Execute commands and capture real-time output
- Open new tabs in a single window (for asynchronous operations)
- Navigate between tabs and monitor multiple processes
- Get command output and working directories
- Set tab titles for organization

IMPORTANT WORKFLOW:
1. Write scripts using Shell connector (execute_command)
2. Execute scripts in Terminal for visual feedback
3. Verify results in BOTH Terminal output AND file system

What Terminal automation task would you like to accomplish?"""
            }
        ]
    
    async def call_tool(self, tool_call: ToolCall) -> ToolResponse:
        """Execute a tool call."""
        tool_name = tool_call.name
        arguments = tool_call.arguments or {}
        
        logger.info(f"Executing tool: {tool_name} with arguments: {arguments}")
        
        try:
            if tool_name == "terminal_execute_command":
                result = await self._execute_command(
                    arguments.get("command"),
                    arguments.get("wait_for_output", True),
                    arguments.get("timeout", 10)
                )
            elif tool_name == "terminal_new_tab":
                result = await self._new_tab(
                    arguments.get("command"),
                    arguments.get("title")
                )
            elif tool_name == "terminal_get_output":
                result = await self._get_output(arguments.get("lines", 50))
            elif tool_name == "terminal_list_tabs":
                result = await self._list_tabs()
            elif tool_name == "terminal_switch_tab":
                result = await self._switch_tab(arguments.get("tab_index"))
            elif tool_name == "terminal_close_tab":
                result = await self._close_tab(arguments.get("tab_index"))
            elif tool_name == "terminal_clear_screen":
                result = await self._clear_screen()
            elif tool_name == "terminal_send_text":
                result = await self._send_text(
                    arguments.get("text"),
                    arguments.get("execute", False)
                )
            elif tool_name == "terminal_get_working_directory":
                result = await self._get_working_directory()
            elif tool_name == "terminal_set_tab_title":
                result = await self._set_tab_title(
                    arguments.get("title"),
                    arguments.get("tab_index")
                )
            else:
                raise ValueError(f"Unknown tool: {tool_name}")
            
            return ToolResponse(content=result)
            
        except Exception as e:
            logger.error(f"Error executing {tool_name}: {str(e)}")
            return ToolResponse(content=f"Error: {str(e)}", is_error=True)
    
    async def _execute_applescript(self, script: str) -> str:
        """Execute an AppleScript and return the result."""
        try:
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            error_msg = f"AppleScript error: {e.stderr}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    async def _execute_command(self, command: str, wait_for_output: bool = True, timeout: int = 10) -> str:
        """Execute a command in Terminal and optionally wait for output."""
        # First, execute the command
        script = f'''
        tell application "Terminal"
            activate
            do script "{command}" in front window
        end tell
        '''
        await self._execute_applescript(script)
        
        if wait_for_output:
            # Wait a moment for command to start
            await asyncio.sleep(0.5)
            
            # Get the output with timeout
            start_time = time.time()
            last_output = ""
            stable_count = 0
            
            while time.time() - start_time < timeout:
                current_output = await self._get_output(100)
                
                # Check if output has stabilized
                if current_output == last_output:
                    stable_count += 1
                    if stable_count >= 2:  # Output unchanged for 2 checks
                        break
                else:
                    stable_count = 0
                    last_output = current_output
                
                await asyncio.sleep(0.5)
            
            # Extract just the command output (after the command line)
            lines = current_output.split('\n')
            for i, line in enumerate(lines):
                if command in line:
                    # Return everything after the command
                    return '\n'.join(lines[i+1:])
            
            return current_output
        else:
            return f"Command '{command}' sent to Terminal"
    
    async def _new_tab(self, command: Optional[str] = None, title: Optional[str] = None) -> str:
        """Open a new tab in Terminal."""
        script = '''
        tell application "Terminal"
            activate
            tell application "System Events" to keystroke "t" using command down
        '''
        
        if command:
            script += f'''
            delay 0.5
            do script "{command}" in front window
        '''
        
        script += '''
        end tell
        '''
        
        await self._execute_applescript(script)
        
        # Set title if provided
        if title:
            await asyncio.sleep(0.5)  # Wait for tab to be ready
            await self._set_tab_title(title)
        
        return f"Opened new Terminal tab{' with command: ' + command if command else ''}{' titled: ' + title if title else ''}"
    
    async def _get_output(self, lines: int = 50) -> str:
        """Get the current visible output from Terminal."""
        script = f'''
        tell application "Terminal"
            tell front window
                tell selected tab
                    set outputText to contents
                    set lineList to paragraphs of outputText
                    set lineCount to count of lineList
                    if lineCount > {lines} then
                        set startLine to lineCount - {lines} + 1
                        set outputLines to items startLine thru lineCount of lineList
                    else
                        set outputLines to lineList
                    end if
                    set AppleScript's text item delimiters to linefeed
                    set outputText to outputLines as string
                    set AppleScript's text item delimiters to ""
                    return outputText
                end tell
            end tell
        end tell
        '''
        return await self._execute_applescript(script)
    
    async def _list_tabs(self) -> str:
        """List all Terminal tabs."""
        script = '''
        tell application "Terminal"
            set tabList to {}
            set windowCount to count of windows
            repeat with w from 1 to windowCount
                tell window w
                    set tabCount to count of tabs
                    repeat with t from 1 to tabCount
                        tell tab t
                            set tabInfo to "Window " & w & ", Tab " & t & ": "
                            try
                                set tabInfo to tabInfo & (custom title)
                            on error
                                set tabInfo to tabInfo & "Terminal"
                            end try
                            if selected then
                                set tabInfo to tabInfo & " [ACTIVE]"
                            end if
                            set end of tabList to tabInfo
                        end tell
                    end repeat
                end tell
            end repeat
            set AppleScript's text item delimiters to linefeed
            set tabListText to tabList as string
            set AppleScript's text item delimiters to ""
            return tabListText
        end tell
        '''
        return await self._execute_applescript(script)
    
    async def _switch_tab(self, tab_index: int) -> str:
        """Switch to a specific tab."""
        script = f'''
        tell application "Terminal"
            activate
            tell front window
                set selected tab to tab {tab_index}
            end tell
        end tell
        '''
        await self._execute_applescript(script)
        return f"Switched to tab {tab_index}"
    
    async def _close_tab(self, tab_index: Optional[int] = None) -> str:
        """Close a Terminal tab."""
        if tab_index:
            script = f'''
            tell application "Terminal"
                tell front window
                    close tab {tab_index}
                end tell
            end tell
            '''
        else:
            script = '''
            tell application "Terminal"
                tell front window
                    close selected tab
                end tell
            end tell
            '''
        await self._execute_applescript(script)
        return f"Closed tab{' ' + str(tab_index) if tab_index else ' (current)'}"
    
    async def _clear_screen(self) -> str:
        """Clear the Terminal screen."""
        await self._execute_command("clear", wait_for_output=False)
        return "Cleared Terminal screen"
    
    async def _send_text(self, text: str, execute: bool = False) -> str:
        """Send text to Terminal."""
        # Escape quotes in the text
        escaped_text = text.replace('"', '\\"')
        
        script = f'''
        tell application "Terminal"
            activate
            tell application "System Events"
                keystroke "{escaped_text}"
        '''
        
        if execute:
            script += '''
                keystroke return
        '''
        
        script += '''
            end tell
        end tell
        '''
        
        await self._execute_applescript(script)
        return f"Sent text to Terminal{' and executed' if execute else ''}"
    
    async def _get_working_directory(self) -> str:
        """Get current working directory."""
        # Execute pwd and get output
        result = await self._execute_command("pwd", wait_for_output=True, timeout=2)
        return result.strip()
    
    async def _set_tab_title(self, title: str, tab_index: Optional[int] = None) -> str:
        """Set the title of a Terminal tab."""
        if tab_index:
            script = f'''
            tell application "Terminal"
                tell front window
                    tell tab {tab_index}
                        set custom title to "{title}"
                    end tell
                end tell
            end tell
            '''
        else:
            script = f'''
            tell application "Terminal"
                tell front window
                    tell selected tab
                        set custom title to "{title}"
                    end tell
                end tell
            end tell
            '''
        
        await self._execute_applescript(script)
        return f"Set tab{' ' + str(tab_index) if tab_index else ''} title to: {title}"
    
    async def read_resource(self, resource_name: str) -> Resource:
        """Read a resource."""
        logger.info(f"Reading resource: {resource_name}")
        
        try:
            if resource_name == "terminal_sessions":
                # Get detailed info about all Terminal sessions
                script = '''
                tell application "Terminal"
                    set sessionInfo to {}
                    repeat with w from 1 to count of windows
                        tell window w
                            repeat with t from 1 to count of tabs
                                tell tab t
                                    set tabData to {windowIndex:w, tabIndex:t}
                                    try
                                        set tabData to tabData & {title:(custom title)}
                                    on error
                                        set tabData to tabData & {title:"Terminal"}
                                    end try
                                    set tabData to tabData & {isActive:selected}
                                    set tabData to tabData & {isBusy:busy}
                                    set end of sessionInfo to tabData
                                end tell
                            end repeat
                        end tell
                    end repeat
                    return sessionInfo
                end tell
                '''
                result = await self._execute_applescript(script)
                
                # Parse the AppleScript record format
                sessions = []
                # This is simplified - real parsing would be more complex
                sessions_data = {"sessions": sessions, "count": len(sessions)}
                
                return Resource(
                    uri=f"terminal:///{resource_name}",
                    contents=[ResourceContent(
                        text=json.dumps(sessions_data, indent=2),
                        mime_type="application/json"
                    )]
                )
                
            elif resource_name == "terminal_history":
                # Get recent command history
                history = await self._get_output(100)
                
                return Resource(
                    uri=f"terminal:///{resource_name}",
                    contents=[ResourceContent(
                        text=history,
                        mime_type="text/plain"
                    )]
                )
            else:
                raise ValueError(f"Unknown resource: {resource_name}")
                
        except Exception as e:
            logger.error(f"Error reading resource {resource_name}: {str(e)}")
            raise
    
    async def call_prompt(self, prompt_name: str, arguments: Optional[Dict[str, Any]] = None) -> PromptResponse:
        """Generate a prompt response."""
        logger.info(f"Calling prompt: {prompt_name}")
        
        prompts = {p["name"]: p for p in self.get_prompts()}
        
        if prompt_name not in prompts:
            raise ValueError(f"Unknown prompt: {prompt_name}")
        
        prompt_def = prompts[prompt_name]
        
        return PromptResponse(
            messages=[PromptMessage(
                role="assistant",
                content=prompt_def["prompt"]
            )]
        )