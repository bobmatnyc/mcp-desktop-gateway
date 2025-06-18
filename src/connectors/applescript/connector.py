"""
AppleScript Connector for MCP Gateway
Provides macOS automation capabilities through AppleScript
"""

import asyncio
import json
import platform
import subprocess
from datetime import datetime
from typing import Any, Dict, List

from core.base_connector import BaseConnector
from core.models import (
    ToolContent, ToolDefinition, ToolResult,
    PromptDefinition, PromptResult
)
from core.resource_models import ResourceDefinition, ResourceResult


class AppleScriptConnector(BaseConnector):
    """AppleScript connector for macOS automation"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.timeout = config.get('timeout', 30)
        self.is_macos = platform.system() == 'Darwin'
        
    def get_tools(self) -> List[ToolDefinition]:
        """Define AppleScript tools"""
        tools = [
            ToolDefinition(
                name="run_applescript",
                description="Execute AppleScript code. Note: MCP Gateway includes specialized app connectors for Safari (web automation), Contacts, Messages, Finder, and Terminal with dedicated tools. Use 'app_connectors_guide' prompt for details.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "script": {
                            "type": "string",
                            "description": "AppleScript code to execute"
                        },
                        "timeout": {
                            "type": "number",
                            "description": "Timeout in seconds (optional, max 60)"
                        }
                    },
                    "required": ["script"]
                }
            ),
            ToolDefinition(
                name="system_notification",
                description="Display a system notification",
                input_schema={
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Notification title"
                        },
                        "message": {
                            "type": "string",
                            "description": "Notification message"
                        },
                        "sound": {
                            "type": "string",
                            "description": "Sound name (optional)"
                        }
                    },
                    "required": ["title", "message"]
                }
            ),
            ToolDefinition(
                name="get_running_apps",
                description="Get list of currently running applications",
                input_schema={
                    "type": "object",
                    "properties": {}
                }
            ),
            ToolDefinition(
                name="control_app",
                description="Control applications (quit, activate, hide)",
                input_schema={
                    "type": "object",
                    "properties": {
                        "app_name": {
                            "type": "string",
                            "description": "Name of the application"
                        },
                        "action": {
                            "type": "string",
                            "enum": ["activate", "quit", "hide"],
                            "description": "Action to perform"
                        }
                    },
                    "required": ["app_name", "action"]
                }
            ),
            ToolDefinition(
                name="get_clipboard",
                description="Get clipboard contents",
                input_schema={
                    "type": "object",
                    "properties": {}
                }
            ),
            ToolDefinition(
                name="set_clipboard",
                description="Set clipboard contents",
                input_schema={
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "Text to copy to clipboard"
                        }
                    },
                    "required": ["text"]
                }
            )
        ]
        
        # Add macOS-specific note if not on macOS
        if not self.is_macos:
            for tool in tools:
                tool.description += " (macOS only)"
        
        return tools
    
    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> ToolResult:
        """Execute AppleScript tools"""
        
        if not self.is_macos:
            return ToolResult(
                content=[ToolContent(type="text", text="AppleScript is only available on macOS")],
                is_error=True,
                error_message="Platform not supported"
            )
        
        if tool_name == "run_applescript":
            return await self._run_applescript(arguments)
        elif tool_name == "system_notification":
            return await self._system_notification(arguments)
        elif tool_name == "get_running_apps":
            return await self._get_running_apps(arguments)
        elif tool_name == "control_app":
            return await self._control_app(arguments)
        elif tool_name == "get_clipboard":
            return await self._get_clipboard(arguments)
        elif tool_name == "set_clipboard":
            return await self._set_clipboard(arguments)
        else:
            return ToolResult(
                content=[ToolContent(type="text", text=f"Unknown tool: {tool_name}")],
                is_error=True,
                error_message=f"Tool '{tool_name}' not found"
            )
    
    async def _run_applescript(self, arguments: Dict[str, Any]) -> ToolResult:
        """Execute raw AppleScript"""
        script = arguments.get("script", "").strip()
        timeout = min(arguments.get("timeout", self.timeout), 60)
        
        if not script:
            return ToolResult(
                content=[ToolContent(type="text", text="Error: No script provided")],
                is_error=True,
                error_message="Script is required"
            )
        
        # Security: Check for potentially dangerous operations
        dangerous_patterns = ['do shell script', 'system events', 'delete', 'remove']
        if any(pattern in script.lower() for pattern in dangerous_patterns):
            return ToolResult(
                content=[ToolContent(type="text", text="Warning: Script contains potentially sensitive operations. Proceeding with caution.")]
            )
        
        try:
            # Execute AppleScript
            process = await asyncio.create_subprocess_exec(
                'osascript', '-e', script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
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
                    content=[ToolContent(type="text", text=f"Error: Script timed out after {timeout} seconds")],
                    is_error=True,
                    error_message="Script timeout"
                )
            
            stdout_text = stdout.decode('utf-8', errors='replace').strip()
            stderr_text = stderr.decode('utf-8', errors='replace').strip()
            
            result_text = f"AppleScript executed successfully\n"
            result_text += f"Exit Code: {process.returncode}\n\n"
            
            if stdout_text:
                result_text += f"Output:\n{stdout_text}\n"
            
            if stderr_text:
                result_text += f"Errors:\n{stderr_text}\n"
            
            if not stdout_text and not stderr_text:
                result_text += "No output\n"
            
            return ToolResult(
                content=[ToolContent(type="text", text=result_text)],
                is_error=(process.returncode != 0)
            )
            
        except Exception as e:
            return ToolResult(
                content=[ToolContent(type="text", text=f"Error executing AppleScript: {str(e)}")],
                is_error=True,
                error_message=str(e)
            )
    
    async def _system_notification(self, arguments: Dict[str, Any]) -> ToolResult:
        """Display system notification"""
        title = arguments.get("title", "")
        message = arguments.get("message", "")
        sound = arguments.get("sound", "")
        
        script = f'display notification "{message}" with title "{title}"'
        if sound:
            script += f' sound name "{sound}"'
        
        return await self._run_applescript({"script": script})
    
    async def _get_running_apps(self, arguments: Dict[str, Any]) -> ToolResult:
        """Get list of running applications"""
        script = '''
        tell application "System Events"
            set appList to {}
            repeat with proc in (every process whose background only is false)
                set end of appList to name of proc
            end repeat
        end tell
        return appList
        '''
        
        result = await self._run_applescript({"script": script})
        
        if not result.is_error:
            # Parse the output to make it more readable
            output = result.content[0].text
            if "Output:" in output:
                apps_text = output.split("Output:")[1].strip()
                if apps_text:
                    # Convert AppleScript list to readable format
                    apps = apps_text.replace("{", "").replace("}", "").split(", ")
                    formatted_apps = "\n".join([f"- {app.strip()}" for app in apps if app.strip()])
                    
                    new_text = "Running Applications:\n" + formatted_apps
                    result.content[0].text = new_text
        
        return result
    
    async def _control_app(self, arguments: Dict[str, Any]) -> ToolResult:
        """Control applications"""
        app_name = arguments.get("app_name", "")
        action = arguments.get("action", "")
        
        if not app_name or not action:
            return ToolResult(
                content=[ToolContent(type="text", text="Error: app_name and action are required")],
                is_error=True,
                error_message="Missing required parameters"
            )
        
        if action == "activate":
            script = f'tell application "{app_name}" to activate'
        elif action == "quit":
            script = f'tell application "{app_name}" to quit'
        elif action == "hide":
            script = f'tell application "System Events" to set visible of process "{app_name}" to false'
        else:
            return ToolResult(
                content=[ToolContent(type="text", text=f"Error: Unknown action '{action}'")],
                is_error=True,
                error_message="Invalid action"
            )
        
        result = await self._run_applescript({"script": script})
        
        # Customize the success message
        if not result.is_error:
            result.content[0].text = f"Successfully {action}d {app_name}"
        
        return result
    
    async def _get_clipboard(self, arguments: Dict[str, Any]) -> ToolResult:
        """Get clipboard contents"""
        script = 'return the clipboard'
        
        result = await self._run_applescript({"script": script})
        
        if not result.is_error:
            # Clean up the output format
            output = result.content[0].text
            if "Output:" in output:
                clipboard_content = output.split("Output:")[1].strip()
                result.content[0].text = f"Clipboard contents:\n{clipboard_content}"
        
        return result
    
    async def _set_clipboard(self, arguments: Dict[str, Any]) -> ToolResult:
        """Set clipboard contents"""
        text = arguments.get("text", "")
        
        if not text:
            return ToolResult(
                content=[ToolContent(type="text", text="Error: text is required")],
                is_error=True,
                error_message="Text is required"
            )
        
        # Escape quotes in the text
        escaped_text = text.replace('"', '\\"')
        script = f'set the clipboard to "{escaped_text}"'
        
        result = await self._run_applescript({"script": script})
        
        if not result.is_error:
            result.content[0].text = f"Successfully copied to clipboard: {text[:50]}{'...' if len(text) > 50 else ''}"
        
        return result
    
    def get_resources(self) -> List[ResourceDefinition]:
        """Define AppleScript resources"""
        return [
            ResourceDefinition(
                uri="applescript://apps",
                name="Running Applications",
                description="List of currently running applications",
                mimeType="application/json"
            ),
            ResourceDefinition(
                uri="applescript://system",
                name="System Information",
                description="macOS system information via AppleScript",
                mimeType="application/json"
            )
        ]
    
    async def read_resource(self, uri: str) -> ResourceResult:
        """Read AppleScript resources"""
        
        if not self.is_macos:
            return ResourceResult(
                content='{"error": "AppleScript resources only available on macOS"}',
                mimeType="application/json"
            )
        
        if uri == "applescript://apps":
            # Get running apps as JSON
            result = await self._get_running_apps({})
            if not result.is_error:
                # Extract apps from result and format as JSON
                apps_text = result.content[0].text
                if "Running Applications:" in apps_text:
                    apps_list = []
                    for line in apps_text.split("\n")[1:]:  # Skip the header
                        if line.strip().startswith("- "):
                            apps_list.append(line.strip()[2:])  # Remove "- "
                    
                    apps_data = {
                        "running_applications": apps_list,
                        "count": len(apps_list),
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    return ResourceResult(
                        content=json.dumps(apps_data, indent=2),
                        mimeType="application/json"
                    )
            
            return ResourceResult(
                content='{"error": "Failed to get running applications"}',
                mimeType="application/json"
            )
        
        elif uri == "applescript://system":
            # Get system info via AppleScript
            script = '''
            tell application "System Events"
                set sysInfo to {}
                set end of sysInfo to system attribute "sys2"
                set end of sysInfo to system attribute "ram "
            end tell
            return sysInfo
            '''
            
            result = await self._run_applescript({"script": script})
            
            system_info = {
                "platform": "macOS",
                "applescript_available": True,
                "timestamp": datetime.now().isoformat(),
                "capabilities": [
                    "notifications",
                    "app_control",
                    "clipboard_access",
                    "system_events"
                ]
            }
            
            return ResourceResult(
                content=json.dumps(system_info, indent=2),
                mimeType="application/json"
            )
        
        else:
            raise ValueError(f"Resource not found: {uri}")
    
    def get_prompts(self) -> List[PromptDefinition]:
        """Define AppleScript prompts"""
        return [
            self._create_prompt_definition(
                name="available_adapters",
                description="List all available AppleScript tool adapters for macOS app automation",
                arguments=[]
            ),
            self._create_prompt_definition(
                name="applescript_help",
                description="Get comprehensive help with AppleScript automation and available app connectors",
                arguments=[]
            ),
            self._create_prompt_definition(
                name="automate_task",
                description="Get guidance for automating a specific task",
                arguments=[
                    {
                        "name": "task",
                        "description": "Description of the task to automate",
                        "required": True,
                        "type": "string"
                    }
                ]
            ),
            self._create_prompt_definition(
                name="app_connectors_guide",
                description="Get detailed guide on using app-specific connectors (Safari, Contacts, Messages, Finder, Terminal)",
                arguments=[
                    {
                        "name": "app",
                        "description": "Specific app to get help with (safari, contacts, messages, finder, terminal, or 'all')",
                        "required": False,
                        "type": "string"
                    }
                ]
            ),
            self._create_prompt_definition(
                name="terminal_automation",
                description="Learn effective Terminal automation with AppleScript vs Shell",
                arguments=[]
            )
        ]
    
    async def execute_prompt(self, prompt_name: str, arguments: Dict[str, Any]) -> PromptResult:
        """Execute AppleScript prompts"""
        
        if prompt_name == "available_adapters":
            content = """Available AppleScript Tool Adapters in MCP Desktop Gateway

