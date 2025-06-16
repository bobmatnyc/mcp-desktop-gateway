"""
Simple OAuth implementation for Claude.ai MCP integration
"""

from aiohttp import web
from aiohttp.web import Request, Response
import uuid
import logging
from urllib.parse import urlencode, parse_qs

logger = logging.getLogger(__name__)


class SimpleOAuthHandler:
    """Simple OAuth handler for development"""
    
    def __init__(self, server):
        self.server = server
        self.authorization_codes = {}  # Store temp auth codes
        
    def get_routes(self):
        """Get OAuth routes"""
        return [
            web.get('/oauth/authorize', self.handle_authorize),
            web.post('/oauth/token', self.handle_token),
            web.get('/oauth/callback', self.handle_callback),
            web.get('/oauth/userinfo', self.handle_userinfo),
            web.get('/userinfo', self.handle_userinfo),  # Alternative path
        ]
        
    async def handle_authorize(self, request: Request) -> Response:
        """OAuth authorization endpoint"""
        # Get query parameters
        client_id = request.query.get('client_id', 'claude-ai')
        redirect_uri = request.query.get('redirect_uri', '')
        state = request.query.get('state', '')
        response_type = request.query.get('response_type', 'code')
        
        # In production, you'd show a login page here
        # For development, auto-approve
        
        # Generate authorization code
        auth_code = f"dev_code_{uuid.uuid4().hex[:8]}"
        self.authorization_codes[auth_code] = {
            'client_id': client_id,
            'redirect_uri': redirect_uri,
            'user_id': 'dev-user'
        }
        
        # Redirect back with code
        if redirect_uri:
            params = {
                'code': auth_code,
                'state': state
            }
            redirect_url = f"{redirect_uri}?{urlencode(params)}"
            
            logger.info(f"OAuth authorize: redirecting to {redirect_url}")
            return web.HTTPFound(redirect_url)
        else:
            # Show simple approval page
            html = f"""
            <html>
            <head>
                <title>MCP Bridge Authorization</title>
                <style>
                    body {{ font-family: Arial; padding: 40px; max-width: 600px; margin: 0 auto; }}
                    .container {{ background: #f5f5f5; padding: 30px; border-radius: 10px; }}
                    h2 {{ color: #333; }}
                    .info {{ background: white; padding: 20px; border-radius: 5px; margin: 20px 0; }}
                    .code {{ font-family: monospace; background: #333; color: #0f0; padding: 10px; }}
                    button {{ background: #4CAF50; color: white; padding: 12px 24px; border: none; 
                             border-radius: 5px; font-size: 16px; cursor: pointer; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h2>🔐 MCP Bridge Authorization</h2>
                    <div class="info">
                        <p><strong>Client:</strong> {client_id}</p>
                        <p><strong>Authorization Code:</strong></p>
                        <div class="code">{auth_code}</div>
                    </div>
                    <p>This is a development OAuth flow. In production, users would log in here.</p>
                    <p>Copy the authorization code above if needed.</p>
                </div>
            </body>
            </html>
            """
            return web.Response(text=html, content_type='text/html')
    
    async def handle_token(self, request: Request) -> Response:
        """OAuth token endpoint"""
        try:
            data = await request.post()
            
            grant_type = data.get('grant_type', 'authorization_code')
            code = data.get('code', '')
            
            # Validate authorization code
            if code in self.authorization_codes:
                # Generate access token
                access_token = f"mcp_token_{uuid.uuid4().hex}"
                
                logger.info(f"OAuth token exchange successful for code: {code}")
                
                return web.json_response({
                    "access_token": access_token,
                    "token_type": "Bearer",
                    "expires_in": 3600,
                    "scope": "read write execute"
                })
            else:
                return web.json_response({
                    "error": "invalid_grant",
                    "error_description": "Invalid authorization code"
                }, status=400)
                
        except Exception as e:
            logger.error(f"OAuth token error: {e}")
            return web.json_response({
                "error": "server_error",
                "error_description": str(e)
            }, status=500)
    
    async def handle_userinfo(self, request: Request) -> Response:
        """OAuth userinfo endpoint"""
        # In dev mode, just return a simple user
        return web.json_response({
            "sub": "dev-user-001",
            "name": "Development User",
            "email": "dev@mcp-bridge.local",
            "preferred_username": "devuser"
        })
    
    async def handle_callback(self, request: Request) -> Response:
        """OAuth callback handler"""
        code = request.query.get('code', '')
        state = request.query.get('state', '')
        
        html = f"""
        <html>
        <head><title>Authorization Complete</title></head>
        <body style="font-family: Arial; padding: 40px; text-align: center;">
            <h2>✅ Authorization Complete</h2>
            <p>You can close this window and return to Claude.ai</p>
            <p style="color: #666;">Authorization code: {code}</p>
        </body>
        </html>
        """
        return web.Response(text=html, content_type='text/html')