"""
MCP Integration for Unified Backend
Adds MCP protocol support over HTTP+SSE to the unified backend
"""

import json
import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from uuid import uuid4

from aiohttp import web
from aiohttp.web import Request, Response

from ..rest_api.services.mcp_service import MCPService
from ..core.config import ConfigManager

logger = logging.getLogger(__name__)


class MCPIntegration:
    """MCP protocol integration for unified backend"""
    
    def __init__(self, unified_server):
        self.server = unified_server
        self.mcp_service: Optional[MCPService] = None
        self.config_manager = ConfigManager()
        self._initialized = False
        
    async def initialize(self):
        """Initialize MCP service"""
        if self._initialized:
            return
            
        logger.info("Initializing MCP integration for unified backend")
        
        # Create and initialize MCP service
        self.mcp_service = MCPService()
        await self.mcp_service.initialize()
        
        self._initialized = True
        logger.info("MCP integration initialized")
        
    def get_routes(self) -> list:
        """Get MCP routes to add to unified backend"""
        return [
            # MCP SSE endpoint
            web.get('/mcp', self.handle_mcp_sse),
            web.get('/mcp/', self.handle_mcp_sse),
            
            # Claude.ai specific endpoints
            web.get('/api/mcp', self.handle_api_mcp),
            web.post('/register', self.handle_register),
            
            # MCP REST endpoints
            web.post('/mcp/request', self.handle_mcp_request),
            web.get('/mcp/tools', self.handle_mcp_tools),
            web.get('/mcp/resources', self.handle_mcp_resources),
            web.get('/mcp/prompts', self.handle_mcp_prompts),
            web.get('/mcp/info', self.handle_mcp_info),
            web.get('/mcp/health', self.handle_mcp_health),
            
            # Auth endpoints
            web.get('/mcp/auth', self.handle_mcp_oauth_initiate),
            web.post('/mcp/auth', self.handle_mcp_auth_validate),
            web.get('/mcp/auth/validate', self.handle_mcp_auth_validate),
            web.post('/mcp/auth/validate', self.handle_mcp_auth_validate),
            web.post('/mcp/auth/callback', self.handle_mcp_oauth_callback),
            web.get('/mcp/auth/callback', self.handle_mcp_oauth_callback),
            
            # WebSocket alternative
            web.get('/mcp/ws', self.handle_mcp_websocket),
        ]
        
    async def handle_mcp_sse(self, request: Request) -> Response:
        """Handle MCP SSE connection"""
        # Get user from session or token
        user_id = await self._get_user_id(request)
        # For development, always allow access
        if not user_id:
            user_id = 'anonymous'
            
        # Check if this is an SSE request
        if request.headers.get("accept") != "text/event-stream":
            return web.json_response({
                "error": "This endpoint requires Server-Sent Events",
                "hint": "Set Accept: text/event-stream header"
            }, status=400)
            
        # Create SSE response
        response = web.StreamResponse()
        response.headers['Content-Type'] = 'text/event-stream'
        response.headers['Cache-Control'] = 'no-cache'
        response.headers['Connection'] = 'keep-alive'
        response.headers['X-Accel-Buffering'] = 'no'
        
        # Add CORS headers for Claude.AI
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, Accept'
        
        await response.prepare(request)
        
        # Stream MCP events
        try:
            async for event in self.mcp_service.handle_sse_connection(user_id):
                await response.write(event.encode('utf-8'))
                await response.drain()
        except Exception as e:
            logger.error(f"SSE error: {e}")
        finally:
            await response.write_eof()
            
        return response
        
    async def handle_mcp_request(self, request: Request) -> Response:
        """Handle single MCP request"""
        user_id = await self._get_user_id(request)
        if not user_id:
            user_id = 'anonymous'
            
        try:
            data = await request.json()
            result = await self.mcp_service.process_mcp_request(data, user_id)
            return web.json_response(result)
        except Exception as e:
            logger.error(f"MCP request error: {e}")
            return web.json_response({
                "jsonrpc": "2.0",
                "id": data.get("id") if "data" in locals() else None,
                "error": {
                    "code": -32603,
                    "message": str(e)
                }
            })
            
    async def handle_mcp_tools(self, request: Request) -> Response:
        """List available tools"""
        user_id = await self._get_user_id(request)
        if not user_id:
            user_id = 'anonymous'
            
        response = await self.mcp_service.handle_list_tools("list_tools")
        tools = response["result"]["tools"]
        
        return web.json_response({
            "tools": tools,
            "total": len(tools)
        })
        
    async def handle_mcp_resources(self, request: Request) -> Response:
        """List available resources"""
        user_id = await self._get_user_id(request)
        if not user_id:
            user_id = 'anonymous'
            
        response = await self.mcp_service.handle_list_resources("list_resources")
        resources = response["result"]["resources"]
        
        return web.json_response({
            "resources": resources,
            "total": len(resources)
        })
        
    async def handle_mcp_prompts(self, request: Request) -> Response:
        """List available prompts"""
        user_id = await self._get_user_id(request)
        if not user_id:
            user_id = 'anonymous'
            
        response = await self.mcp_service.handle_list_prompts("list_prompts")
        prompts = response["result"]["prompts"]
        
        return web.json_response({
            "prompts": prompts,
            "total": len(prompts)
        })
        
    async def handle_mcp_info(self, request: Request) -> Response:
        """Get MCP service information"""
        # Get the host from the request for proper URL construction
        host = request.headers.get('Host', f'localhost:{self.server.port}')
        scheme = 'https' if 'ngrok' in host or request.secure else 'http'
        base_url = f"{scheme}://{host}"
        
        return web.json_response({
            "service": "py-mcp-bridge Unified Backend with MCP",
            "version": "2.6.0",
            "protocol": "MCP 2024-11-05",
            "transport": ["HTTP+SSE", "WebSocket"],
            "capabilities": {
                "tools": True,
                "resources": True,
                "prompts": True,
                "streaming": True
            },
            "authentication": {
                "type": "bearer",
                "required": False,
                "description": "Optional Bearer token for development"
            },
            "connectors": self.mcp_service.connector_registry.list_initialized_connectors() if self.mcp_service else [],
            "endpoints": {
                "sse": f"{base_url}/mcp/",
                "request": f"{base_url}/mcp/request",
                "tools": f"{base_url}/mcp/tools",
                "resources": f"{base_url}/mcp/resources",
                "prompts": f"{base_url}/mcp/prompts",
                "websocket": f"{base_url.replace('http', 'ws')}/mcp/ws"
            }
        })
        
    async def handle_mcp_health(self, request: Request) -> Response:
        """MCP health check"""
        if not self.mcp_service:
            return web.json_response({
                "status": "unhealthy",
                "error": "MCP service not initialized"
            }, status=503)
            
        return web.json_response({
            "status": "healthy",
            "service": "mcp",
            "active_sessions": len(self.mcp_service.active_sessions),
            "connectors": len(self.mcp_service.connector_registry.list_initialized_connectors()),
            "tools": len(self.mcp_service.connector_registry.get_all_tools())
        })
        
    async def handle_mcp_oauth_initiate(self, request: Request) -> Response:
        """Initiate OAuth flow for MCP/Claude.AI"""
        # For development, we'll use a simple flow
        state = request.query.get('state', 'default')
        redirect_uri = request.query.get('redirect_uri', '')
        
        # In production, you would redirect to your OAuth provider
        # For now, we'll simulate a successful auth
        if redirect_uri:
            # Simulate OAuth code
            code = f"dev_code_{uuid.uuid4().hex[:8]}"
            # Redirect back with code
            redirect_url = f"{redirect_uri}?code={code}&state={state}"
            return web.HTTPFound(redirect_url)
        else:
            # Return a simple auth page
            html = """
            <html>
            <head><title>MCP Bridge Authentication</title></head>
            <body style="font-family: Arial; padding: 40px; text-align: center;">
                <h2>MCP Bridge Authentication</h2>
                <p>This is a development authentication endpoint.</p>
                <p>In production, this would redirect to your OAuth provider.</p>
                <form method="get">
                    <input type="hidden" name="state" value="{state}">
                    <button type="submit" name="action" value="approve" 
                            style="padding: 10px 20px; font-size: 16px; background: #4CAF50; color: white; border: none; cursor: pointer;">
                        Approve Access
                    </button>
                </form>
            </body>
            </html>
            """.format(state=state)
            return web.Response(text=html, content_type='text/html')
    
    async def handle_mcp_auth_validate(self, request: Request) -> Response:
        """Validate auth token for Claude.ai"""
        # Get auth header or token from request
        auth_header = request.headers.get('Authorization', '')
        
        # Also check request body for token
        token = None
        if request.method == 'POST':
            try:
                data = await request.json()
                token = data.get('token') or data.get('api_key') or data.get('apiKey')
            except:
                pass
        
        # Extract token from Bearer header
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
        
        # In development, accept any token
        if token or self.server.base_url:  # Always return success in dev
            return web.json_response({
                "valid": True,
                "user_id": "dev-user",
                "permissions": ["read", "write", "execute"],
                "endpoints": {
                    "base": f"{request.scheme}://{request.host}/mcp",
                    "sse": f"{request.scheme}://{request.host}/mcp/",
                    "request": f"{request.scheme}://{request.host}/mcp/request"
                }
            })
        else:
            return web.json_response({
                "valid": False,
                "error": "No token provided"
            }, status=401)
    
    async def handle_mcp_oauth_callback(self, request: Request) -> Response:
        """Handle OAuth callback for MCP/Claude.AI"""
        try:
            data = await request.json()
            code = data.get('code')
            state = data.get('state')
            
            # Store in unified backend's OAuth callbacks
            callback_id = f"mcp_{state}"
            self.server.oauth_callbacks[callback_id] = {
                'service': 'claude_ai',
                'code': code,
                'state': state,
                'timestamp': datetime.now().isoformat()
            }
            
            # TODO: Exchange code for token with Claude.AI
            
            return web.json_response({
                "status": "success",
                "message": "OAuth callback processed",
                "callback_id": callback_id
            })
            
        except Exception as e:
            logger.error(f"OAuth callback error: {e}")
            return web.json_response({
                "error": "OAuth callback failed",
                "message": str(e)
            }, status=400)
            
    async def handle_mcp_websocket(self, request: Request) -> web.WebSocketResponse:
        """WebSocket endpoint for MCP (alternative to SSE)"""
        user_id = await self._get_user_id(request)
        if not user_id:
            user_id = 'anonymous'
            
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        session_id = f"mcp_ws_{user_id}_{datetime.now().isoformat()}"
        logger.info(f"New MCP WebSocket connection: {session_id}")
        
        try:
            # Send connection message
            await ws.send_json({
                "type": "connection",
                "status": "connected",
                "session_id": session_id
            })
            
            # Handle messages
            async for msg in ws:
                if msg.type == web.WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    
                    # Process MCP request
                    response = await self.mcp_service.process_mcp_request(data, user_id)
                    
                    # Send response
                    await ws.send_json(response)
                    
                elif msg.type == web.WSMsgType.ERROR:
                    logger.error(f'WebSocket error: {ws.exception()}')
                    
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            logger.info(f"WebSocket closed: {session_id}")
            
        return ws
        
    async def _get_user_id(self, request: Request) -> Optional[str]:
        """Get user ID from request (token, session, or default for dev)"""
        # Check Authorization header
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
            
            # In development, accept test tokens
            if token == 'dev-token':
                return 'dev-user'
                
            # TODO: Validate JWT token and extract user ID
            # For now, use token as user ID
            return f"user_{token[:8]}"
            
        # Check session
        # TODO: Implement session management
        
        # In development mode, allow unauthenticated access
        # Always allow anonymous access for now since we're in development
        return 'anonymous'
        
    async def handle_api_mcp(self, request: Request) -> Response:
        """Handle /api/mcp endpoint for Claude.ai discovery"""
        host = request.headers.get('Host', f'localhost:{self.server.port}')
        scheme = 'https' if 'ngrok' in host or request.secure else 'http'
        base_url = f"{scheme}://{host}"
        
        return web.json_response({
            "version": "1.0",
            "protocol": "mcp",
            "endpoints": {
                "mcp": f"{base_url}/mcp",
                "tools": f"{base_url}/mcp/tools",
                "authorize": f"{base_url}/oauth/authorize",
                "token": f"{base_url}/oauth/token"
            },
            "capabilities": {
                "tools": True,
                "resources": True,
                "prompts": True,
                "oauth": True
            }
        })
        
    async def handle_register(self, request: Request) -> Response:
        """Handle /register endpoint for Claude.ai registration"""
        try:
            data = await request.json()
            
            # Log registration attempt
            logger.info(f"Registration request from Claude.ai: {data}")
            
            # Return success with client credentials
            return web.json_response({
                "client_id": f"claude-{uuid4().hex[:8]}",
                "client_secret": "not-required-in-dev",
                "redirect_uris": [
                    "https://claude.ai/oauth/callback",
                    "https://claude.ai/integrations/callback"
                ],
                "grant_types": ["authorization_code"],
                "response_types": ["code"],
                "scope": "read write execute"
            })
        except Exception as e:
            logger.error(f"Registration error: {e}")
            return web.json_response({
                "error": "registration_failed",
                "error_description": str(e)
            }, status=400)
    
    async def shutdown(self):
        """Shutdown MCP integration"""
        if self.mcp_service:
            await self.mcp_service.shutdown()