The MCP Desktop Gateway provides specialized AppleScript adapters for automating common macOS applications. Each adapter includes multiple tools and resources for comprehensive automation.

🌐 SAFARI CONNECTOR (15 tools)
• Web browser automation: open URLs, manage tabs, execute JavaScript, take screenshots
• Tools: safari_open_url, safari_get_tabs, safari_execute_javascript, safari_take_screenshot, etc.
• Resources: safari://tabs, safari://current, safari://bookmarks, safari://history

📇 CONTACTS CONNECTOR (10 tools)  
• Contact management: search, create, update, delete contacts and groups
• Tools: contacts_search, contacts_create, contacts_update, contacts_delete, etc.
• Resources: contacts://all, contacts://groups, contacts://recent

💬 MESSAGES CONNECTOR (10 tools)
• Text messaging automation: send messages, manage conversations, search history
• Tools: messages_send, messages_get_conversations, messages_search, messages_send_file, etc.
• Resources: messages://conversations, messages://unread, messages://recent

📁 FINDER CONNECTOR (10 tools)
• File system GUI operations: navigate folders, manage files, search, trash operations
• Tools: finder_open, finder_get_selection, finder_move_to_trash, finder_search, etc.
• Resources: finder://desktop, finder://selection, finder://trash

🖥️ TERMINAL CONNECTOR (10 tools)
• Terminal.app automation: execute commands, manage tabs, capture output
• Tools: terminal_execute_command, terminal_new_tab, terminal_get_output, etc.
• Resources: terminal://sessions, terminal://history

