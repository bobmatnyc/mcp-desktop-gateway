"""
Gateway Utilities Connector
Provides built-in utility tools for the MCP Gateway
"""

import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, List

from core.base_connector import BaseConnector
from core.models import (
    ToolContent, ToolDefinition, ToolResult,
    PromptDefinition, PromptResult
)
from core.resource_models import ResourceDefinition, ResourceResult


class GatewayUtilsConnector(BaseConnector):
    """Built-in utilities for MCP Gateway"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.start_time = datetime.now()
        
    def get_tools(self) -> List[ToolDefinition]:
        """Define utility tools"""
        return [
            ToolDefinition(
                name="list_connectors",
                description="List all active connectors in the MCP Gateway",
                input_schema={
                    "type": "object",
                    "properties": {
                        "include_disabled": {
                            "type": "boolean",
                            "description": "Include disabled connectors"
                        }
                    },
                    "required": []
                }
            ),
            ToolDefinition(
                name="gateway_health",
                description="Check health status of the MCP Gateway",
                input_schema={
                    "type": "object",
                    "properties": {}
                }
            ),
            ToolDefinition(
                name="reload_config",
                description="Reload gateway configuration (Note: requires restart for some changes)",
                input_schema={
                    "type": "object",
                    "properties": {}
                }
            )
        ]
    
    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> ToolResult:
        """Execute utility tools"""
        
        if tool_name == "list_connectors":
            # Access the registry through the parent gateway
            from core.registry import ConnectorRegistry
            from core.config import ConfigManager
            
            config = ConfigManager()
            include_disabled = arguments.get("include_disabled", False)
            
            result = "=== MCP Gateway Connectors ===\n\n"
            result += "Active Connectors:\n"
            
            # List active connectors from config
            for conn_config in config.get_connector_configs():
                if conn_config.enabled or include_disabled:
                    status = "✅ Enabled" if conn_config.enabled else "❌ Disabled"
                    result += f"  - {conn_config.name}: {status}\n"
                    if conn_config.config:
                        result += f"    Config: {json.dumps(conn_config.config, indent=6)}\n"
            
            return ToolResult(
                content=[ToolContent(type="text", text=result)]
            )
        
        elif tool_name == "gateway_health":
            health = {
                "status": "healthy",
                "gateway": {
                    "name": "mcp-gateway",
                    "version": "1.0.0",
                    "uptime": str(datetime.now() - self.start_time),
                    "python_version": sys.version.split()[0],
                    "platform": sys.platform,
                    "pid": os.getpid()
                },
                "timestamp": datetime.now().isoformat()
            }
            
            result = "=== MCP Gateway Health ===\n\n"
            result += f"Status: ✅ {health['status'].upper()}\n"
            result += f"Uptime: {health['gateway']['uptime']}\n"
            result += f"Python: {health['gateway']['python_version']}\n"
            result += f"Platform: {health['gateway']['platform']}\n"
            result += f"Process ID: {health['gateway']['pid']}\n"
            result += f"\nFull Details:\n{json.dumps(health, indent=2)}"
            
            return ToolResult(
                content=[ToolContent(type="text", text=result)]
            )
        
        elif tool_name == "reload_config":
            try:
                from core.config import ConfigManager
                config = ConfigManager()
                config.reload()
                
                result = "✅ Configuration reloaded successfully!\n\n"
                result += "Note: Some changes may require restarting the gateway:\n"
                result += "- New connectors\n"
                result += "- Connector enable/disable changes\n"
                result += "- Server configuration changes"
                
                return ToolResult(
                    content=[ToolContent(type="text", text=result)]
                )
            except Exception as e:
                return ToolResult(
                    content=[ToolContent(type="text", text=f"Failed to reload config: {str(e)}")],
                    is_error=True,
                    error_message=str(e)
                )
        
        else:
            return ToolResult(
                content=[ToolContent(type="text", text=f"Unknown tool: {tool_name}")],
                is_error=True,
                error_message=f"Tool '{tool_name}' not found"
            )
    
    def get_resources(self) -> List[ResourceDefinition]:
        """Define utility resources"""
        return [
            ResourceDefinition(
                uri="gateway://utils/config",
                name="Gateway Configuration",
                description="Current gateway configuration",
                mimeType="application/json"
            ),
            ResourceDefinition(
                uri="gateway://utils/environment",
                name="Environment Variables",
                description="Gateway-related environment variables",
                mimeType="application/json"
            ),
            ResourceDefinition(
                uri="gateway://utils/manifest",
                name="Gateway Manifest",
                description="Complete gateway manifest with all tools, resources, and prompts",
                mimeType="application/json"
            )
        ]
    
    async def read_resource(self, uri: str) -> ResourceResult:
        """Read utility resources"""
        
        if uri == "gateway://utils/config":
            from core.config import ConfigManager
            config = ConfigManager()
            
            config_data = {
                "server": {
                    "name": config.get_server_config().name,
                    "version": config.get_server_config().version,
                    "log_level": config.get_server_config().log_level
                },
                "connectors": [
                    {
                        "name": c.name,
                        "enabled": c.enabled,
                        "config": c.config
                    }
                    for c in config.get_connector_configs()
                ],
                "config_path": config.config_path
            }
            
            return ResourceResult(
                content=json.dumps(config_data, indent=2),
                mimeType="application/json"
            )
        
        elif uri == "gateway://utils/environment":
            # Get gateway-related environment variables
            env_vars = {
                "PYTHONPATH": os.getenv("PYTHONPATH", "Not set"),
                "MCP_GATEWAY_CONFIG": os.getenv("MCP_GATEWAY_CONFIG", "Not set"),
                "MCP_GATEWAY_DEBUG": os.getenv("MCP_GATEWAY_DEBUG", "Not set"),
                "MCP_GATEWAY_PORT": os.getenv("MCP_GATEWAY_PORT", "Not set"),
                "PATH": os.getenv("PATH", "Not set")
            }
            
            return ResourceResult(
                content=json.dumps(env_vars, indent=2),
                mimeType="application/json"
            )
        
        elif uri == "gateway://utils/manifest":
            # This would need access to the registry, so we'll provide a template
            manifest = {
                "gateway": {
                    "name": "mcp-gateway",
                    "version": "1.0.0",
                    "description": "MCP Gateway - Universal bridge for Claude Desktop"
                },
                "connector": {
                    "name": self.name,
                    "description": "Built-in gateway utilities"
                },
                "capabilities": {
                    "tools": [t.name for t in self.get_tools()],
                    "resources": [r.uri for r in self.get_resources()],
                    "prompts": [p.name for p in self.get_prompts()]
                },
                "note": "Use list_connectors tool to see all available connectors"
            }
            
            return ResourceResult(
                content=json.dumps(manifest, indent=2),
                mimeType="application/json"
            )
        
        else:
            raise ValueError(f"Resource not found: {uri}")
    
    def get_prompts(self) -> List[PromptDefinition]:
        """Define utility prompts"""
        return [
            self._create_prompt_definition(
                name="gateway_status",
                description="Get complete gateway status including health and connectors",
                arguments=[]
            ),
            self._create_prompt_definition(
                name="troubleshoot_gateway",
                description="Troubleshoot common gateway issues",
                arguments=[
                    {
                        "name": "issue",
                        "description": "Describe the issue you're experiencing",
                        "required": False,
                        "type": "string"
                    }
                ]
            ),
            self._create_prompt_definition(
                name="complete_services_guide",
                description="Get comprehensive guide on all MCP Desktop Gateway services",
                arguments=[]
            )
        ]
    
    async def execute_prompt(self, prompt_name: str, arguments: Dict[str, Any]) -> PromptResult:
        """Execute utility prompts"""
        
        if prompt_name == "gateway_status":
            content = """Check the complete MCP Gateway status:

