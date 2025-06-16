"""
Authentication Manager for MCP Bridge

Provides a unified interface for handling OAuth and other authentication flows
within the MCP protocol, allowing connectors to request authentication without
breaking the JSON-RPC communication.
"""

import asyncio
import json
import logging
import os
import pickle
import secrets
import threading
import webbrowser
from datetime import datetime, timedelta
from enum import Enum
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple
from urllib.parse import parse_qs, urlparse

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class AuthStatus(Enum):
    """Authentication status states"""
    AUTHENTICATED = "authenticated"
    NEEDS_AUTH = "needs_auth"
    AUTH_IN_PROGRESS = "auth_in_progress"
    AUTH_FAILED = "auth_failed"
    TOKEN_EXPIRED = "token_expired"


class AuthRequest(BaseModel):
    """Authentication request details"""
    service_name: str
    auth_url: str
    instructions: str
    callback_uri: Optional[str] = None
    state: Optional[str] = None
    expires_at: Optional[datetime] = None


class AuthResult(BaseModel):
    """Authentication result"""
    success: bool
    error: Optional[str] = None
    credentials: Optional[Dict[str, Any]] = None


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """Handle OAuth callbacks"""
    
    def do_GET(self):
        """Handle GET request with auth code"""
        parsed_url = urlparse(self.path)
        query_params = parse_qs(parsed_url.query)
        
        if "code" in query_params:
            self.server.auth_code = query_params["code"][0]
            self.server.state = query_params.get("state", [None])[0]
            
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            
            success_html = f"""
            <html>
            <head>
                <title>Authentication Successful</title>
                <style>
                    body {{
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                        text-align: center;
                        padding: 50px;
                        background: #f8f9fa;
                    }}
                    .container {{
                        max-width: 500px;
                        margin: 0 auto;
                        background: white;
                        padding: 40px;
                        border-radius: 12px;
                        box-shadow: 0 4px 20px rgba(0,0,0,0.1);
                    }}
                    h1 {{ color: #2563eb; margin-bottom: 20px; }}
                    .code-box {{
                        background: #f3f4f6;
                        padding: 15px;
                        border-radius: 8px;
                        font-family: monospace;
                        word-break: break-all;
                        margin: 20px 0;
                    }}
                    .instructions {{
                        color: #6b7280;
                        font-size: 16px;
                        line-height: 1.5;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>✅ Authentication Successful!</h1>
                    <p class="instructions">
                        {self.server.service_name} has been authenticated successfully.
                    </p>
                    <div class="code-box">
                        Authorization Code: {query_params["code"][0][:20]}...
                    </div>
                    <p class="instructions">
                        You can close this window and return to Claude Desktop.
                    </p>
                </div>
            </body>
            </html>
            """
            self.wfile.write(success_html.encode())
            
        elif "error" in query_params:
            self.server.auth_error = query_params["error"][0]
            self.send_response(400)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            
            error_html = f"""
            <html>
            <body style="font-family: sans-serif; text-align: center; padding: 50px;">
                <h1>❌ Authentication Failed</h1>
                <p>Error: {query_params.get("error_description", ["Unknown error"])[0]}</p>
                <p>Please try again in Claude Desktop.</p>
            </body>
            </html>
            """
            self.wfile.write(error_html.encode())
    
    def log_message(self, format, *args):
        """Suppress request logging"""
        pass