QUICK START:
1. Use 'app_connectors_guide' prompt with app name for detailed documentation
2. Example: app_connectors_guide with app="safari" for Safari-specific help
3. Or use app="all" to see documentation for all connectors

NOTE: These adapters are automatically available when the AppleScript connector is enabled."""
            
            return PromptResult(
                content=content,
                metadata={"connector": self.name, "prompt": prompt_name}
            )
        
        elif prompt_name == "applescript_help":
            content = """AppleScript Connector - Comprehensive Help Guide

🚀 AVAILABLE APP-SPECIFIC CONNECTORS:
The MCP Desktop Gateway includes 5 specialized AppleScript adapters with 55+ tools total:
• 🌐 Safari (15 tools) - Web automation, JavaScript execution, screenshots
• 📇 Contacts (10 tools) - Contact management and vCard operations  
• 💬 Messages (10 tools) - Text messaging and conversation management
• 📁 Finder (10 tools) - File system GUI operations
• 🖥️ Terminal (10 tools) - Terminal.app automation

💡 Use 'available_adapters' prompt for a complete list of all tools
💡 Use 'app_connectors_guide' prompt for detailed app-specific documentation

BASIC APPLESCRIPT TOOLS:
1. run_applescript - Execute custom AppleScript code
   • script: The AppleScript code to execute
   • Example: tell application "Safari" to activate

