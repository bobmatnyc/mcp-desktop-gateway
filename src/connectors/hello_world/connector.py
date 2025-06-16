"""
Hello World Connector for MCP Gateway
Demonstrates basic functionality with diagnostics, echo, and test tools
"""

import json
import sys
from datetime import datetime
from typing import Any, Dict, List

from core.base_connector import BaseConnector
from core.models import (
    ToolContent, ToolDefinition, ToolResult,
    PromptDefinition, PromptResult
)
from core.resource_models import ResourceDefinition, ResourceResult


class HelloWorldConnector(BaseConnector):
    """Hello World connector demonstrating MCP Gateway capabilities"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.start_time = datetime.now()
        self.request_count = 0
        self.last_requests = []
    
    def get_tools(self) -> List[ToolDefinition]:
        """Define available tools"""
        return [
            ToolDefinition(
                name="hello_world",
                description="Greet the user with MCP Gateway information",
                input_schema={
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Name to greet (optional)"
                        }
                    }
                }
            ),
            ToolDefinition(
                name="gateway_diagnostics",
                description="Get MCP Gateway diagnostics and service information",
                input_schema={
                    "type": "object",
                    "properties": {
                        "verbose": {
                            "type": "boolean",
                            "description": "Include detailed diagnostics"
                        }
                    }
                }
            ),
            ToolDefinition(
                name="echo",
                description="Echo back user input with metadata",
                input_schema={
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "description": "Message to echo back"
                        },
                        "include_metadata": {
                            "type": "boolean",
                            "description": "Include request metadata"
                        }
                    },
                    "required": ["message"]
                }
            )
        ]
    
    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> ToolResult:
        """Execute the requested tool"""
        self.request_count += 1
        self._log_request("tool", tool_name, arguments)
        
        if tool_name == "hello_world":
            user_name = arguments.get("name", "User")
            message = f"""Hello {user_name}! 👋

Welcome to MCP Gateway
Service: mcp-gateway
Connector: {self.name}
Version: {self.version}

This is the unified MCP Gateway that connects Claude Desktop to various services through modular connectors.

Current Status: ✅ Operational
Uptime: {self._get_uptime()}
Requests Handled: {self.request_count}"""
            
            return ToolResult(
                content=[ToolContent(type="text", text=message)]
            )
        
        elif tool_name == "gateway_diagnostics":
            verbose = arguments.get("verbose", False)
            diagnostics = self._get_diagnostics(verbose)
            
            return ToolResult(
                content=[ToolContent(type="text", text=diagnostics)]
            )
        
        elif tool_name == "echo":
            message = arguments.get("message", "")
            include_metadata = arguments.get("include_metadata", False)
            
            response = f"Echo: {message}"
            
            if include_metadata:
                metadata = {
                    "timestamp": datetime.now().isoformat(),
                    "request_number": self.request_count,
                    "message_length": len(message),
                    "connector": self.name,
                    "service": "mcp-gateway"
                }
                response += f"\n\nMetadata:\n{json.dumps(metadata, indent=2)}"
            
            return ToolResult(
                content=[ToolContent(type="text", text=response)]
            )
        
        else:
            return ToolResult(
                content=[ToolContent(type="text", text=f"Unknown tool: {tool_name}")],
                is_error=True,
                error_message=f"Tool '{tool_name}' not found in {self.name}"
            )
    
    def get_resources(self) -> List[ResourceDefinition]:
        """Define available resources"""
        return [
            ResourceDefinition(
                uri="gateway://hello/config",
                name="Hello World Configuration",
                description="Current hello world connector configuration",
                mimeType="application/json"
            ),
            ResourceDefinition(
                uri="gateway://hello/status",
                name="Connector Status",
                description="Hello world connector status and metrics",
                mimeType="application/json"
            ),
            ResourceDefinition(
                uri="gateway://hello/logs",
                name="Activity Logs",
                description="Recent hello world connector activity",
                mimeType="text/plain"
            )
        ]
    
    async def read_resource(self, uri: str) -> ResourceResult:
        """Read the requested resource"""
        self.request_count += 1
        self._log_request("resource", uri, {})
        
        if uri == "gateway://hello/config":
            config = {
                "connector": {
                    "name": self.name,
                    "version": self.version,
                    "type": "hello_world"
                },
                "features": {
                    "tools": ["hello_world", "gateway_diagnostics", "echo"],
                    "resources": ["config", "status", "logs"],
                    "prompts": ["quick_test", "debug_info"]
                },
                "configuration": self.config
            }
            
            return ResourceResult(
                content=json.dumps(config, indent=2),
                mimeType="application/json"
            )
        
        elif uri == "gateway://hello/status":
            status = {
                "status": "operational",
                "connector": self.name,
                "uptime": self._get_uptime(),
                "metrics": {
                    "total_requests": self.request_count,
                    "start_time": self.start_time.isoformat(),
                    "current_time": datetime.now().isoformat()
                }
            }
            
            return ResourceResult(
                content=json.dumps(status, indent=2),
                mimeType="application/json"
            )
        
        elif uri == "gateway://hello/logs":
            logs = f"=== {self.name} Activity Logs ===\n\n"
            logs += f"Connector Started: {self.start_time.isoformat()}\n"
            logs += f"Total Requests: {self.request_count}\n\n"
            
            if self.last_requests:
                logs += "Recent Requests:\n"
                for req in self.last_requests[-10:]:
                    logs += f"  [{req['timestamp']}] {req['type']}: {req['name']} {req['args']}\n"
            else:
                logs += "No requests logged yet.\n"
            
            return ResourceResult(
                content=logs,
                mimeType="text/plain"
            )
        
        else:
            raise ValueError(f"Resource not found: {uri}")
    
    def get_prompts(self) -> List[PromptDefinition]:
        """Define available prompts"""
        return [
            self._create_prompt_definition(
                name="hello_quick_test",
                description="Quick test of hello world connector features",
                arguments=[]
            ),
            self._create_prompt_definition(
                name="hello_debug_info",
                description="Get debug information from hello world connector",
                arguments=[]
            )
        ]
    
    async def execute_prompt(self, prompt_name: str, arguments: Dict[str, Any]) -> PromptResult:
        """Execute the requested prompt"""
        if prompt_name == "hello_quick_test":
            content = """Test the Hello World connector in MCP Gateway:

