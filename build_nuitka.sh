#!/bin/bash
# Nuitka compilation script for MCP Gateway
# Creates a standalone binary with better performance

# Install Nuitka if not present
pip install nuitka

# Create standalone binary
python -m nuitka \
    --standalone \
    --onefile \
    --follow-imports \
    --include-package=src \
    --include-package=mcp \
    --include-data-dir=config=config \
    --include-data-dir=src=src \
    --enable-plugin=anti-bloat \
    --python-flag=no_site \
    --python-flag=no_warnings \
    --python-flag=no_asserts \
    --output-dir=dist \
    --output-filename=mcp-gateway \
    run_mcp_gateway.py

echo "Binary created at: dist/mcp-gateway"