2. system_notification - Display macOS notifications
   • title: Notification title
   • message: Notification message
   • sound: Optional sound name
   • Example: title="Task Complete" message="Download finished"

3. get_running_apps - List all running applications
   • No parameters required
   • Returns list of active applications

4. control_app - Control application lifecycle
   • app_name: Name of the application
   • action: "activate", "quit", or "hide"
   • Example: app_name="Safari" action="activate"

5. get_clipboard - Get current clipboard contents
   • No parameters required
   • Returns text from clipboard

6. set_clipboard - Set clipboard contents
   • text: Text to copy to clipboard
   • Example: text="Hello, clipboard!"

APP-SPECIFIC CONNECTORS (55+ TOOLS):
The MCP Desktop Gateway includes 5 specialized AppleScript adapters:
• Safari (15 tools) - safari_open_url, safari_execute_javascript, safari_take_screenshot, etc.
• Contacts (10 tools) - contacts_search, contacts_create, contacts_update, etc.
• Messages (10 tools) - messages_send, messages_get_conversations, messages_search, etc.
• Finder (10 tools) - finder_open, finder_get_selection, finder_move_to_trash, etc.
• Terminal (10 tools) - terminal_execute_command, terminal_new_tab, terminal_get_output, etc.

📌 Use 'available_adapters' prompt for complete tool list
📌 Use 'app_connectors_guide' prompt for detailed documentation

