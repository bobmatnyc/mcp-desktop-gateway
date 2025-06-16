"""
MCP Router for Claude.AI Web Integration
Provides HTTP+SSE endpoints for MCP protocol
"""

import logging
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel

from ..services.mcp_service import MCPService
from ..auth.dependencies import get_current_user, User

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/mcp", tags=["mcp"])

# Shared MCP service instance
mcp_service: Optional[MCPService] = None


class OAuthCallback(BaseModel):
    """OAuth callback data"""
    code: str
    state: str


class MCPRequest(BaseModel):
    """MCP JSON-RPC request"""
    jsonrpc: str = "2.0"
    id: Optional[str] = None
    method: str
    params: Optional[dict] = None


async def get_mcp_service() -> MCPService:
    """Get or create MCP service instance"""
    global mcp_service
    if mcp_service is None:
        mcp_service = MCPService()
        await mcp_service.initialize()
    return mcp_service


@router.get("/")
async def mcp_sse_endpoint(
    request: Request,
    user: User = Depends(get_current_user),
    service: MCPService = Depends(get_mcp_service)
):
    """
    Main MCP Server-Sent Events endpoint for Claude.AI integration
    
    This endpoint establishes an SSE connection for bidirectional communication
    using the MCP protocol over HTTP.
    """
    logger.info(f"New MCP SSE connection from user: {user.id}")
    
    # Check if this is an SSE request
    if request.headers.get("accept") != "text/event-stream":
        return JSONResponse(
            content={
                "error": "This endpoint requires Server-Sent Events",
                "hint": "Set Accept: text/event-stream header"
            },
            status_code=400
        )
    
    # Create SSE response
    return StreamingResponse(
        service.handle_sse_connection(user.id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable Nginx buffering
            "Access-Control-Allow-Origin": "https://claude.ai",
            "Access-Control-Allow-Credentials": "true"
        }
    )


@router.post("/request")
async def mcp_request_endpoint(
    request: MCPRequest,
    user: User = Depends(get_current_user),
    service: MCPService = Depends(get_mcp_service)
):
    """
    Alternative endpoint for single MCP requests (non-streaming)
    
    This can be used for one-off requests without establishing an SSE connection.
    """
    logger.info(f"MCP request from user {user.id}: {request.method}")
    
    # Process the request
    response = await service.process_mcp_request(
        request.dict(),
        user.id
    )
    
    return response


@router.get("/tools")
async def list_tools(
    user: User = Depends(get_current_user),
    service: MCPService = Depends(get_mcp_service)
):
    """
    Convenience endpoint to list available tools
    
    Returns all tools available to the authenticated user.
    """
    # Create a synthetic MCP request
    response = await service.handle_list_tools("list_tools_request")
    
    # Extract just the tools array
    return {
        "tools": response["result"]["tools"],
        "total": len(response["result"]["tools"])
    }


@router.get("/resources")
async def list_resources(
    user: User = Depends(get_current_user),
    service: MCPService = Depends(get_mcp_service)
):
    """
    Convenience endpoint to list available resources
    
    Returns all resources available to the authenticated user.
    """
    response = await service.handle_list_resources("list_resources_request")
    
    return {
        "resources": response["result"]["resources"],
        "total": len(response["result"]["resources"])
    }


@router.get("/prompts")
async def list_prompts(
    user: User = Depends(get_current_user),
    service: MCPService = Depends(get_mcp_service)
):
    """
    Convenience endpoint to list available prompts
    
    Returns all prompts available to the authenticated user.
    """
    response = await service.handle_list_prompts("list_prompts_request")
    
    return {
        "prompts": response["result"]["prompts"],
        "total": len(response["result"]["prompts"])
    }


@router.post("/auth/callback")
async def oauth_callback(callback: OAuthCallback):
    """
    Handle OAuth 2.0 callback from Claude.AI
    
    This endpoint receives the authorization code after user approves
    the integration in Claude.AI.
    """
    logger.info(f"OAuth callback received with state: {callback.state}")
    
    # TODO: Implement OAuth token exchange
    # For now, return success
    return {
        "status": "success",
        "message": "OAuth callback received",
        "integration_id": str(uuid4())
    }


@router.get("/health")
async def health_check(service: MCPService = Depends(get_mcp_service)):
    """
    Health check endpoint for MCP service
    
    Returns the current status of the MCP service and its components.
    """
    return {
        "status": "healthy",
        "service": "mcp",
        "active_sessions": len(service.active_sessions),
        "initialized_connectors": len(service.connector_registry.list_initialized_connectors()),
        "total_tools": len(service.connector_registry.get_all_tools())
    }


@router.get("/info")
async def service_info(service: MCPService = Depends(get_mcp_service)):
    """
    Get detailed information about the MCP service
    
    Returns capabilities, version, and configuration details.
    """
    return {
        "service": "py-mcp-bridge MCP Server",
        "version": "2.6.0",
        "protocol": "MCP 2024-11-05",
        "transport": "HTTP+SSE",
        "capabilities": {
            "tools": True,
            "resources": True,
            "prompts": True,
            "streaming": True
        },
        "connectors": service.connector_registry.list_initialized_connectors(),
        "endpoints": {
            "sse": "/mcp/",
            "request": "/mcp/request",
            "tools": "/mcp/tools",
            "resources": "/mcp/resources",
            "prompts": "/mcp/prompts",
            "oauth": "/mcp/auth/callback",
            "health": "/mcp/health"
        }
    }


# WebSocket support (alternative to SSE)
@router.websocket("/ws")
async def mcp_websocket_endpoint(
    websocket,
    user: User = Depends(get_current_user),
    service: MCPService = Depends(get_mcp_service)
):
    """
    WebSocket endpoint for MCP protocol (alternative to SSE)
    
    This provides full duplex communication for scenarios where
    SSE might not be suitable.
    """
    await websocket.accept()
    session_id = f"mcp_ws_{user.id}_{uuid4()}"
    logger.info(f"New WebSocket connection: {session_id}")
    
    try:
        # Send initial connection message
        await websocket.send_json({
            "type": "connection",
            "status": "connected",
            "session_id": session_id
        })
        
        # Handle messages
        while True:
            data = await websocket.receive_json()
            
            # Process MCP request
            response = await service.process_mcp_request(data, user.id)
            
            # Send response
            await websocket.send_json(response)
            
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        logger.info(f"WebSocket closed: {session_id}")