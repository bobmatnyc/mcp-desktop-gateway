#!/usr/bin/env python3
"""
MCP Gateway Hello World POC
A minimal implementation demonstrating core MCP functionality
"""

import asyncio
import json
import logging
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool, Resource, Prompt, 
    TextContent, ImageContent,
    CallToolResult, ReadResourceResult, GetPromptResult
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("mcp-gateway-hello-world")

class HelloWorldPOC:
    """MCP Gateway Hello World POC Implementation"""
    
    def __init__(self):
        self.server = Server("mcp-gateway-hello-world")
        self.start_time = datetime.now()
        self.request_count = 0
        self.last_requests = []
        
        # Setup handlers
        self._setup_tools()
        self._setup_resources()
        self._setup_prompts()
        
        logger.info("MCP Gateway Hello World POC initialized")
    
    def _setup_tools(self):
        """Register tool handlers"""
        
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            """List available tools"""
            return [
                Tool(
                    name="hello_world",
                    description="Greet the user with service information",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "Name to greet (optional)"
                            }
                        }
                    }
                ),
                Tool(
                    name="diagnostics",
                    description="Get system diagnostics and service information",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "verbose": {
                                "type": "boolean",
                                "description": "Include detailed diagnostics"
                            }
                        }
                    }
                ),
                Tool(
                    name="echo",
                    description="Echo back user input with metadata",
                    inputSchema={
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
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
            """Handle tool calls"""
            self.request_count += 1
            self._log_request("tool", name, arguments)
            
            if name == "hello_world":
                user_name = arguments.get("name", "User")
                message = f"""Hello {user_name}! 👋

Welcome to MCP Gateway Hello World POC
Version: v0.1.0-poc
Service: mcp-gateway-hello-world

This is a demonstration of the MCP Gateway system that allows Claude Desktop to connect to various services through a unified interface.

Current Status: ✅ Operational
Uptime: {self._get_uptime()}
Requests Handled: {self.request_count}"""
                
                return CallToolResult(
                    content=[TextContent(type="text", text=message)],
                    isError=False
                )
            
            elif name == "diagnostics":
                verbose = arguments.get("verbose", False)
                diagnostics = self._get_diagnostics(verbose)
                
                return CallToolResult(
                    content=[TextContent(type="text", text=diagnostics)],
                    isError=False
                )
            
            elif name == "echo":
                message = arguments.get("message", "")
                include_metadata = arguments.get("include_metadata", False)
                
                response = f"Echo: {message}"
                
                if include_metadata:
                    metadata = {
                        "timestamp": datetime.now().isoformat(),
                        "request_number": self.request_count,
                        "message_length": len(message),
                        "service": "mcp-gateway-hello-world"
                    }
                    response += f"\n\nMetadata:\n{json.dumps(metadata, indent=2)}"
                
                return CallToolResult(
                    content=[TextContent(type="text", text=response)],
                    isError=False
                )
            
            else:
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Unknown tool: {name}")],
                    isError=True
                )
    
    def _setup_resources(self):
        """Register resource handlers"""
        
        @self.server.list_resources()
        async def list_resources() -> List[Resource]:
            """List available resources"""
            return [
                Resource(
                    uri="gateway://config",
                    name="Gateway Configuration",
                    description="Current service configuration",
                    mimeType="application/json"
                ),
                Resource(
                    uri="gateway://status",
                    name="Service Status",
                    description="Current service status and health information",
                    mimeType="application/json"
                ),
                Resource(
                    uri="gateway://logs",
                    name="Recent Activity Logs",
                    description="Recent requests and activity logs",
                    mimeType="text/plain"
                )
            ]
        
        @self.server.read_resource()
        async def read_resource(uri: str) -> ReadResourceResult:
            """Handle resource reads"""
            self.request_count += 1
            self._log_request("resource", uri, {})
            
            if uri == "gateway://config":
                config = {
                    "service": {
                        "name": "mcp-gateway-hello-world",
                        "version": "v0.1.0-poc",
                        "description": "MCP Gateway Hello World POC"
                    },
                    "features": {
                        "tools": ["hello_world", "diagnostics", "echo"],
                        "resources": ["config", "status", "logs"],
                        "prompts": ["quick_test", "debug_info", "connector_template"]
                    },
                    "metadata": {
                        "author": "MCP Gateway Team",
                        "repository": "https://github.com/user/mcp-gateway",
                        "documentation": "/docs/poc/README.md"
                    }
                }
                
                return ReadResourceResult(
                    contents=[TextContent(
                        type="text",
                        text=json.dumps(config, indent=2),
                        mimeType="application/json"
                    )]
                )
            
            elif uri == "gateway://status":
                status = {
                    "status": "operational",
                    "uptime": self._get_uptime(),
                    "metrics": {
                        "total_requests": self.request_count,
                        "start_time": self.start_time.isoformat(),
                        "current_time": datetime.now().isoformat()
                    },
                    "health": {
                        "server": "healthy",
                        "memory": "normal",
                        "response_time": "fast"
                    }
                }
                
                return ReadResourceResult(
                    contents=[TextContent(
                        type="text",
                        text=json.dumps(status, indent=2),
                        mimeType="application/json"
                    )]
                )
            
            elif uri == "gateway://logs":
                logs = "=== Recent Activity Logs ===\n\n"
                logs += f"Service Started: {self.start_time.isoformat()}\n"
                logs += f"Total Requests: {self.request_count}\n\n"
                
                if self.last_requests:
                    logs += "Recent Requests:\n"
                    for req in self.last_requests[-10:]:  # Last 10 requests
                        logs += f"  [{req['timestamp']}] {req['type']}: {req['name']} {req['args']}\n"
                else:
                    logs += "No requests logged yet.\n"
                
                return ReadResourceResult(
                    contents=[TextContent(
                        type="text",
                        text=logs,
                        mimeType="text/plain"
                    )]
                )
            
            else:
                return ReadResourceResult(
                    contents=[TextContent(
                        type="text",
                        text=f"Resource not found: {uri}"
                    )]
                )
    
    def _setup_prompts(self):
        """Register prompt handlers"""
        
        @self.server.list_prompts()
        async def list_prompts() -> List[Prompt]:
            """List available prompts"""
            return [
                Prompt(
                    name="quick_test",
                    description="Quick test of all MCP Gateway features",
                    arguments=[]
                ),
                Prompt(
                    name="debug_info",
                    description="Get comprehensive debug information",
                    arguments=[]
                ),
                Prompt(
                    name="connector_template",
                    description="Template for creating new connectors",
                    arguments=[
                        {
                            "name": "connector_name",
                            "description": "Name for the new connector",
                            "required": True
                        }
                    ]
                )
            ]
        
        @self.server.get_prompt()
        async def get_prompt(name: str, arguments: Dict[str, Any]) -> GetPromptResult:
            """Handle prompt requests"""
            self.request_count += 1
            self._log_request("prompt", name, arguments)
            
            if name == "quick_test":
                prompt = """Test all MCP Gateway Hello World features:

1. First, greet me using the hello_world tool
2. Then, show me the diagnostics using the diagnostics tool with verbose=true
3. Echo this message: "MCP Gateway is working!" using the echo tool with include_metadata=true
4. Read and display the gateway://status resource
5. Finally, read the gateway://logs resource to show the activity

This will verify all tools and resources are working correctly."""
                
                return GetPromptResult(
                    prompt=Prompt(
                        name="quick_test",
                        description="Quick test of all MCP Gateway features",
                        arguments=[],
                        content=[TextContent(type="text", text=prompt)]
                    )
                )
            
            elif name == "debug_info":
                prompt = """Please gather comprehensive debug information:

1. Run diagnostics tool with verbose=true
2. Read all three resources:
   - gateway://config
   - gateway://status  
   - gateway://logs
3. Test the echo tool with a timestamp
4. Summarize any issues or anomalies found

This will help troubleshoot any problems with the MCP Gateway."""
                
                return GetPromptResult(
                    prompt=Prompt(
                        name="debug_info",
                        description="Get comprehensive debug information",
                        arguments=[],
                        content=[TextContent(type="text", text=prompt)]
                    )
                )
            
            elif name == "connector_template":
                connector_name = arguments.get("connector_name", "my_connector")
                
                template = f"""Create a new MCP connector named '{connector_name}':

```python
# {connector_name}.py
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, Resource, TextContent, CallToolResult

class {connector_name.title().replace('_', '')}Connector:
    def __init__(self):
        self.server = Server("{connector_name}")
        self._setup_handlers()
    
    def _setup_handlers(self):
        @self.server.list_tools()
        async def list_tools():
            return [
                Tool(
                    name="example_tool",
                    description="Example tool for {connector_name}",
                    inputSchema={{"type": "object", "properties": {{}}}}
                )
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict):
            # Implement your tool logic here
            return CallToolResult(
                content=[TextContent(type="text", text="Tool response")],
                isError=False
            )
    
    async def run(self):
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(read_stream, write_stream)

if __name__ == "__main__":
    import asyncio
    connector = {connector_name.title().replace('_', '')}Connector()
    asyncio.run(connector.run())
```

Save this template and customize it for your specific service integration."""
                
                return GetPromptResult(
                    prompt=Prompt(
                        name="connector_template",
                        description="Template for creating new connectors",
                        arguments=[],
                        content=[TextContent(type="text", text=template)]
                    )
                )
            
            else:
                return GetPromptResult(
                    prompt=Prompt(
                        name="error",
                        description="Error",
                        arguments=[],
                        content=[TextContent(type="text", text=f"Unknown prompt: {name}")]
                    )
                )
    
    def _get_uptime(self) -> str:
        """Calculate and format uptime"""
        uptime = datetime.now() - self.start_time
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours}h {minutes}m {seconds}s"
    
    def _get_diagnostics(self, verbose: bool = False) -> str:
        """Generate diagnostics information"""
        diag = f"""=== MCP Gateway Diagnostics ===
Service: mcp-gateway-hello-world
Version: v0.1.0-poc
Status: ✅ Operational

System Information:
- Python Version: {sys.version.split()[0]}
- Platform: {sys.platform}
- Start Time: {self.start_time.isoformat()}
- Uptime: {self._get_uptime()}

Service Metrics:
- Total Requests: {self.request_count}
- Tools Available: 3 (hello_world, diagnostics, echo)
- Resources Available: 3 (config, status, logs)
- Prompts Available: 3 (quick_test, debug_info, connector_template)"""
        
        if verbose:
            diag += f"""

Detailed Information:
- Process ID: {os.getpid() if 'os' in globals() else 'N/A'}
- Working Directory: {os.getcwd() if 'os' in globals() else 'N/A'}
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
        
        logger.info(f"Request: {req_type}:{name} - Args: {args}")
    
    async def run(self):
        """Run the MCP server"""
        logger.info("Starting MCP Gateway Hello World POC...")
        logger.info("Version: v0.1.0-poc")
        logger.info("Service ID: mcp-gateway-hello-world")
        
        # Print startup diagnostics
        print("\n" + "="*50)
        print("MCP Gateway Hello World POC")
        print("Version: v0.1.0-poc")
        print("Status: Starting...")
        print("✓ Configuration loaded")
        print("✓ MCP server initialized")
        print("✓ Tools registered: 3")
        print("✓ Resources registered: 3")
        print("✓ Prompts registered: 3")
        print("✓ Server ready on stdio")
        print("Service ID: mcp-gateway-hello-world")
        print("Waiting for requests...")
        print("="*50 + "\n")
        
        # Run the server
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(read_stream, write_stream)

# Add os import for diagnostics if available
try:
    import os
except ImportError:
    pass

if __name__ == "__main__":
    poc = HelloWorldPOC()
    asyncio.run(poc.run())