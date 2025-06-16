# src/core/oauth_callback_server.py
"""
Minimal OAuth callback server for MCP Bridge
"""

import asyncio
import logging
from typing import Optional, Dict, Any
from aiohttp import web
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class OAuthCallbackResult(BaseModel):
    """Result from OAuth callback"""
    success: bool
    error: Optional[str] = None
    code: Optional[str] = None
    state: Optional[str] = None
    error_description: Optional[str] = None


async def run_oauth_callback_server(port: int = 8080, timeout: int = 300) -> Optional[str]:
    """
    Start a temporary OAuth callback server
    
    Args:
        port: Port to listen on
        timeout: Timeout in seconds
        
    Returns:
        Authorization code if successful, None otherwise
    """
    
    result = None
    
    async def callback_handler(request):
        nonlocal result
        
        # Extract query parameters
        query_params = dict(request.query)
        
        if 'error' in query_params:
            result = OAuthCallbackResult(
                success=False,
                error=query_params.get('error'),
                error_description=query_params.get('error_description')
            )
        elif 'code' in query_params:
            result = OAuthCallbackResult(
                success=True,
                code=query_params.get('code'),
                state=query_params.get('state')
            )
        else:
            result = OAuthCallbackResult(
                success=False,
                error="invalid_request",
                error_description="No code or error parameter received"
            )
        
        # Return success page
        return web.Response(
            text="""
            <html>
            <head><title>OAuth Success</title></head>
            <body>
                <h1>Authorization Complete</h1>
                <p>You can now close this window and return to Claude Desktop.</p>
                <script>window.close();</script>
            </body>
            </html>
            """,
            content_type='text/html'
        )
    
    # Create web application
    app = web.Application()
    app.router.add_get('/oauth/callback', callback_handler)
    app.router.add_get('/callback', callback_handler)  # Alternative path
    
    # Start server
    runner = web.AppRunner(app)
    await runner.setup()
    
    site = web.TCPSite(runner, 'localhost', port)
    await site.start()
    
    logger.info(f"OAuth callback server started on http://localhost:{port}")
    
    try:
        # Wait for callback or timeout
        start_time = asyncio.get_event_loop().time()
        while result is None:
            if asyncio.get_event_loop().time() - start_time > timeout:
                result = OAuthCallbackResult(
                    success=False,
                    error="timeout",
                    error_description=f"OAuth callback not received within {timeout} seconds"
                )
                break
            
            await asyncio.sleep(0.1)
        
        return result.code if result and result.success else None
        
    finally:
        await runner.cleanup()
        logger.info("OAuth callback server stopped")


async def oauth_callback_server(port: int = 8080, timeout: int = 300) -> OAuthCallbackResult:
    """
    Start a temporary OAuth callback server (legacy function)
    
    Args:
        port: Port to listen on
        timeout: Timeout in seconds
        
    Returns:
        OAuthCallbackResult with the callback data
    """
    auth_code = await run_oauth_callback_server(port, timeout)
    if auth_code:
        return OAuthCallbackResult(success=True, code=auth_code)
    else:
        return OAuthCallbackResult(success=False, error="No authorization code received")
