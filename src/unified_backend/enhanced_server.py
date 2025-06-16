"""
Enhanced Unified Backend Server with MCP Integration
Consolidates OAuth, Chrome extension API, MCP protocol, and other HTTP services
"""

import asyncio
import socket
import logging
import json
import time
import ssl
import os
from datetime import datetime
from typing import Dict, Any, Optional, List, Callable
from urllib.parse import urlparse, parse_qs
import uuid

from aiohttp import web
from aiohttp.web import Request, Response, json_response
import aiohttp_cors
from motor.motor_asyncio import AsyncIOMotorClient

# Import MCP integration
from .mcp_integration import MCPIntegration
from .oauth_wellknown import OAuthWellKnownHandler
from .oauth_simple import SimpleOAuthHandler

# Import event system components
try:
    from ..core.events import EventSystemManager
    event_system_available = True
except ImportError:
    event_system_available = False
    EventSystemManager = None

logger = logging.getLogger(__name__)


class EnhancedUnifiedServer:
    """
    Enhanced unified server that handles:
    - OAuth callbacks for all services
    - Chrome extension API endpoints
    - MCP protocol for Claude.AI (NEW)
    - WebSocket connections
    - Health checks and debugging
    - Event system integration
    """
    
    def __init__(
        self, 
        port_range: tuple = (3000, 3003),
        enable_events: bool = True,
        enable_mcp: bool = True,
        enable_https: bool = False,
        mongo_uri: str = "mongodb://localhost:27017"
    ):
        self.port_range = port_range
        self.port = None
        self.app = None
        self.runner = None
        self.site = None
        self.base_url = None
        self.enable_https = enable_https
        
        # SSL configuration
        self.ssl_context = None
        if enable_https:
            self.ssl_context = self._create_ssl_context()
        
        # Store for OAuth callbacks waiting to be processed
        self.oauth_callbacks: Dict[str, Dict[str, Any]] = {}
        
        # Store for WebSocket connections
        self.websockets: List[web.WebSocketResponse] = []
        
        # Store for debugging
        self.request_log: List[Dict[str, Any]] = []
        self.max_log_size = 100
        
        # Plugin management
        self.registered_plugins: Dict[str, Dict[str, Any]] = {}
        self.plugin_connections: Dict[str, web.WebSocketResponse] = {}
        
        # OAuth handlers by service
        self.oauth_handlers: Dict[str, Callable] = {}
        
        # Event system integration
        self.enable_events = enable_events and event_system_available
        self.mongo_uri = mongo_uri
        self.event_system: Optional[EventSystemManager] = None
        self.mongo_client: Optional[AsyncIOMotorClient] = None
        
        # MCP integration
        self.enable_mcp = enable_mcp
        self.mcp_integration: Optional[MCPIntegration] = None
        if enable_mcp:
            self.mcp_integration = MCPIntegration(self)
            
        # OAuth handlers
        self.oauth_wellknown = OAuthWellKnownHandler(self)
        self.oauth_simple = SimpleOAuthHandler(self)
    
    def _create_ssl_context(self) -> Optional[ssl.SSLContext]:
        """Create SSL context for HTTPS"""
        cert_file = os.getenv('SSL_CERT_FILE')
        key_file = os.getenv('SSL_KEY_FILE')
        
        if not (cert_file and key_file):
            logger.warning("SSL certificates not configured")
            return None
            
        try:
            context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            context.load_cert_chain(cert_file, key_file)
            return context
        except Exception as e:
            logger.error(f"Failed to create SSL context: {e}")
            return None
    
    def find_available_port(self) -> Optional[int]:
        """Find an available port in the specified range"""
        for port in range(self.port_range[0], self.port_range[1] + 1):
            try:
                # Try to bind to the port
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.bind(('', port))
                sock.close()
                return port
            except OSError:
                continue
        return None
    
    def log_request(self, request: Request, response_data: Any = None):
        """Log request for debugging"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'method': request.method,
            'path': request.path,
            'headers': dict(request.headers),
            'query': dict(request.query),
            'response': response_data
        }
        
        self.request_log.append(log_entry)
        
        # Keep log size limited
        if len(self.request_log) > self.max_log_size:
            self.request_log = self.request_log[-self.max_log_size:]
    
    async def create_app(self) -> web.Application:
        """Create the aiohttp application with all routes"""
        self.app = web.Application()
        
        # Set up CORS - use wildcard for dev, but no credentials with wildcard
        default_cors = aiohttp_cors.ResourceOptions(
            allow_credentials=False,  # Can't use credentials with wildcard
            expose_headers="*",
            allow_headers="*",
            allow_methods="*"
        )
        
        # Add specific origins that need credentials
        cors_origins = {
            "*": default_cors,
            "https://claude.ai": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
                allow_methods="*"
            ),
            "https://www.claude.ai": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
                allow_methods="*"
            ),
            "https://console.anthropic.com": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
                allow_methods="*"
            ),
            "http://localhost:3000": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
                allow_methods="*"
            )
        }
        
        cors = aiohttp_cors.setup(self.app, defaults=cors_origins)
        
        # Base routes
        routes = [
            # Health and info
            web.get('/', self.handle_root),
            web.get('/health', self.handle_health),
            web.get('/debug', self.handle_debug),
            
            # OAuth callbacks
            web.get('/oauth/callback', self.handle_oauth_callback),
            web.post('/oauth/callback', self.handle_oauth_callback),
            web.get('/oauth/{service}/callback', self.handle_service_oauth_callback),
            web.post('/oauth/{service}/callback', self.handle_service_oauth_callback),
            
            # Chrome extension API
            web.post('/api/extension/ping', self.handle_extension_ping),
            web.post('/api/extension/page-context', self.handle_page_context),
            web.post('/api/extension/request', self.handle_extension_request),
            
            # WebSocket
            web.get('/ws', self.handle_websocket),
            web.get('/ws/extension', self.handle_websocket),
            
            # Original MCP Bridge integration
            web.post('/api/mcp/tool', self.handle_mcp_tool_request),
            web.get('/api/mcp/status', self.handle_mcp_status),
            
            # Plugin management endpoints
            web.post('/api/plugins/register', self.handle_plugin_register),
            web.get('/api/plugins', self.handle_plugin_list),
            web.post('/api/plugins/{plugin_id}/execute', self.handle_plugin_execute),
            web.get('/api/plugins/{plugin_id}/status', self.handle_plugin_status),
            web.delete('/api/plugins/{plugin_id}', self.handle_plugin_unregister),
            
            # Plugin WebSocket endpoint
            web.get('/ws/plugin/{plugin_id}', self.handle_plugin_websocket),
        ]
        
        # Add OAuth routes (always enabled for MCP)
        routes.extend(self.oauth_wellknown.get_routes())
        routes.extend(self.oauth_simple.get_routes())
        
        # Add MCP routes if enabled
        if self.enable_mcp and self.mcp_integration:
            mcp_routes = self.mcp_integration.get_routes()
            routes.extend(mcp_routes)
        
        # Add event system routes if enabled
        if self.enable_events:
            event_routes = [
                # Event API
                web.post('/api/events', self.handle_publish_event),
                web.get('/api/events/stats', self.handle_event_stats),
                web.get('/api/events/recent', self.handle_recent_events),
                
                # Task API
                web.post('/api/tasks', self.handle_queue_task),
                web.get('/api/tasks/{task_id}', self.handle_task_status),
                
                # Event WebSocket
                web.get('/ws/events', self.handle_event_websocket),
            ]
            routes.extend(event_routes)
        
        # Add all routes with CORS
        for route in routes:
            cors.add(self.app.router.add_route(route.method, route.path, route.handler))
        
        # Initialize subsystems on startup
        self.app.on_startup.append(self._init_subsystems)
        self.app.on_cleanup.append(self._cleanup_subsystems)
        
        return self.app
    
    async def _init_subsystems(self, app):
        """Initialize all subsystems"""
        # Initialize event system if enabled
        if self.enable_events:
            await self._init_event_system(app)
        
        # Initialize MCP integration if enabled
        if self.enable_mcp and self.mcp_integration:
            await self.mcp_integration.initialize()
    
    async def _cleanup_subsystems(self, app):
        """Cleanup all subsystems"""
        # Cleanup event system
        if self.enable_events:
            await self._cleanup_event_system(app)
        
        # Cleanup MCP integration
        if self.enable_mcp and self.mcp_integration:
            await self.mcp_integration.shutdown()
    
    # Root and health endpoints
    async def handle_root(self, request: Request) -> Response:
        """Root endpoint with service information"""
        self.log_request(request)
        
        protocol = "https" if self.enable_https else "http"
        
        data = {
            'service': 'MCP Bridge Enhanced Unified Backend',
            'version': '2.0.0',
            'port': self.port,
            'protocol': protocol,
            'endpoints': {
                'health': f'{self.base_url}/health',
                'debug': f'{self.base_url}/debug',
                'oauth_callback': f'{self.base_url}/oauth/callback',
                'extension_api': f'{self.base_url}/api/extension/',
                'plugin_api': f'{self.base_url}/api/plugins/',
                'websocket': f'ws{"s" if self.enable_https else ""}://localhost:{self.port}/ws'
            },
            'features': {
                'oauth': True,
                'chrome_extension': True,
                'plugins': True,
                'websocket': True,
                'events': self.enable_events,
                'mcp': self.enable_mcp,
                'https': self.enable_https
            },
            'timestamp': datetime.now().isoformat()
        }
        
        # Add MCP endpoints if enabled
        if self.enable_mcp:
            data['endpoints']['mcp'] = {
                'sse': f'{self.base_url}/mcp/',
                'request': f'{self.base_url}/mcp/request',
                'tools': f'{self.base_url}/mcp/tools',
                'info': f'{self.base_url}/mcp/info'
            }
        
        # Add event system endpoints if enabled
        if self.enable_events:
            data['endpoints']['event_api'] = f'{self.base_url}/api/events/'
            data['endpoints']['task_api'] = f'{self.base_url}/api/tasks/'
            data['endpoints']['event_websocket'] = f'ws{"s" if self.enable_https else ""}://localhost:{self.port}/ws/events'
            data['event_system'] = {
                'enabled': True,
                'status': 'active' if self.event_system else 'initializing'
            }
        
        return json_response(data)
    
    async def handle_health(self, request: Request) -> Response:
        """Health check endpoint"""
        health_data = {
            'status': 'healthy',
            'port': self.port,
            'protocol': 'https' if self.enable_https else 'http',
            'active_websockets': len(self.websockets),
            'pending_oauth': len(self.oauth_callbacks),
            'registered_plugins': len(self.registered_plugins),
            'connected_plugins': sum(1 for ws in self.plugin_connections.values() if not ws.closed),
            'features': {
                'mcp': self.enable_mcp and self.mcp_integration is not None,
                'events': self.enable_events and self.event_system is not None,
                'https': self.enable_https and self.ssl_context is not None
            },
            'timestamp': datetime.now().isoformat()
        }
        
        # Add MCP health if enabled
        if self.enable_mcp and self.mcp_integration and self.mcp_integration.mcp_service:
            health_data['mcp'] = {
                'active_sessions': len(self.mcp_integration.mcp_service.active_sessions),
                'connectors': len(self.mcp_integration.mcp_service.connector_registry.list_initialized_connectors()),
                'tools': len(self.mcp_integration.mcp_service.connector_registry.get_all_tools())
            }
        
        return json_response(health_data)
    
    async def handle_debug(self, request: Request) -> Response:
        """Debug information endpoint"""
        return json_response({
            'port': self.port,
            'active_websockets': len(self.websockets),
            'pending_oauth_callbacks': list(self.oauth_callbacks.keys()),
            'registered_plugins': list(self.registered_plugins.keys()),
            'connected_plugins': [pid for pid, ws in self.plugin_connections.items() if not ws.closed],
            'recent_requests': self.request_log[-20:],
            'timestamp': datetime.now().isoformat()
        })
    
    async def _broadcast_websocket(self, data: Dict[str, Any]):
        """Broadcast data to all connected WebSocket clients"""
        if self.websockets:
            await asyncio.gather(
                *[ws.send_json(data) for ws in self.websockets if not ws.closed],
                return_exceptions=True
            )
    
    async def handle_oauth_callback(self, request: Request) -> Response:
        """Generic OAuth callback handler"""
        self.log_request(request)
        
        # Extract OAuth parameters
        code = request.query.get('code')
        state = request.query.get('state')
        error = request.query.get('error')
        
        # Determine service from state or referrer
        service = self._determine_oauth_service(request)
        
        # Store callback data
        callback_id = str(uuid.uuid4())
        self.oauth_callbacks[callback_id] = {
            'service': service,
            'code': code,
            'state': state,
            'error': error,
            'timestamp': datetime.now().isoformat(),
            'query': dict(request.query)
        }
        
        # Notify via WebSocket if any clients connected
        await self._broadcast_websocket({
            'type': 'oauth_callback',
            'callback_id': callback_id,
            'service': service,
            'success': code is not None
        })
        
        # Return user-friendly HTML response
        if error:
            html = f"""
            <html>
            <head><title>Authorization Failed</title></head>
            <body style="font-family: Arial; padding: 40px; text-align: center;">
                <h2>❌ Authorization Failed</h2>
                <p>Error: {error}</p>
                <p>You can close this window and try again.</p>
            </body>
            </html>
            """
        else:
            html = f"""
            <html>
            <head><title>Authorization Successful</title></head>
            <body style="font-family: Arial; padding: 40px; text-align: center;">
                <h2>✅ Authorization Successful!</h2>
                <p>You can now close this window and return to the application.</p>
                <script>
                    // Auto-close after 3 seconds
                    setTimeout(() => window.close(), 3000);
                </script>
            </body>
            </html>
            """
        
        return Response(text=html, content_type='text/html')
    
    def _determine_oauth_service(self, request: Request) -> str:
        """Determine which service the OAuth callback is for"""
        # Check state parameter
        state = request.query.get('state', '')
        if 'gmail' in state.lower():
            return 'gmail'
        elif 'gcal' in state.lower() or 'calendar' in state.lower():
            return 'gcal'
        elif 'github' in state.lower():
            return 'github'
        elif 'slack' in state.lower():
            return 'slack'
        elif 'claude' in state.lower():
            return 'claude_ai'
        
        # Check referrer
        referrer = request.headers.get('Referer', '')
        if 'google' in referrer:
            return 'google'
        elif 'github' in referrer:
            return 'github'
        elif 'slack' in referrer:
            return 'slack'
        elif 'claude.ai' in referrer:
            return 'claude_ai'
        
        return 'unknown'
    
    async def handle_service_oauth_callback(self, request: Request) -> Response:
        """Service-specific OAuth callback handler"""
        service = request.match_info.get('service', 'unknown')
        
        # If we have a registered handler for this service, use it
        if service in self.oauth_handlers:
            return await self.oauth_handlers[service](request)
        
        # Otherwise, use generic handler
        return await self.handle_oauth_callback(request)
    
    # Chrome Extension API endpoints
    async def handle_extension_ping(self, request: Request) -> Response:
        """Extension connectivity test"""
        self.log_request(request)
        
        data = await request.json()
        extension_id = data.get('extensionId')
        capabilities = data.get('capabilities', [])
        
        # Register extension if it has capabilities
        if extension_id and capabilities:
            self.registered_plugins[f"extension_{extension_id}"] = {
                'id': extension_id,
                'name': 'Chrome Extension',
                'type': 'chrome_extension',
                'capabilities': capabilities,
                'registered_at': datetime.now().isoformat(),
                'status': 'active'
            }
            
            # Broadcast extension activation
            await self._broadcast_websocket({
                'type': 'extension_activated',
                'extension_id': extension_id,
                'capabilities': capabilities
            })
        
        return json_response({
            'status': 'ok',
            'message': 'Unified backend is running',
            'port': self.port,
            'extension_registered': bool(extension_id),
            'timestamp': int(time.time())
        })
    
    async def handle_page_context(self, request: Request) -> Response:
        """Receive page context from extension"""
        data = await request.json()
        self.log_request(request, data)
        
        # Broadcast to WebSocket clients
        await self._broadcast_websocket({
            'type': 'page_context',
            'data': data,
            'timestamp': datetime.now().isoformat()
        })
        
        return json_response({
            'success': True,
            'data': {
                'message': f"Received context for {data.get('title', 'unknown')}",
                'url': data.get('url'),
                'timestamp': data.get('timestamp')
            }
        })
    
    async def handle_extension_request(self, request: Request) -> Response:
        """Handle generic extension requests"""
        data = await request.json()
        self.log_request(request, data)
        
        action = data.get('action')
        
        # Route to appropriate handler
        if action == 'get_oauth_status':
            return json_response({
                'success': True,
                'data': {
                    'pending_callbacks': len(self.oauth_callbacks),
                    'services': list(self.oauth_callbacks.keys())
                }
            })
        
        # Default response
        return json_response({
            'success': True,
            'data': {
                'action': action,
                'echo': data.get('data', {}),
                'processed': True
            }
        })
    
    # WebSocket endpoint
    async def handle_websocket(self, request: Request) -> web.WebSocketResponse:
        """WebSocket connection handler"""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        self.websockets.append(ws)
        logger.info(f"WebSocket connected. Total: {len(self.websockets)}")
        
        # Send welcome message
        await ws.send_json({
            'type': 'connected',
            'message': 'Connected to Unified Backend',
            'port': self.port,
            'timestamp': datetime.now().isoformat()
        })
        
        try:
            async for msg in ws:
                if msg.type == web.WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    logger.info(f"WebSocket received: {data.get('type', 'unknown')}")
                    
                    # Echo back with processing info
                    await ws.send_json({
                        'type': 'response',
                        'original': data,
                        'processed': True,
                        'timestamp': datetime.now().isoformat()
                    })
                    
                elif msg.type == web.WSMsgType.ERROR:
                    logger.error(f'WebSocket error: {ws.exception()}')
                    
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            self.websockets.remove(ws)
            logger.info(f"WebSocket disconnected. Total: {len(self.websockets)}")
            
        return ws
    
    # Plugin management endpoints
    async def handle_plugin_register(self, request: Request) -> Response:
        """Register a new plugin"""
        self.log_request(request)
        
        try:
            data = await request.json()
            plugin_id = data.get('id')
            
            if not plugin_id:
                return json_response({'error': 'Plugin ID required'}, status=400)
            
            # Store plugin registration
            self.registered_plugins[plugin_id] = {
                'id': plugin_id,
                'name': data.get('name', plugin_id),
                'type': data.get('type', 'unknown'),
                'version': data.get('version', '1.0.0'),
                'capabilities': data.get('capabilities', []),
                'registered_at': datetime.now().isoformat(),
                'status': 'active'
            }
            
            logger.info(f"Plugin registered: {plugin_id}")
            
            # Broadcast plugin registration
            await self._broadcast_websocket({
                'type': 'plugin_registered',
                'plugin': self.registered_plugins[plugin_id]
            })
            
            return json_response({
                'success': True,
                'plugin_id': plugin_id,
                'message': f'Plugin {plugin_id} registered successfully'
            })
            
        except Exception as e:
            logger.error(f"Plugin registration error: {e}")
            return json_response({'error': str(e)}, status=500)
    
    async def handle_plugin_list(self, request: Request) -> Response:
        """List all registered plugins"""
        return json_response({
            'plugins': list(self.registered_plugins.values()),
            'count': len(self.registered_plugins)
        })
    
    async def handle_plugin_execute(self, request: Request) -> Response:
        """Execute a plugin action"""
        plugin_id = request.match_info['plugin_id']
        
        if plugin_id not in self.registered_plugins:
            return json_response({'error': 'Plugin not found'}, status=404)
        
        try:
            data = await request.json()
            action = data.get('action')
            params = data.get('params', {})
            
            # Check if plugin has WebSocket connection
            plugin_ws = self.plugin_connections.get(plugin_id)
            if plugin_ws and not plugin_ws.closed:
                # Forward to plugin via WebSocket
                await plugin_ws.send_json({
                    'type': 'execute_action',
                    'action': action,
                    'params': params,
                    'request_id': str(uuid.uuid4())
                })
                
                return json_response({
                    'success': True,
                    'message': 'Action sent to plugin',
                    'async': True
                })
            else:
                # Plugin not connected, queue for later or return error
                return json_response({
                    'error': 'Plugin not connected',
                    'plugin_id': plugin_id
                }, status=503)
                
        except Exception as e:
            logger.error(f"Plugin execution error: {e}")
            return json_response({'error': str(e)}, status=500)
    
    async def handle_plugin_status(self, request: Request) -> Response:
        """Get plugin status"""
        plugin_id = request.match_info['plugin_id']
        
        if plugin_id not in self.registered_plugins:
            return json_response({'error': 'Plugin not found'}, status=404)
        
        plugin = self.registered_plugins[plugin_id]
        plugin['connected'] = plugin_id in self.plugin_connections and not self.plugin_connections[plugin_id].closed
        
        return json_response(plugin)
    
    async def handle_plugin_unregister(self, request: Request) -> Response:
        """Unregister a plugin"""
        plugin_id = request.match_info['plugin_id']
        
        if plugin_id not in self.registered_plugins:
            return json_response({'error': 'Plugin not found'}, status=404)
        
        # Remove plugin
        del self.registered_plugins[plugin_id]
        
        # Close WebSocket if connected
        if plugin_id in self.plugin_connections:
            ws = self.plugin_connections[plugin_id]
            if not ws.closed:
                await ws.close()
            del self.plugin_connections[plugin_id]
        
        logger.info(f"Plugin unregistered: {plugin_id}")
        
        # Broadcast plugin removal
        await self._broadcast_websocket({
            'type': 'plugin_unregistered',
            'plugin_id': plugin_id
        })
        
        return json_response({
            'success': True,
            'message': f'Plugin {plugin_id} unregistered'
        })
    
    async def handle_plugin_websocket(self, request: Request) -> web.WebSocketResponse:
        """WebSocket connection for a specific plugin"""
        plugin_id = request.match_info['plugin_id']
        
        if plugin_id not in self.registered_plugins:
            return web.Response(text='Plugin not found', status=404)
        
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        # Store plugin connection
        self.plugin_connections[plugin_id] = ws
        logger.info(f"Plugin WebSocket connected: {plugin_id}")
        
        # Update plugin status
        self.registered_plugins[plugin_id]['status'] = 'connected'
        
        # Send welcome message
        await ws.send_json({
            'type': 'connected',
            'message': f'Plugin {plugin_id} connected to Unified Backend',
            'plugin': self.registered_plugins[plugin_id]
        })
        
        try:
            async for msg in ws:
                if msg.type == web.WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    logger.info(f"Plugin {plugin_id} message: {data.get('type', 'unknown')}")
                    
                    # Handle plugin messages
                    if data.get('type') == 'status_update':
                        self.registered_plugins[plugin_id].update(data.get('status', {}))
                    elif data.get('type') == 'action_result':
                        # Broadcast result to interested parties
                        await self._broadcast_websocket({
                            'type': 'plugin_action_result',
                            'plugin_id': plugin_id,
                            'result': data.get('result')
                        })
                    
                elif msg.type == web.WSMsgType.ERROR:
                    logger.error(f'Plugin WebSocket error: {ws.exception()}')
                    
        except Exception as e:
            logger.error(f"Plugin WebSocket error: {e}")
        finally:
            # Clean up
            if plugin_id in self.plugin_connections:
                del self.plugin_connections[plugin_id]
            self.registered_plugins[plugin_id]['status'] = 'disconnected'
            logger.info(f"Plugin WebSocket disconnected: {plugin_id}")
            
        return ws
    
    # Event system methods (if enabled)
    async def _init_event_system(self, app):
        """Initialize event system"""
        if not self.enable_events:
            return
            
        try:
            # Connect to MongoDB
            self.mongo_client = AsyncIOMotorClient(self.mongo_uri)
            
            # Initialize event system
            self.event_system = EventSystemManager(self.mongo_client)
            await self.event_system.initialize()
            
            logger.info("Event system initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize event system: {e}")
            self.enable_events = False
    
    async def _cleanup_event_system(self, app):
        """Cleanup event system"""
        if self.event_system:
            await self.event_system.shutdown()
        
        if self.mongo_client:
            self.mongo_client.close()
    
    # Event API handlers
    async def handle_publish_event(self, request: Request) -> Response:
        """Publish an event to the event bus"""
        if not self.event_system:
            return json_response({'error': 'Event system not available'}, status=503)
        
        try:
            data = await request.json()
            event_bus = self.event_system.get_event_bus()
            
            # Create and publish event
            from ..core.events import Event, EventType, Priority
            event = Event(
                event_type=EventType(data.get('event_type')),
                source=data.get('source', 'unified_backend'),
                data=data.get('data', {}),
                priority=Priority(data.get('priority', 'medium')),
                correlation_id=data.get('correlation_id')
            )
            
            event_id = await event_bus.publish(event)
            
            return json_response({
                'event_id': event_id,
                'status': 'published'
            })
            
        except Exception as e:
            logger.error(f"Failed to publish event: {e}")
            return json_response({'error': str(e)}, status=500)
    
    async def handle_queue_task(self, request: Request) -> Response:
        """Queue a task for execution"""
        if not self.event_system:
            return json_response({'error': 'Event system not available'}, status=503)
        
        try:
            data = await request.json()
            task_queue = self.event_system.get_task_queue()
            
            # Queue task
            from ..core.events import Priority
            task_id = await task_queue.queue_task(
                task_type=data.get('task_type'),
                task_data=data.get('task_data', {}),
                priority=Priority(data.get('priority', 'medium')),
                correlation_id=data.get('correlation_id')
            )
            
            return json_response({
                'task_id': task_id,
                'status': 'queued'
            })
            
        except Exception as e:
            logger.error(f"Failed to queue task: {e}")
            return json_response({'error': str(e)}, status=500)
    
    async def handle_task_status(self, request: Request) -> Response:
        """Get task status"""
        if not self.event_system:
            return json_response({'error': 'Event system not available'}, status=503)
        
        task_id = request.match_info['task_id']
        task_queue = self.event_system.get_task_queue()
        
        # Check task results
        if task_id in task_queue.task_results:
            result = task_queue.task_results[task_id]
            return json_response({
                'task_id': task_id,
                'status': 'completed' if result.success else 'failed',
                'result': result.result if result.success else None,
                'error': result.error if not result.success else None
            })
        
        # Check active tasks
        if task_id in task_queue.active_tasks:
            return json_response({
                'task_id': task_id,
                'status': 'processing'
            })
        
        return json_response({'error': 'Task not found'}, status=404)
    
    async def handle_event_stats(self, request: Request) -> Response:
        """Get event system statistics"""
        if not self.event_system:
            return json_response({'error': 'Event system not available'}, status=503)
        
        try:
            event_bus = self.event_system.get_event_bus()
            task_queue = self.event_system.get_task_queue()
            
            event_stats = await event_bus.get_event_stats()
            queue_stats = task_queue.get_queue_stats()
            
            return json_response({
                'event_stats': event_stats,
                'queue_stats': queue_stats,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return json_response({'error': str(e)}, status=500)
    
    async def handle_recent_events(self, request: Request) -> Response:
        """Get recent events"""
        if not self.event_system:
            return json_response({'error': 'Event system not available'}, status=503)
        
        try:
            limit = int(request.query.get('limit', 100))
            event_bus = self.event_system.get_event_bus()
            
            events = await event_bus.query_events(limit=limit)
            
            return json_response({
                'events': [
                    {
                        'event_id': event.event_id,
                        'event_type': event.event_type.value,
                        'source': event.source,
                        'status': event.status.value,
                        'timestamp': event.timestamp.isoformat(),
                        'correlation_id': event.correlation_id
                    }
                    for event in events
                ],
                'count': len(events)
            })
            
        except Exception as e:
            logger.error(f"Failed to get recent events: {e}")
            return json_response({'error': str(e)}, status=500)
    
    async def handle_event_websocket(self, request: Request) -> web.WebSocketResponse:
        """WebSocket endpoint for real-time event streaming"""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        if not self.event_system:
            await ws.send_json({'error': 'Event system not available'})
            await ws.close()
            return ws
        
        # Subscribe to all events
        event_queue = asyncio.Queue()
        event_bus = self.event_system.get_event_bus()
        
        async def event_handler(event):
            await event_queue.put(event)
        
        event_bus.subscribe_all(event_handler)
        
        try:
            # Send events as they arrive
            while True:
                event = await event_queue.get()
                await ws.send_json({
                    'event_id': event.event_id,
                    'event_type': event.event_type.value,
                    'source': event.source,
                    'data': event.data,
                    'timestamp': event.timestamp.isoformat()
                })
                
        except Exception as e:
            logger.error(f"Event WebSocket error: {e}")
        finally:
            await ws.close()
        
        return ws
    
    # MCP tool request handler (original)
    async def handle_mcp_tool_request(self, request: Request) -> Response:
        """Handle MCP tool execution request from plugins"""
        data = await request.json()
        self.log_request(request, data)
        
        # TODO: Execute tool via MCP bridge
        # For now, just acknowledge
        return json_response({
            'success': True,
            'data': {
                'tool': data.get('tool'),
                'result': 'Tool execution would happen here',
                'timestamp': datetime.now().isoformat()
            }
        })
    
    async def handle_mcp_status(self, request: Request) -> Response:
        """Get MCP bridge status"""
        return json_response({
            'status': 'connected' if self.enable_mcp else 'disabled',
            'mcp_enabled': self.enable_mcp,
            'timestamp': datetime.now().isoformat()
        })
    
    # Main server methods
    async def start(self):
        """Start the unified server"""
        # Find available port
        self.port = self.find_available_port()
        if not self.port:
            raise RuntimeError(f"No available port in range {self.port_range}")
        
        # Create application
        await self.create_app()
        
        # Setup runner
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        
        # Create site with SSL if enabled
        if self.enable_https and self.ssl_context:
            self.site = web.TCPSite(
                self.runner,
                'localhost',
                self.port,
                ssl_context=self.ssl_context
            )
            self.base_url = f"https://localhost:{self.port}"
        else:
            self.site = web.TCPSite(self.runner, 'localhost', self.port)
            self.base_url = f"http://localhost:{self.port}"
        
        await self.site.start()
        
        logger.info(f"Enhanced Unified Backend running on {self.base_url}")
        logger.info(f"Features: MCP={self.enable_mcp}, Events={self.enable_events}, HTTPS={self.enable_https}")
        
        return self.base_url
    
    async def stop(self):
        """Stop the unified server"""
        if self.site:
            await self.site.stop()
        
        if self.runner:
            await self.runner.cleanup()
        
        logger.info("Enhanced Unified Backend stopped")


# Convenience function to create and start server
async def start_enhanced_unified_backend(
    port_range=(3000, 3003),
    enable_mcp=True,
    enable_events=True,
    enable_https=False
) -> str:
    """Start the enhanced unified backend server"""
    server = EnhancedUnifiedServer(
        port_range=port_range,
        enable_mcp=enable_mcp,
        enable_events=enable_events,
        enable_https=enable_https
    )
    
    url = await server.start()
    
    # Keep reference to server for cleanup
    import atexit
    atexit.register(lambda: asyncio.create_task(server.stop()))
    
    return url