1. First, check gateway health using the gateway_health tool
2. List all connectors using the list_connectors tool with include_disabled=true
3. Read the gateway://utils/config resource to see full configuration
4. Read the gateway://utils/environment resource to check environment
5. Read the gateway://utils/manifest resource for capabilities
6. Summarize the gateway status and any potential issues

This will give you a complete overview of the MCP Gateway."""
            
            return PromptResult(
                content=content,
                metadata={"connector": self.name, "prompt": prompt_name}
            )
        
        elif prompt_name == "troubleshoot_gateway":
            issue = arguments.get("issue", "general")
            
            content = f"""Troubleshooting MCP Gateway{f' - Issue: {issue}' if issue != 'general' else ''}:

1. Check gateway health with gateway_health tool
2. List connectors with list_connectors tool (include_disabled=true)
3. Read gateway://utils/config to verify configuration
4. Read gateway://utils/environment to check environment setup

Common issues to check:
- Connector not appearing: Check if it's enabled in config
- Tool not found: Verify connector is loaded and initialized
- Connection errors: Check environment variables and paths
- Python errors: Verify PYTHONPATH includes the gateway src directory

Specific debugging steps:
- Check Claude Desktop logs at ~/Library/Logs/Claude/mcp*.log
- Look for Python tracebacks or initialization errors
- Verify all dependencies are installed: pip install -r requirements.txt

