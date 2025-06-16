#!/usr/bin/env python3
"""
Run MCP Gateway with Hello World connector
Simple script for POC testing
"""

import asyncio
import logging
import sys
import os

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from mcp.server import Server, NotificationOptions
from mcp.server.stdio import stdio_server
from mcp.server.models import InitializationOptions
import mcp.types as types
from core.registry import ConnectorRegistry
from core.config import ConfigManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr  # Always log to stderr
)
logger = logging.getLogger(__name__)

# Check for development mode
DEV_MODE = os.environ.get('MCP_DEV_MODE', '').lower() in ('1', 'true', 'yes')
if DEV_MODE:
    logging.getLogger().setLevel(logging.DEBUG)
    logger.info("Running in DEVELOPMENT mode")


class MCPGateway:
    """Main MCP Gateway server"""
    
    def __init__(self):
        self.server = Server("mcp-gateway")
        self.registry = ConnectorRegistry()
        self.config = ConfigManager()
        
    async def initialize(self):
        """Initialize the gateway and connectors"""
        logger.info("Initializing MCP Gateway...")
        
        # Auto-discover connectors
        self.registry.auto_discover_connectors()
        logger.info(f"Discovered connectors: {self.registry.list_registered_classes()}")
        
        # Initialize enabled connectors
        enabled = self.config.get_enabled_connectors()
        logger.info(f"Enabling {len(enabled)} connectors: {[c.name for c in enabled]}")
        
        for conn_config in enabled:
            try:
                await self.registry.initialize_connector(
                    conn_config.name, 
                    conn_config.config
                )
                logger.info(f"✓ Initialized connector: {conn_config.name}")
            except Exception as e:
                logger.error(f"✗ Failed to initialize {conn_config.name}: {e}")
        
        # Set up MCP handlers
        self._setup_handlers()
        
    def _setup_handlers(self):
        """Set up MCP protocol handlers"""
        
        @self.server.list_tools()
        async def list_tools() -> list[types.Tool]:
            """List all available tools from all connectors"""
            all_tools = []
            for connector in self.registry.get_all_connectors():
                tools = connector.get_tools()
                for tool in tools:
                    # Convert ToolDefinition to types.Tool
                    mcp_tool = types.Tool(
                        name=tool.name,
                        description=tool.description,
                        inputSchema=tool.input_schema
                    )
                    all_tools.append(mcp_tool)
            logger.info(f"Listing {len(all_tools)} tools")
            return all_tools
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
            """Route tool calls to appropriate connector"""
            logger.info(f"Tool call: {name} with args: {arguments}")
            
            # Find which connector owns this tool
            for connector in self.registry.get_all_connectors():
                tools = connector.get_tools()
                if any(tool.name == name for tool in tools):
                    result = await connector.execute_tool(name, arguments)
                    # Convert ToolResult to list of TextContent
                    text_contents = []
                    for content in result.content:
                        text_contents.append(types.TextContent(
                            type="text",
                            text=content.text
                        ))
                    return text_contents
            
            # Tool not found
            return [types.TextContent(
                type="text", 
                text=f"Tool not found: {name}"
            )]
        
        @self.server.list_resources()
        async def list_resources() -> list[types.Resource]:
            """List all available resources from all connectors"""
            all_resources = []
            for connector in self.registry.get_all_connectors():
                resources = connector.get_resources()
                for resource in resources:
                    # Convert ResourceDefinition to types.Resource
                    mcp_resource = types.Resource(
                        uri=resource.uri,
                        name=resource.name,
                        description=resource.description,
                        mimeType=resource.mimeType
                    )
                    all_resources.append(mcp_resource)
            logger.info(f"Listing {len(all_resources)} resources")
            return all_resources
        
        @self.server.read_resource()
        async def read_resource(uri: str) -> str:
            """Route resource reads to appropriate connector"""
            logger.info(f"Resource read: {uri}")
            
            # Find which connector owns this resource
            for connector in self.registry.get_all_connectors():
                resources = connector.get_resources()
                if any(resource.uri == uri for resource in resources):
                    result = await connector.read_resource(uri)
                    return result.content
            
            # Resource not found
            return f"Resource not found: {uri}"
        
        @self.server.list_prompts()
        async def list_prompts() -> list[types.Prompt]:
            """List all available prompts from all connectors"""
            all_prompts = []
            for connector in self.registry.get_all_connectors():
                prompts = connector.get_prompts()
                for prompt in prompts:
                    # Convert PromptDefinition to types.Prompt
                    mcp_prompt = types.Prompt(
                        name=prompt.name,
                        description=prompt.description,
                        arguments=[
                            types.PromptArgument(
                                name=arg.name,
                                description=arg.description,
                                required=arg.required
                            ) for arg in prompt.arguments
                        ]
                    )
                    all_prompts.append(mcp_prompt)
            logger.info(f"Listing {len(all_prompts)} prompts")
            return all_prompts
        
        @self.server.get_prompt()
        async def get_prompt(name: str, arguments: dict) -> types.GetPromptResult:
            """Route prompt requests to appropriate connector"""
            logger.info(f"Prompt request: {name} with args: {arguments}")
            
            # Find which connector owns this prompt
            for connector in self.registry.get_all_connectors():
                prompts = connector.get_prompts()
                prompt_def = next((p for p in prompts if p.name == name), None)
                if prompt_def:
                    result = await connector.execute_prompt(name, arguments)
                    return types.GetPromptResult(
                        description=prompt_def.description,
                        messages=[
                            types.PromptMessage(
                                role="user",
                                content=types.TextContent(
                                    type="text",
                                    text=result.content
                                )
                            )
                        ]
                    )
            
            # Prompt not found
            return types.GetPromptResult(
                description="Error: Prompt not found",
                messages=[
                    types.PromptMessage(
                        role="user",
                        content=types.TextContent(
                            type="text",
                            text=f"Prompt not found: {name}"
                        )
                    )
                ]
            )
    
    async def run(self):
        """Run the MCP Gateway"""
        await self.initialize()
        
        print("\n" + "="*50, file=sys.stderr)
        print("MCP Gateway Started", file=sys.stderr)
        print("="*50, file=sys.stderr)
        print(f"Service: mcp-desktop-gateway", file=sys.stderr)
        print(f"Version: {self.config.get_server_config().version}", file=sys.stderr)
        print(f"\nActive Connectors:", file=sys.stderr)
        for connector in self.registry.get_all_connectors():
            print(f"  ✓ {connector.name}", file=sys.stderr)
        print(f"\nTotal Tools: {len(self.registry.get_all_tools())}", file=sys.stderr)
        print("\nReady for Claude Desktop connection", file=sys.stderr)
        print("="*50 + "\n", file=sys.stderr)
        
        # Run the server
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream, 
                write_stream,
                InitializationOptions(
                    server_name="mcp-gateway",
                    server_version=self.config.get_server_config().version,
                    capabilities=self.server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={}
                    )
                )
            )


async def main():
    """Main entry point"""
    gateway = MCPGateway()
    try:
        await gateway.run()
    except KeyboardInterrupt:
        logger.info("Shutting down MCP Gateway")
    except Exception as e:
        logger.error(f"Gateway error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())