#!/bin/bash
# Test the NPM package locally

echo "🧪 Testing MCP Gateway NPM Package..."

# 1. Clean previous builds
echo "🧹 Cleaning previous builds..."
rm -rf node_modules package-lock.json
rm -rf venv __pycache__ src/__pycache__

# 2. Test npm install
echo "📦 Testing npm install..."
npm install

# 3. Test the CLI
echo "🔧 Testing CLI commands..."
echo "  Testing help..."
node lib/cli.js help

echo "  Testing setup..."
node lib/cli.js setup

echo "  Testing config..."
node lib/cli.js config

# 4. Test running the gateway
echo "🚀 Testing gateway startup (5 seconds)..."
timeout 5 node lib/cli.js || true

# 5. Check that files were created
echo "📁 Checking created files..."
if [ -d "venv" ]; then
    echo "  ✅ Virtual environment created"
else
    echo "  ❌ Virtual environment NOT created"
fi

if [ -f "venv/bin/python" ] || [ -f "venv/Scripts/python.exe" ]; then
    echo "  ✅ Python executable found"
else
    echo "  ❌ Python executable NOT found"
fi

# 6. Test with npm link (global install simulation)
echo "🌍 Testing global install with npm link..."
npm link

# Test global command
which mcp-gateway && echo "  ✅ Global command available" || echo "  ❌ Global command NOT available"

echo ""
echo "✅ Package testing complete!"
echo ""
echo "To test in Claude Desktop:"
echo "1. Update config with: mcp-gateway config"
echo "2. Restart Claude Desktop"
echo "3. Check available tools"