RESOURCES:
- applescript://apps - List of running applications
- applescript://system - System information

SAFETY FEATURES:
- Timeout protection (30 seconds default)
- Platform detection (macOS only)
- Dangerous operation detection
- Error handling and logging

COMMON PATTERNS:
1. Activating an app:
   tell application "AppName" to activate

2. GUI automation:
   tell application "System Events"
       tell process "AppName"
           click menu item "Save" of menu "File" of menu bar 1
       end tell
   end tell

3. Getting window info:
   tell application "AppName"
       get name of every window
   end tell"""
            
            return PromptResult(
                content=content,
                metadata={"connector": self.name, "prompt": prompt_name}
            )
        
        elif prompt_name == "automate_task":
            task = arguments.get("task", "")
            
            content = f"""Automating task: {task}

APPROACH:
1. Identify the applications involved
2. Check if they're running with get_running_apps
3. Use control_app to activate/manage apps
4. Use run_applescript for custom automation
5. Test with simple operations first

COMMON AUTOMATION TASKS:
- Opening applications: control_app with "activate"
- Sending notifications: system_notification
- Managing clipboard: get_clipboard, set_clipboard
- Window management: AppleScript with System Events
- Document automation: App-specific AppleScript

EXAMPLE WORKFLOW:
1. get_running_apps to see current state
2. control_app to open required applications
3. run_applescript for specific automation
4. system_notification to confirm completion

Start simple and build complexity gradually."""
            
            return PromptResult(
                content=content,
                metadata={"connector": self.name, "prompt": prompt_name, "task": task}
            )
        
        elif prompt_name == "app_connectors_guide":
            app = arguments.get("app", "all").lower()
            
            if app == "safari" or app == "all":
                safari_guide = """
SAFARI CONNECTOR - Web Browser Automation

TOOLS:
1. safari_open_url - Open URL in Safari
   • url: URL to open
   • new_tab: Open in new tab (default: true)
   • new_window: Open in new window (default: false)

2. safari_get_current_url - Get URL of current tab
3. safari_get_page_title - Get title of current page
4. safari_get_tabs - List all open tabs
   • include_content: Include page content (default: false)

5. safari_close_tab - Close a tab
   • tab_index: Tab number to close (1-based)

6. safari_switch_tab - Switch to specific tab
   • tab_index: Tab number to switch to

7. safari_reload_page - Reload current page
8. safari_go_back/safari_go_forward - Navigate history
9. safari_search - Search using search engine
   • query: Search query
   • search_engine: google, bing, duckduckgo (default: google)

10. safari_execute_javascript - Run JavaScript in page
    • javascript: JavaScript code to execute

11. safari_get_page_source - Get HTML source
12. safari_take_screenshot - Capture page screenshot
    • output_path: Where to save screenshot

13. safari_set_zoom - Adjust page zoom
    • zoom_level: 1.0 = 100%, 1.5 = 150%, etc.

14. safari_add_bookmark - Bookmark current page
    • title: Bookmark title
    • folder: Bookmark folder

RESOURCES:
- safari://tabs - All open tabs
- safari://current - Current tab info
- safari://bookmarks - Bookmarks (planned)
- safari://history - History (planned)
"""
            
            if app == "contacts" or app == "all":
                contacts_guide = """
CONTACTS CONNECTOR - Contact Management

TOOLS:
1. contacts_search - Find contacts
   • query: Search by name, email, or phone
   • limit: Max results (default: 10)

2. contacts_get_contact - Get contact details
   • contact_name: Full name
   • contact_id: Contact ID (alternative)

3. contacts_create_contact - Create new contact
   • first_name: Required
   • last_name, email, phone, company, job_title: Optional

4. contacts_update_contact - Update existing contact
   • contact_name: Contact to update
   • Any fields to update

5. contacts_delete_contact - Delete contact
   • contact_name: Contact to delete
   • confirm: Must be true