1. First, greet me using the hello_world tool
2. Then, show diagnostics using the gateway_diagnostics tool with verbose=true
3. Echo this message: "MCP Gateway is working!" using the echo tool with include_metadata=true
4. Read and display the gateway://hello/status resource
5. Finally, read the gateway://hello/logs resource

This will verify the hello world connector is working correctly."""
            
            return PromptResult(
                content=content,
                metadata={"connector": self.name, "prompt": prompt_name}
            )
        
        elif prompt_name == "hello_debug_info":
            content = """Gather debug information from the hello world connector:

1. Run gateway_diagnostics tool with verbose=true
2. Read all three resources:
   - gateway://hello/config
   - gateway://hello/status
   - gateway://hello/logs
3. Test the echo tool with current timestamp
4. Summarize the connector health

This helps troubleshoot any issues with the hello world connector."""
            
            return PromptResult(
                content=content,
                metadata={"connector": self.name, "prompt": prompt_name}
            )
        
        else:
            return await super().execute_prompt(prompt_name, arguments)
    
    def _get_uptime(self) -> str:
        """Calculate and format uptime"""
        uptime = datetime.now() - self.start_time
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours}h {minutes}m {seconds}s"
    
    def _get_diagnostics(self, verbose: bool = False) -> str:
        """Generate diagnostics information"""
        diag = f"""=== MCP Gateway Diagnostics ===
Service: mcp-gateway
Connector: {self.name}
Version: {self.version}
Status: ✅ Operational

System Information:
- Python Version: {sys.version.split()[0]}
- Platform: {sys.platform}
- Start Time: {self.start_time.isoformat()}
- Uptime: {self._get_uptime()}

Connector Metrics:
- Total Requests: {self.request_count}
- Tools Available: 3 (hello_world, gateway_diagnostics, echo)
- Resources Available: 3 (config, status, logs)
- Prompts Available: 2 (hello_quick_test, hello_debug_info)"""
        
        if verbose:
            import os
            diag += f"""

Detailed Information:
- Process ID: {os.getpid()}
- Working Directory: {os.getcwd()}
- Configuration: {json.dumps(self.config, indent=2)}
- Last 5 Requests:"""
            
            if self.last_requests:
                for req in self.last_requests[-5:]:
                    diag += f"\n  - [{req['timestamp']}] {req['type']}: {req['name']}"
            else:
                diag += "\n  - No requests logged yet"
        
        return diag
    
    def _log_request(self, req_type: str, name: str, args: Dict[str, Any]):
        """Log request for activity tracking"""
        request = {
            "timestamp": datetime.now().isoformat(),
            "type": req_type,
            "name": name,
            "args": args
        }
        self.last_requests.append(request)
        
        # Keep only last 100 requests
        if len(self.last_requests) > 100:
            self.last_requests = self.last_requests[-100:]
        
        self.logger.info(f"Request: {req_type}:{name} - Args: {args}")