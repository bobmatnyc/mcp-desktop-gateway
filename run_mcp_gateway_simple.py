#!/usr/bin/env python3
"""
Simple MCP Gateway - Minimal working version for POC1
"""

import asyncio
import logging
import sys
import os

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.stdio import stdio_server

# Configure logging to stderr only
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

# Simple server implementation
server = Server("mcp-gateway")

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available tools"""
    return [
        types.Tool(
            name="hello_world",
            description="Simple hello world greeting",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name to greet"
                    }
                }
            }
        ),
        types.Tool(
            name="gateway_info",
            description="Get MCP Gateway information",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    """Handle tool calls"""
    logger.info(f"Tool called: {name} with args: {arguments}")
    
    if name == "hello_world":
        user_name = arguments.get("name", "World")
        return [
            types.TextContent(
                type="text",
                text=f"Hello {user_name}! This is MCP Gateway v1.0.0"
            )
        ]
    elif name == "gateway_info":
        return [
            types.TextContent(
                type="text",
                text="""MCP Gateway Information:
- Service: mcp-gateway
- Version: 1.0.0
- Status: Running
- Tools: 2 (hello_world, gateway_info)
- Description: Universal bridge for Claude Desktop"""
            )
        ]
    else:
        raise ValueError(f"Unknown tool: {name}")

async def main():
    """Main entry point"""
    print("Starting MCP Gateway (Simple)...", file=sys.stderr)
    
    # Run the server
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="mcp-gateway",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={}
                )
            )
        )

if __name__ == "__main__":
    asyncio.run(main())