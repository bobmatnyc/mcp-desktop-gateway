#!/usr/bin/env python3
"""
Run the MCP Gateway server
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import and run the gateway
from src.mcp_gateway import main
import asyncio

if __name__ == "__main__":
    print("Starting MCP Gateway...")
    print("=" * 60)
    print()
    print("Configure Claude Desktop to connect to: http://localhost:3000")
    print()
    print("To add connectors:")
    print("1. Edit config/connectors.yaml")
    print("2. Start your connector services")
    print("3. Restart this gateway")
    print()
    print("Press Ctrl+C to stop")
    print("=" * 60)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nGateway stopped.")