class AuthenticationManager:
    """Manages authentication flows for MCP Bridge connectors"""
    
    def __init__(self, base_path: Path = None):
        """Initialize authentication manager
        
        Args:
            base_path: Base path for storing credentials
        """
        self.base_path = base_path or Path.home() / ".mcp-bridge" / "auth"
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        self._auth_servers: Dict[str, HTTPServer] = {}
        self._auth_states: Dict[str, AuthRequest] = {}
        self._callbacks: Dict[str, Callable] = {}
        
    def create_auth_request(
        self,
        service_name: str,
        auth_url: str,
        instructions: Optional[str] = None,
        callback_port: Optional[int] = None
    ) -> AuthRequest:
        """Create an authentication request
        
        Args:
            service_name: Name of the service requiring auth
            auth_url: OAuth authorization URL
            instructions: User instructions
            callback_port: Optional callback port for OAuth flow
            
        Returns:
            AuthRequest object
        """
        state = secrets.token_urlsafe(32)
        
        if not instructions:
            instructions = (
                f"To authenticate {service_name}:\n"
                f"1. Click or copy the URL below\n"
                f"2. Sign in and authorize access\n"
                f"3. You'll be redirected back automatically"
            )
        
        callback_uri = None
        if callback_port:
            callback_uri = f"http://localhost:{callback_port}/callback"
            
        request = AuthRequest(
            service_name=service_name,
            auth_url=auth_url,
            instructions=instructions,
            callback_uri=callback_uri,
            state=state,
            expires_at=datetime.now() + timedelta(minutes=10)
        )
        
        self._auth_states[state] = request
        return request
    
    async def start_oauth_server(
        self,
        service_name: str,
        port: int,
        callback: Callable[[str, Optional[str]], None]
    ) -> None:
        """Start OAuth callback server
        
        Args:
            service_name: Service name for display
            port: Port to listen on
            callback: Callback function when auth completes
        """
        if port in self._auth_servers:
            logger.warning(f"OAuth server already running on port {port}")
            return
            
        def run_server():
            server = HTTPServer(("localhost", port), OAuthCallbackHandler)
            server.service_name = service_name
            server.auth_code = None
            server.auth_error = None
            server.state = None
            
            self._auth_servers[port] = server
            
            # Handle single request
            server.handle_request()
            
            # Call callback with results
            if server.auth_code:
                callback(server.auth_code, server.state)
            elif server.auth_error:
                callback(None, server.auth_error)
                
            # Cleanup
            del self._auth_servers[port]
            
        # Run server in background thread
        thread = threading.Thread(target=run_server, daemon=True)
        thread.start()
        
        # Give server time to start
        await asyncio.sleep(0.1)
        
    def format_auth_response(self, request: AuthRequest) -> Dict[str, Any]:
        """Format authentication request for MCP response
        
        Args:
            request: Authentication request
            
        Returns:
            Formatted response for MCP protocol
        """
        return {
            "type": "authentication_required",
            "service": request.service_name,
            "auth_url": request.auth_url,
            "instructions": request.instructions,
            "state": request.state,
            "expires_at": request.expires_at.isoformat() if request.expires_at else None
        }
    
    def save_credentials(
        self,
        service_name: str,
        credentials: Any,
        format: str = "pickle"
    ) -> Path:
        """Save credentials securely
        
        Args:
            service_name: Service name
            credentials: Credentials to save
            format: Storage format (pickle or json)
            
        Returns:
            Path to saved credentials
        """
        filename = f"{service_name}_token.{format}"
        filepath = self.base_path / filename
        
        if format == "pickle":
            with open(filepath, "wb") as f:
                pickle.dump(credentials, f)
        elif format == "json":
            with open(filepath, "w") as f:
                json.dump(credentials, f)
        else:
            raise ValueError(f"Unknown format: {format}")
            
        logger.info(f"Saved {service_name} credentials to {filepath}")
        return filepath
    
    def load_credentials(
        self,
        service_name: str,
        format: str = "pickle"
    ) -> Optional[Any]:
        """Load saved credentials
        
        Args:
            service_name: Service name
            format: Storage format (pickle or json)
            
        Returns:
            Credentials if found, None otherwise
        """
        filename = f"{service_name}_token.{format}"
        filepath = self.base_path / filename
        
        if not filepath.exists():
            return None
            
        try:
            if format == "pickle":
                with open(filepath, "rb") as f:
                    return pickle.load(f)
            elif format == "json":
                with open(filepath, "r") as f:
                    return json.load(f)
            else:
                raise ValueError(f"Unknown format: {format}")
        except Exception as e:
            logger.error(f"Failed to load {service_name} credentials: {e}")
            return None
    
    def check_auth_status(self, service_name: str) -> AuthStatus:
        """Check authentication status for a service
        
        Args:
            service_name: Service to check
            
        Returns:
            Current authentication status
        """
        # Check if we have saved credentials
        creds = self.load_credentials(service_name)
        if not creds:
            return AuthStatus.NEEDS_AUTH
            
        # Check if credentials are valid (service-specific logic needed)
        # For now, assume valid if they exist
        return AuthStatus.AUTHENTICATED
    
    async def wait_for_auth(
        self,
        state: str,
        timeout: int = 300
    ) -> Optional[AuthResult]:
        """Wait for authentication to complete
        
        Args:
            state: Authentication state token
            timeout: Timeout in seconds
            
        Returns:
            Authentication result or None if timeout
        """
        # This would be implemented to wait for OAuth callback
        # For now, return None
        return None


# Global instance
_auth_manager: Optional[AuthenticationManager] = None


def get_auth_manager() -> AuthenticationManager:
    """Get global authentication manager instance"""
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = AuthenticationManager()
    return _auth_manager