After gathering information, analyze the results and suggest solutions."""
            
            return PromptResult(
                content=content,
                metadata={
                    "connector": self.name,
                    "prompt": prompt_name,
                    "issue": issue
                }
            )
        
        elif prompt_name == "complete_services_guide":
            content = """MCP Desktop Gateway - Complete Services Guide

The MCP Desktop Gateway provides comprehensive automation and integration capabilities through multiple specialized connectors.

=== CORE CONNECTORS ===

1. SHELL CONNECTOR
Purpose: Script writing, system commands, and file operations
Key Tools:
• execute_command - Write scripts locally AND run shell commands
• list_directory - Browse file system
• get_system_info - Get system information
Primary Uses:
• SCRIPT WRITING - Create Python, JavaScript, Shell scripts locally
• Quick commands without visual feedback
• File system verification after script execution
Resources:
• shell://env - Environment variables
• shell://cwd - Current working directory
Prompts:
• shell_help - Script writing and command guidelines
• system_analysis - Basic system diagnostics
• user_scripts_guide - User scripts management

2. APPLESCRIPT CONNECTOR (macOS)
Purpose: macOS application automation and script execution
Basic Tools:
• run_applescript - Execute custom AppleScript
• system_notification - Display notifications
• control_app - Manage applications
• get/set_clipboard - Clipboard operations
App-Specific Connectors:
• Safari - Web browser automation (15 tools)
• Contacts - Contact management (10 tools)
• Messages - Text messaging (10 tools)
• Finder - File system GUI (10 tools)
• Terminal - Script execution with visual feedback (10 tools)
Terminal Connector Features:
• SCRIPT EXECUTION - Run scripts with real-time output
• Tab management (single window, multiple tabs)
• Visual feedback for user interaction
• No timeout restrictions
• Process monitoring
Resources:
• applescript://apps - Running applications
• applescript://system - System information
• terminal_sessions - Active Terminal sessions
• terminal_history - Command history
Prompts:
• applescript_help - Complete AppleScript guide
• app_connectors_guide - App-specific documentation
• automate_task - Task automation guidance
• terminal_automation - Shell vs Terminal usage guide

3. GATEWAY UTILS CONNECTOR
Purpose: Gateway management and diagnostics
Tools:
• list_connectors - Show available connectors
• gateway_health - Health check
• reload_config - Reload configuration
Resources:
• gateway://utils/config - Configuration
• gateway://utils/manifest - Service manifest
Prompts:
• gateway_status - Complete status check
• troubleshoot_gateway - Issue resolution
• complete_services_guide - This guide

