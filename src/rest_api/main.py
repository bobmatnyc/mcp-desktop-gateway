"""
Enhanced REST API Server with MCP Support for Claude.AI
"""

import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Import routers
from .routers import mcp

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application lifecycle"""
    logger.info("Starting REST API + MCP Server")
    
    # Startup tasks
    yield
    
    # Shutdown tasks
    logger.info("Shutting down REST API + MCP Server")
    
    # Cleanup MCP service if needed
    from .routers.mcp import mcp_service
    if mcp_service:
        await mcp_service.shutdown()


# Create FastAPI app
app = FastAPI(
    title="py-mcp-bridge API + MCP Server",
    version="2.6.0",
    description="Unified REST API and MCP server for Claude integrations",
    lifespan=lifespan
)

# Configure CORS for Claude.AI
origins = [
    "https://claude.ai",
    "https://console.anthropic.com",
    "http://localhost:3000",  # Development
    "http://localhost:5173",  # Vite dev server
]

# Add any custom origins from environment
custom_origins = os.getenv("CORS_ORIGINS", "").split(",")
origins.extend([o.strip() for o in custom_origins if o.strip()])

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"]
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc) if os.getenv("DEBUG") else "An error occurred"
        }
    )


# Include routers
app.include_router(mcp.router)

# You can include additional routers here
# app.include_router(api.router, prefix="/api/v1")


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "service": "py-mcp-bridge REST API + MCP Server",
        "version": "2.6.0",
        "endpoints": {
            "mcp": "/mcp",
            "docs": "/docs",
            "openapi": "/openapi.json",
            "health": "/health"
        }
    }


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "services": ["rest_api", "mcp_server"],
        "version": "2.6.0"
    }


# Auth endpoints (for testing)
@app.post("/auth/token")
async def create_token(user_id: str = "test-user"):
    """Create a test JWT token (development only)"""
    if os.getenv("ENV") == "production":
        return {"error": "Not available in production"}
        
    from .auth.dependencies import create_access_token
    
    token = create_access_token(
        user_id=user_id,
        email=f"{user_id}@example.com",
        is_claude_ai=True
    )
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user_id
    }


if __name__ == "__main__":
    import uvicorn
    
    # Get configuration from environment
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8080"))
    
    # Run with SSL in production
    ssl_cert = os.getenv("SSL_CERT_FILE")
    ssl_key = os.getenv("SSL_KEY_FILE")
    
    if ssl_cert and ssl_key:
        uvicorn.run(
            app,
            host=host,
            port=port,
            ssl_certfile=ssl_cert,
            ssl_keyfile=ssl_key
        )
    else:
        logger.warning("Running without SSL - use only for development!")
        uvicorn.run(app, host=host, port=port)