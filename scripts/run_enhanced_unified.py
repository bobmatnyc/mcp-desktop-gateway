#!/usr/bin/env python3
"""
Run the Enhanced Unified Backend with OAuth and MCP support
"""

import asyncio
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.unified_backend.enhanced_server import EnhancedUnifiedServer

async def main():
    """Start the enhanced unified backend server"""
    print("Starting Enhanced Unified Backend Server...")
    print("=" * 60)
    
    # Create server instance with MCP and OAuth enabled
    server = EnhancedUnifiedServer(
        port_range=(3003, 3003),  # Use specific port
        enable_events=False,  # Disable event system for now
        enable_mcp=True,     # Enable MCP integration
        enable_https=False   # HTTP for ngrok
    )
    
    try:
        # Start the server
        base_url = await server.start()
        
        print(f"\n✅ Enhanced Unified Backend Started!")
        print(f"📍 Base URL: {base_url}")
        print(f"🔌 Port: {server.port}")
        print(f"\nOAuth Endpoints:")
        print(f"  Discovery: {base_url}/.well-known/oauth-authorization-server")
        print(f"  Authorization: {base_url}/oauth/authorize")
        print(f"  Token: {base_url}/oauth/token")
        print(f"  Registration: {base_url}/register")
        print(f"\nMCP Endpoints:")
        print(f"  Discovery: {base_url}/api/mcp")
        print(f"  SSE Stream: {base_url}/mcp")
        print(f"  Tools: {base_url}/mcp/tools")
        print(f"\nPress Ctrl+C to stop the server\n")
        
        # Keep the server running
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\nShutting down server...")
    except Exception as e:
        print(f"\n❌ Error: {e}")
    finally:
        await server.stop()
        print("Server stopped.")

if __name__ == "__main__":
    # Run the server
    asyncio.run(main())