"""
MCP Gateway - Bridge between Claude Desktop and HTTP connectors
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import aiohttp
from aiohttp import web
import yaml
import os

logger = logging.getLogger(__name__)


@dataclass
class ConnectorConfig:
    """Configuration for an HTTP connector"""
    name: str
    url: str
    enabled: bool = True
    auth: Optional[Dict[str, str]] = None
    timeout: int = 30


class MCPGateway:
    """Main gateway server that bridges MCP to HTTP connectors"""
    
    def __init__(self, config_path: str = "config/connectors.yaml"):
        self.config_path = config_path
        self.connectors: Dict[str, ConnectorConfig] = {}
        self.session: Optional[aiohttp.ClientSession] = None
        self.app = web.Application()
        self._setup_routes()
        
    def _setup_routes(self):
        """Setup MCP protocol routes"""
        # MCP endpoints
        self.app.router.add_get('/mcp', self.handle_mcp_sse)
        self.app.router.add_post('/mcp/request', self.handle_mcp_request)
        
        # Tool discovery
        self.app.router.add_get('/mcp/tools', self.handle_list_tools)
        self.app.router.add_get('/mcp/resources', self.handle_list_resources)
        self.app.router.add_get('/mcp/prompts', self.handle_list_prompts)
        
        # Health check
        self.app.router.add_get('/health', self.handle_health)
        
    async def load_config(self):
        """Load connector configuration"""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
                
            for conn in config.get('connectors', []):
                connector = ConnectorConfig(**conn)
                if connector.enabled:
                    self.connectors[connector.name] = connector
                    logger.info(f"Loaded connector: {connector.name} -> {connector.url}")
                    
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            
    async def start(self):
        """Start the gateway server"""
        await self.load_config()
        self.session = aiohttp.ClientSession()
        
    async def stop(self):
        """Stop the gateway server"""
        if self.session:
            await self.session.close()
            
    async def _make_connector_request(
        self, 
        connector: ConnectorConfig, 
        method: str, 
        path: str, 
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """Make HTTP request to a connector"""
        url = f"{connector.url.rstrip('/')}/{path.lstrip('/')}"
        
        headers = kwargs.get('headers', {})
        if connector.auth:
            auth_type = connector.auth.get('type', 'bearer')
            if auth_type == 'bearer':
                headers['Authorization'] = f"Bearer {connector.auth['token']}"
                
        try:
            async with self.session.request(
                method, 
                url, 
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=connector.timeout),
                **{k: v for k, v in kwargs.items() if k != 'headers'}
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    logger.error(f"Connector {connector.name} returned {resp.status}")
                    return None
        except Exception as e:
            logger.error(f"Error calling connector {connector.name}: {e}")
            return None
            
    async def handle_mcp_sse(self, request: web.Request) -> web.StreamResponse:
        """Handle MCP SSE connection"""
        response = web.StreamResponse()
        response.headers['Content-Type'] = 'text/event-stream'
        response.headers['Cache-Control'] = 'no-cache'
        response.headers['X-Accel-Buffering'] = 'no'
        
        await response.prepare(request)
        
        # Send initial connection event
        await response.write(b'data: {"type": "connection", "status": "connected"}\n\n')
        
        # Send capabilities
        tools_count = await self._count_all_tools()
        capabilities = {
            "type": "capabilities",
            "tools_count": tools_count,
            "connectors": list(self.connectors.keys())
        }
        await response.write(f'data: {json.dumps(capabilities)}\n\n'.encode())
        
        # Keep connection alive
        try:
            while True:
                await asyncio.sleep(30)
                await response.write(b':keepalive\n\n')
        except Exception:
            pass
            
        return response
        
    async def handle_mcp_request(self, request: web.Request) -> web.Response:
        """Handle MCP request/response protocol"""
        data = await request.json()
        method = data.get('method')
        params = data.get('params', {})
        
        if method == 'tools/list':
            tools = await self._get_all_tools()
            return web.json_response({"tools": tools})
            
        elif method == 'tools/call':
            result = await self._execute_tool(
                params.get('name'),
                params.get('arguments', {})
            )
            return web.json_response(result)
            
        elif method == 'resources/list':
            resources = await self._get_all_resources()
            return web.json_response({"resources": resources})
            
        elif method == 'resources/read':
            result = await self._read_resource(params.get('uri'))
            return web.json_response(result)
            
        elif method == 'prompts/list':
            prompts = await self._get_all_prompts()
            return web.json_response({"prompts": prompts})
            
        elif method == 'prompts/get':
            result = await self._get_prompt(params.get('name'))
            return web.json_response(result)
            
        else:
            return web.json_response(
                {"error": f"Unknown method: {method}"},
                status=400
            )
            
    async def handle_list_tools(self, request: web.Request) -> web.Response:
        """List all tools from all connectors"""
        tools = await self._get_all_tools()
        return web.json_response({"tools": tools})
        
    async def handle_list_resources(self, request: web.Request) -> web.Response:
        """List all resources from all connectors"""
        resources = await self._get_all_resources()
        return web.json_response({"resources": resources})
        
    async def handle_list_prompts(self, request: web.Request) -> web.Response:
        """List all prompts from all connectors"""
        prompts = await self._get_all_prompts()
        return web.json_response({"prompts": prompts})
        
    async def handle_health(self, request: web.Request) -> web.Response:
        """Health check endpoint"""
        connector_status = {}
        
        for name, connector in self.connectors.items():
            info = await self._make_connector_request(connector, 'GET', '/info')
            connector_status[name] = {
                "url": connector.url,
                "healthy": info is not None,
                "info": info
            }
            
        return web.json_response({
            "status": "healthy",
            "connectors": connector_status
        })
        
    async def _count_all_tools(self) -> int:
        """Count tools from all connectors"""
        total = 0
        for connector in self.connectors.values():
            result = await self._make_connector_request(connector, 'GET', '/tools')
            if result:
                total += len(result.get('tools', []))
        return total
        
    async def _get_all_tools(self) -> List[Dict[str, Any]]:
        """Get tools from all connectors"""
        all_tools = []
        
        for connector in self.connectors.values():
            result = await self._make_connector_request(connector, 'GET', '/tools')
            if result:
                tools = result.get('tools', [])
                # Prefix tool names with connector name to avoid conflicts
                for tool in tools:
                    tool['name'] = f"{connector.name}_{tool['name']}"
                    tool['_connector'] = connector.name
                all_tools.extend(tools)
                
        return all_tools
        
    async def _execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool on the appropriate connector"""
        # Extract connector name from tool name
        parts = tool_name.split('_', 1)
        if len(parts) != 2:
            return {"error": f"Invalid tool name: {tool_name}"}
            
        connector_name, actual_tool_name = parts
        connector = self.connectors.get(connector_name)
        
        if not connector:
            return {"error": f"Connector not found: {connector_name}"}
            
        result = await self._make_connector_request(
            connector,
            'POST',
            f'/tools/{actual_tool_name}/execute',
            json={"arguments": arguments}
        )
        
        return result or {"error": "Tool execution failed"}
        
    async def _get_all_resources(self) -> List[Dict[str, Any]]:
        """Get resources from all connectors"""
        all_resources = []
        
        for connector in self.connectors.values():
            result = await self._make_connector_request(connector, 'GET', '/resources')
            if result:
                resources = result.get('resources', [])
                # Prefix URIs with connector name
                for resource in resources:
                    resource['uri'] = f"{connector.name}:{resource['uri']}"
                    resource['_connector'] = connector.name
                all_resources.extend(resources)
                
        return all_resources
        
    async def _read_resource(self, uri: str) -> Dict[str, Any]:
        """Read a resource from the appropriate connector"""
        # Extract connector name from URI
        parts = uri.split(':', 1)
        if len(parts) != 2:
            return {"error": f"Invalid resource URI: {uri}"}
            
        connector_name, actual_uri = parts
        connector = self.connectors.get(connector_name)
        
        if not connector:
            return {"error": f"Connector not found: {connector_name}"}
            
        result = await self._make_connector_request(
            connector,
            'GET',
            f'/resources/{actual_uri}'
        )
        
        return result or {"error": "Resource read failed"}
        
    async def _get_all_prompts(self) -> List[Dict[str, Any]]:
        """Get prompts from all connectors"""
        all_prompts = []
        
        for connector in self.connectors.values():
            result = await self._make_connector_request(connector, 'GET', '/prompts')
            if result:
                prompts = result.get('prompts', [])
                # Prefix prompt names with connector name
                for prompt in prompts:
                    prompt['name'] = f"{connector.name}_{prompt['name']}"
                    prompt['_connector'] = connector.name
                all_prompts.extend(prompts)
                
        return all_prompts
        
    async def _get_prompt(self, prompt_name: str) -> Dict[str, Any]:
        """Get a prompt from the appropriate connector"""
        # Extract connector name from prompt name
        parts = prompt_name.split('_', 1)
        if len(parts) != 2:
            return {"error": f"Invalid prompt name: {prompt_name}"}
            
        connector_name, actual_prompt_name = parts
        connector = self.connectors.get(connector_name)
        
        if not connector:
            return {"error": f"Connector not found: {connector_name}"}
            
        result = await self._make_connector_request(
            connector,
            'GET',
            f'/prompts/{actual_prompt_name}'
        )
        
        return result or {"error": "Prompt not found"}


async def main():
    """Main entry point"""
    logging.basicConfig(level=logging.INFO)
    
    gateway = MCPGateway()
    await gateway.start()
    
    runner = web.AppRunner(gateway.app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 3000)
    await site.start()
    
    logger.info("MCP Gateway running on http://localhost:3000")
    logger.info(f"Loaded {len(gateway.connectors)} connectors")
    
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        pass
    finally:
        await gateway.stop()
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())