6. contacts_get_groups - List contact groups
7. contacts_create_group - Create new group
   • group_name: Name of new group

8. contacts_add_to_group - Add contact to group
   • contact_name: Contact to add
   • group_name: Target group

9. contacts_export_vcard - Export as vCard
   • contact_name: Specific contact (or all)
   • output_path: Save location

10. contacts_get_recent - Get recent contacts
    • limit: Max results

RESOURCES:
- contacts://all - All contacts
- contacts://groups - All groups
- contacts://recent - Recent contacts
"""

            if app == "messages" or app == "all":
                messages_guide = """
MESSAGES CONNECTOR - Text Messaging

TOOLS:
1. messages_send - Send message
   • recipient: Phone, email, or contact name
   • message: Text to send
   • service: iMessage or SMS (default: iMessage)

2. messages_get_conversations - List conversations
   • limit: Max conversations (default: 10)
   • include_messages: Include recent messages

3. messages_get_conversation - Get specific chat
   • recipient: Contact identifier
   • limit: Max messages (default: 20)

4. messages_search - Search messages
   • query: Search text
   • limit: Max results

5. messages_get_unread - Get unread messages
   • limit: Max messages (default: 50)

6. messages_mark_read - Mark as read
   • recipient: Conversation to mark

7. messages_delete_conversation - Delete chat
   • recipient: Conversation to delete
   • confirm: Must be true

8. messages_send_file - Send attachment
   • recipient: Contact identifier
   • file_path: File to send
   • message: Optional text

9. messages_get_status - Get app status
10. messages_create_group - Create group message
    • recipients: List of contacts
    • message: Initial message
    • group_name: Optional name

RESOURCES:
- messages://conversations - All chats
- messages://unread - Unread messages
- messages://recent - Recent activity
"""

            if app == "finder" or app == "all":
                finder_guide = """
FINDER CONNECTOR - File System Operations

TOOLS:
1. finder_open_folder - Open folder
   • path: Folder path
   • new_window: Open in new window

2. finder_get_selection - Get selected items
3. finder_select_items - Select items
   • paths: List of paths to select

4. finder_move_to_trash - Trash items
   • paths: Items to trash

5. finder_empty_trash - Empty trash
   • confirm: Must be true

6. finder_get_info - Get file/folder info
   • path: Item path

7. finder_create_folder - Create folder
   • parent_path: Where to create
   • folder_name: New folder name

8. finder_duplicate_items - Duplicate items
   • paths: Items to duplicate

9. finder_set_view - Change view mode
   • view_mode: icon, list, column, cover flow

10. finder_search - Search for files
    • query: Search query
    • location: Search scope

RESOURCES:
- finder://desktop - Desktop items
- finder://selection - Selected items
- finder://trash - Trash contents
"""

                terminal_guide = """
TERMINAL CONNECTOR - Command Line Automation

TOOLS:
1. terminal_execute_command - Execute command and get output
   • command: Command to execute
   • wait_for_output: Wait for completion (default: true)
   • timeout: Max wait time in seconds (default: 10)

2. terminal_new_tab - Open new Terminal tab (preferred over windows)
   • command: Optional command to run
   • title: Optional tab title

3. terminal_get_output - Get visible Terminal output
   • lines: Number of lines to retrieve (default: 50)

4. terminal_list_tabs - List all Terminal tabs
5. terminal_switch_tab - Switch to specific tab
   • tab_index: Tab number (1-based)

6. terminal_close_tab - Close Terminal tab
   • tab_index: Tab to close (default: current)

7. terminal_clear_screen - Clear Terminal screen
8. terminal_send_text - Send text without executing
   • text: Text to send
   • execute: Press enter after (default: false)

9. terminal_get_working_directory - Get current directory
10. terminal_set_tab_title - Set tab title
    • title: New title
    • tab_index: Tab number (default: current)

RESOURCES:
- terminal_sessions - Active Terminal session info
- terminal_history - Recent command history