4. HELLO WORLD CONNECTOR
Purpose: Testing and demonstration
Tools:
• hello_world - Basic greeting
• gateway_info - Gateway information
• echo - Echo input back
Resources:
• gateway://hello/status - Connector status
• gateway://hello/logs - Recent logs

=== USER SCRIPTS SYSTEM ===

Directory Structure:
user-scripts/
├── python/         # Python scripts
├── javascript/     # Node.js scripts
├── shell/         # Shell scripts
├── applescript/   # AppleScript files
└── shared/        # Shared resources

Management:
• Use manage.py to create, list, archive scripts
• Templates provided for each language
• Automatic naming convention: YYYY-MM-DD_task-name_language.ext
• Scripts in 'active' directories are .gitignored

Execution:
• Run via execute_command tool
• Access shared data and configs
• Write logs to shared/logs/

=== CONFIGURATION ===

Files:
• config/config.yaml - Main configuration
• config/config.dev.yaml - Development settings
• claude_desktop_config.json - Claude Desktop integration

Key Settings:
• Connector enable/disable
• Command timeouts
• Security restrictions
• Logging levels

=== INTEGRATION TIPS ===

1. Combine Connectors:
   - Use shell to prepare files, then AppleScript to process in apps
   - Check system state with utils before automation

2. Error Handling:
   - All tools return structured error messages
   - Check logs for detailed debugging
   - Use health checks to verify status

3. Security:
   - Shell commands are filtered for dangerous patterns
   - AppleScript has timeout protection
   - User scripts are isolated from main code

4. Best Practices:
   - Test commands individually first
   - Use resources to check state before actions
   - Leverage prompts for task-specific guidance
   - Keep user scripts organized by task

=== COMMON WORKFLOWS ===

1. SCRIPT DEVELOPMENT WORKFLOW (RECOMMENDED):
   Script Writing → Execution → Verification
   
   a) Write script using Shell:
      - execute_command('cat > process_data.py << EOF
        #!/usr/bin/env python3
        import pandas as pd
        # Your code here
        EOF')
   
   b) Execute in Terminal for visual feedback:
      - terminal_new_tab(command="python process_data.py", title="Data Processing")
      - User can see real-time output and interact if needed
   
   c) Verify results in BOTH places:
      - Terminal output: terminal_get_output()
      - File system: execute_command("ls -la output/")
   
   This pattern ensures:
   - Scripts are written locally (Shell)
   - Execution has visual feedback (Terminal)
   - Results are verified comprehensively

2. Web Automation:
   - Use safari_open_url to navigate
   - safari_execute_javascript for page interaction
   - safari_get_page_source for scraping

3. Contact Management:
   - contacts_search to find people
   - contacts_create/update for modifications
   - contacts_export_vcard for backups

4. File Operations:
   - shell commands for bulk operations
   - finder tools for GUI-based selection
   - user scripts for repeated tasks

5. Messaging:
   - messages_send for notifications
   - messages_get_conversations for monitoring
   - messages_send_file for sharing

6. Parallel Processing:
   - Open multiple Terminal tabs for concurrent operations
   - terminal_new_tab(command="npm run frontend", title="Frontend")
   - terminal_new_tab(command="npm run backend", title="Backend")
   - Switch between tabs to monitor progress

=== GETTING HELP ===

1. Use connector-specific prompts:
   - shell_help for command safety
   - applescript_help for automation basics
   - app_connectors_guide for app details

2. Check resources:
   - List available with gateway://utils/manifest
   - Read current state before actions

3. Review logs:
   - ~/Library/Logs/Claude/mcp-server-*.log
   - user-scripts/shared/logs/

This guide covers all major services. For specific details, use the individual connector prompts."""
            
            return PromptResult(
                content=content,
                metadata={"connector": self.name, "prompt": prompt_name}
            )
        
        else:
            return await super().execute_prompt(prompt_name, arguments)