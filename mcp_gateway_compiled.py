#!/usr/bin/env python3
import sys
import os

# Add compiled modules to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import and run from compiled bytecode
from __pycache__.run_mcp_gateway import main
if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
