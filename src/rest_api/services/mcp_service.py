"""
MCP Service for Claude.AI Web Integration
Handles Server-Sent Events (SSE) connections and MCP protocol
"""

import json
import asyncio
import logging
from typing import AsyncGenerator, Dict, Any, Optional
from uuid import uuid4
from datetime import datetime

from ...core.registry import ConnectorRegistry
from ...core.config import ConfigManager
from ...core.models import ToolResult
from ...version import MCP_BRIDGE_VERSION

logger = logging.getLogger(__name__)


class MCPService:
    """Service to handle MCP protocol over HTTP+SSE for Claude.AI"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_manager = ConfigManager(config_path)
        self.connector_registry = ConnectorRegistry()
        self.active_sessions: Dict[str, asyncio.Queue] = {}
        self._initialized = False
        
    async def initialize(self):
        """Initialize the MCP service and connectors"""
        if self._initialized:
            return
            
        logger.info("Initializing MCP Service for Claude.AI")
        
        # Auto-discover and initialize connectors
        self.connector_registry.auto_discover_connectors()
        
        # Initialize enabled connectors
        for connector_config in self.config_manager.get_enabled_connectors():
            try:
                logger.info(f"Initializing connector: {connector_config.name}")
                await self.connector_registry.initialize_connector(
                    connector_config.name, connector_config.config
                )
            except Exception as e:
                logger.error(f"Failed to initialize connector {connector_config.name}: {e}")
                
        self._initialized = True
        logger.info(f"MCP Service initialized with {len(self.connector_registry.list_initialized_connectors())} connectors")
        
    async def handle_sse_connection(self, user_id: str) -> AsyncGenerator[str, None]:
        """Handle Server-Sent Events connection for MCP protocol"""
        session_id = f"mcp_{user_id}_{uuid4()}"
        logger.info(f"New SSE connection: {session_id}")
        
        try:
            # Send initial connection event
            yield self._format_sse_event({
                'type': 'connection',
                'status': 'connected',
                'session_id': session_id,
                'timestamp': datetime.now().isoformat()
            })
            
            # Create message queue for this session
            message_queue = asyncio.Queue()
            self.active_sessions[session_id] = message_queue
            
            # Send initial capabilities
            yield self._format_sse_event({
                'type': 'capabilities',
                'tools_count': len(self.connector_registry.get_all_tools()),
                'connectors': self.connector_registry.list_initialized_connectors()
            })
            
            # Listen for incoming messages
            while True:
                try:
                    # Wait for message with timeout for heartbeat
                    message = await asyncio.wait_for(
                        message_queue.get(), 
                        timeout=30.0
                    )
                    
                    if message.get('type') == 'close':
                        logger.info(f"Closing session: {session_id}")
                        break
                        
                    # Process MCP request
                    response = await self.process_mcp_request(message, user_id)
                    
                    # Send response via SSE
                    yield self._format_sse_event(response)
                    
                except asyncio.TimeoutError:
                    # Send heartbeat to keep connection alive
                    yield self._format_sse_event({
                        'type': 'heartbeat',
                        'timestamp': datetime.now().isoformat()
                    })
                    
        except Exception as e:
            logger.error(f"Error in SSE connection {session_id}: {e}")
            yield self._format_sse_event({
                'type': 'error',
                'message': str(e)
            })
            
        finally:
            # Cleanup session
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
            logger.info(f"Session closed: {session_id}")
            
    def _format_sse_event(self, data: dict) -> str:
        """Format data as SSE event"""
        return f"data: {json.dumps(data)}\n\n"
        
    async def process_mcp_request(self, request: dict, user_id: str) -> dict:
        """Process MCP JSON-RPC request"""
        try:
            method = request.get('method')
            params = request.get('params', {})
            request_id = request.get('id')
            
            logger.debug(f"Processing MCP request: {method}")
            
            if method == 'initialize':
                return await self.handle_initialize(request_id)
            elif method == 'tools/list':
                return await self.handle_list_tools(request_id)
            elif method == 'tools/call':
                return await self.handle_tool_call(request_id, params, user_id)
            elif method == 'resources/list':
                return await self.handle_list_resources(request_id)
            elif method == 'resources/read':
                return await self.handle_read_resource(request_id, params)
            elif method == 'prompts/list':
                return await self.handle_list_prompts(request_id)
            elif method == 'prompts/get':
                return await self.handle_get_prompt(request_id, params)
            else:
                return self._error_response(
                    request_id, 
                    -32601, 
                    f"Method not found: {method}"
                )
                
        except Exception as e:
            logger.error(f"Error processing MCP request: {e}")
            return self._error_response(
                request.get('id'),
                -32603,
                f"Internal error: {str(e)}"
            )
            
    async def handle_initialize(self, request_id: str) -> dict:
        """Handle MCP initialize request"""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {},
                    "resources": {},
                    "prompts": {}
                },
                "serverInfo": {
                    "name": self.config_manager.get_server_config().name,
                    "version": str(MCP_BRIDGE_VERSION),
                    "description": "py-mcp-bridge for Claude.AI web integration"
                }
            }
        }
        
    async def handle_list_tools(self, request_id: str) -> dict:
        """Handle tools/list request"""
        tools = self.connector_registry.get_all_tools()
        
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "tools": [
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "inputSchema": tool.input_schema
                    }
                    for tool in tools
                ]
            }
        }
        
    async def handle_tool_call(self, request_id: str, params: dict, user_id: str) -> dict:
        """Execute tool call through connector registry"""
        tool_name = params.get('name')
        arguments = params.get('arguments', {})
        
        if not tool_name:
            return self._error_response(request_id, -32602, "Tool name is required")
            
        try:
            # Execute tool through registry
            result = await self.connector_registry.execute_tool(tool_name, arguments)
            
            # Convert result to MCP format
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [
                        content.model_dump(exclude_none=True) 
                        for content in result.content
                    ]
                }
            }
            
        except ValueError as e:
            return self._error_response(request_id, -32602, str(e))
        except Exception as e:
            logger.error(f"Tool execution error: {e}")
            return self._error_response(
                request_id, 
                -32603, 
                f"Tool execution failed: {str(e)}"
            )
            
    async def handle_list_resources(self, request_id: str) -> dict:
        """Handle resources/list request"""
        resources = []
        
        for connector in self.connector_registry.get_all_connectors():
            if connector.initialized:
                connector_resources = connector.get_resources()
                for resource_def in connector_resources:
                    resources.append({
                        "uri": resource_def.uri,
                        "name": resource_def.name,
                        "description": resource_def.description,
                        "mimeType": resource_def.mimeType
                    })
                    
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {"resources": resources}
        }
        
    async def handle_read_resource(self, request_id: str, params: dict) -> dict:
        """Handle resources/read request"""
        uri = params.get('uri')
        
        if not uri:
            return self._error_response(request_id, -32602, "Resource URI is required")
            
        try:
            # Find connector that has this resource
            for connector in self.connector_registry.get_all_connectors():
                if connector.initialized and connector.validate_resource_exists(uri):
                    resource_result = await connector.read_resource(uri)
                    
                    # Format content
                    if resource_result.content.type.value == "json":
                        content_str = json.dumps(resource_result.content.data, indent=2)
                    else:
                        content_str = str(resource_result.content.data)
                        
                    return {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {
                            "contents": [{
                                "uri": uri,
                                "mimeType": resource_result.content.mimeType or "text/plain",
                                "text": content_str
                            }]
                        }
                    }
                    
            return self._error_response(request_id, -32602, f"Resource not found: {uri}")
            
        except Exception as e:
            logger.error(f"Error reading resource {uri}: {e}")
            return self._error_response(
                request_id, 
                -32603, 
                f"Failed to read resource: {str(e)}"
            )
            
    async def handle_list_prompts(self, request_id: str) -> dict:
        """Handle prompts/list request"""
        prompts = []
        
        for connector in self.connector_registry.get_all_connectors():
            if connector.initialized:
                connector_prompts = connector.get_prompts()
                for prompt_def in connector_prompts:
                    prompts.append({
                        "name": prompt_def.name,
                        "description": prompt_def.description,
                        "arguments": [
                            {
                                "name": arg.name,
                                "description": arg.description,
                                "required": arg.required,
                                "type": arg.type
                            }
                            for arg in prompt_def.arguments
                        ]
                    })
                    
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {"prompts": prompts}
        }
        
    async def handle_get_prompt(self, request_id: str, params: dict) -> dict:
        """Handle prompts/get request"""
        prompt_name = params.get('name')
        arguments = params.get('arguments', {})
        
        if not prompt_name:
            return self._error_response(request_id, -32602, "Prompt name is required")
            
        try:
            # Find connector that has this prompt
            for connector in self.connector_registry.get_all_connectors():
                if connector.initialized:
                    connector_prompts = connector.get_prompts()
                    for prompt_def in connector_prompts:
                        if prompt_def.name == prompt_name:
                            result = await connector.execute_prompt(prompt_name, arguments)
                            
                            return {
                                "jsonrpc": "2.0",
                                "id": request_id,
                                "result": {
                                    "description": f"Result from prompt: {prompt_name}",
                                    "messages": [
                                        {
                                            "role": "assistant",
                                            "content": {
                                                "type": "text",
                                                "text": result.content
                                            }
                                        }
                                    ]
                                }
                            }
                            
            return self._error_response(request_id, -32602, f"Prompt not found: {prompt_name}")
            
        except Exception as e:
            logger.error(f"Prompt execution error: {e}")
            return self._error_response(
                request_id, 
                -32603, 
                f"Prompt execution failed: {str(e)}"
            )
            
    def _error_response(self, request_id: Any, code: int, message: str) -> dict:
        """Create JSON-RPC error response"""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": code,
                "message": message
            }
        }
        
    async def send_message_to_session(self, session_id: str, message: dict):
        """Send a message to a specific session"""
        if session_id in self.active_sessions:
            await self.active_sessions[session_id].put(message)
            
    async def broadcast_to_all_sessions(self, message: dict):
        """Broadcast a message to all active sessions"""
        for session_id, queue in self.active_sessions.items():
            try:
                await queue.put(message)
            except Exception as e:
                logger.error(f"Failed to send to session {session_id}: {e}")
                
    async def shutdown(self):
        """Shutdown the MCP service"""
        logger.info("Shutting down MCP service")
        
        # Close all sessions
        close_message = {'type': 'close'}
        await self.broadcast_to_all_sessions(close_message)
        
        # Shutdown registry
        await self.connector_registry.shutdown_all()