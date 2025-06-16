"""
OAuth 2.1 Well-Known Configuration for Claude.ai MCP Integration
"""

from aiohttp import web
from aiohttp.web import Request, Response
import logging

logger = logging.getLogger(__name__)


class OAuthWellKnownHandler:
    """Handles OAuth well-known configuration endpoints"""
    
    def __init__(self, server):
        self.server = server
        
    def get_routes(self):
        """Get OAuth well-known routes"""
        return [
            web.get('/.well-known/oauth-authorization-server', self.handle_oauth_metadata),
            web.get('/.well-known/openid-configuration', self.handle_openid_config),
        ]
        
    async def handle_oauth_metadata(self, request: Request) -> Response:
        """OAuth 2.1 Authorization Server Metadata"""
        host = request.headers.get('Host', f'localhost:{self.server.port}')
        scheme = 'https' if 'ngrok' in host or request.secure else 'http'
        base_url = f"{scheme}://{host}"
        
        metadata = {
            "issuer": base_url,
            "authorization_endpoint": f"{base_url}/oauth/authorize",
            "token_endpoint": f"{base_url}/oauth/token",
            "registration_endpoint": f"{base_url}/register",
            "userinfo_endpoint": f"{base_url}/oauth/userinfo",
            "token_endpoint_auth_methods_supported": ["none", "client_secret_post"],
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code"],
            "code_challenge_methods_supported": ["S256", "plain"],
            "scopes_supported": ["read", "write", "execute"],
            "service_documentation": f"{base_url}/docs",
            
            # MCP specific
            "mcp_version": "2024-11-05",
            "mcp_endpoint": f"{base_url}/mcp",
            "mcp_capabilities": {
                "tools": True,
                "resources": True,
                "prompts": True,
                "streaming": True
            }
        }
        
        return web.json_response(metadata)
        
    async def handle_openid_config(self, request: Request) -> Response:
        """OpenID Connect Discovery (fallback)"""
        # Redirect to OAuth metadata
        return await self.handle_oauth_metadata(request)