BEST PRACTICES:
• Always use tabs instead of new windows
• Check command output after execution
• Use wait_for_output=true for important commands
• Set meaningful tab titles for organization
• Handle timeouts gracefully for long operations
"""

            # Build response based on requested app
            content = "MCP Desktop Gateway - App Connectors Guide\n\n"
            
            if app == "all":
                content += "The MCP Desktop Gateway includes specialized connectors for automating common macOS applications.\n\n"
                content += safari_guide + "\n" + contacts_guide + "\n" + messages_guide + "\n" + finder_guide + "\n" + terminal_guide
            elif app == "safari":
                content += safari_guide
            elif app == "contacts":
                content += contacts_guide
            elif app == "messages":
                content += messages_guide
            elif app == "finder":
                content += finder_guide
            elif app == "terminal":
                content += terminal_guide
            else:
                content += f"Unknown app: {app}\n\nAvailable apps: safari, contacts, messages, finder, terminal\nUse 'all' to see documentation for all apps."
            
            content += "\n\nUSAGE TIPS:\n"
            content += "1. App connectors are automatically available when AppleScript connector is enabled\n"
            content += "2. Tools are namespaced by app (e.g., safari_open_url, contacts_search)\n"
            content += "3. Most operations require the target app to be installed\n"
            content += "4. Some operations may require accessibility permissions\n"
            content += "5. Always handle errors gracefully as app states can vary"
            
            return PromptResult(
                content=content,
                metadata={"connector": self.name, "prompt": prompt_name, "app": app}
            )
        
        elif prompt_name == "terminal_automation":
            content = """Terminal Automation Guide - AppleScript vs Shell

The MCP Desktop Gateway provides TWO ways to run terminal commands:
1. Shell Connector - Direct command execution
2. AppleScript Terminal Connector - Full Terminal.app automation

WHEN TO USE SHELL CONNECTOR:
✓ Quick, one-off commands
✓ Simple file operations
✓ Getting system information
✓ Commands that complete quickly
✓ Non-interactive scripts
✓ Piped commands with simple output

Examples:
- ls -la
- cat file.txt
- df -h
- ps aux | grep python

WHEN TO USE APPLESCRIPT TERMINAL CONNECTOR:
✓ Long-running processes (servers, builds, watchers)
✓ Interactive commands requiring user input
✓ Real-time output monitoring
✓ Development servers (npm run dev, rails server)
✓ Multiple terminal sessions/tabs
✓ Commands needing visual feedback
✓ Build processes with streaming output
✓ SSH sessions
✓ Database clients
✓ Any process you'd normally watch in Terminal

Examples:
- npm run dev
- python manage.py runserver
- docker-compose up
- tail -f logfile.log
- ssh user@server
- mysql -u root -p

KEY DIFFERENCES:

Shell Connector:
- Executes in background
- Returns final output only
- 60-second timeout limit
- No interactive capability
- Good for automation scripts

Terminal Connector:
- Opens in Terminal.app
- Real-time output streaming
- No timeout restrictions
- Full interactivity
- Tab management
- Visual feedback
- Persistent sessions

BEST PRACTICES:

1. START WITH SHELL for simple commands:
   execute_command(command="git status")

2. SWITCH TO TERMINAL when you need:
   - To see real-time output
   - To run servers/watchers
   - To interact with prompts
   - To manage multiple sessions

3. TERMINAL WORKFLOW:
   a) Open new tab (not window):
      terminal_new_tab(command="npm run dev", title="Dev Server")
   
   b) Monitor output:
      terminal_get_output(lines=50)
   
   c) Organize with titles:
      terminal_set_tab_title(title="Backend API")
   
   d) Switch between tabs:
      terminal_list_tabs()
      terminal_switch_tab(tab_index=2)

4. COMBINED WORKFLOW:
   - Use Shell to check prerequisites
   - Use Terminal for long-running processes
   - Use Shell for cleanup/verification

Example Development Workflow:
1. shell: execute_command("git pull")
2. shell: execute_command("npm install")
3. terminal: terminal_new_tab(command="npm run dev", title="Frontend")
4. terminal: terminal_new_tab(command="npm run api", title="Backend")
5. terminal: terminal_get_output() to verify both started
6. shell: execute_command("git status") for quick checks

REMEMBER: Terminal automation gives you the full Terminal experience,
while Shell is for quick, headless command execution."""
            
            return PromptResult(
                content=content,
                metadata={"connector": self.name, "prompt": prompt_name}
            )
        
        else:
            return await super().execute_prompt(prompt_name, arguments)