#!/bin/bash
# Development setup script

echo "🚀 Setting up MCP Gateway development environment..."

# 1. Create Python virtual environment for development
echo "📦 Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# 2. Install Python dependencies
echo "📚 Installing Python dependencies..."
pip install -r requirements.txt
# Skip pip install -e . for now as it's not needed for development

# 3. Create development command
echo "🔗 Creating development command..."
cat > mcp-gateway-dev << 'EOF'
#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source "$DIR/venv/bin/activate"
export PYTHONPATH="$DIR/src:$PYTHONPATH"
python "$DIR/run_mcp_gateway.py" "$@"
EOF

chmod +x mcp-gateway-dev

# Try to create symlink in /usr/local/bin if possible, otherwise just use local
if [ -w /usr/local/bin ]; then
    ln -sf "$PWD/mcp-gateway-dev" /usr/local/bin/mcp-gateway-dev 2>/dev/null || true
else
    echo "ℹ️  Cannot create system-wide command. Use ./mcp-gateway-dev instead"
fi

# 4. Set up npm for local testing
echo "📦 Setting up NPM for local testing..."
npm link

echo "✅ Development setup complete!"
echo ""
echo "Usage:"
echo "  Development: mcp-gateway-dev"
echo "  NPM testing: mcp-gateway (after npm link)"
echo "  Direct Python: source venv/bin/activate && python run_mcp_gateway.py"