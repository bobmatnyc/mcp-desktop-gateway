#!/bin/bash

# MCP Desktop Gateway - Claude Desktop Configuration Installer
# This script automatically configures Claude Desktop to use the MCP Desktop Gateway

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
CLAUDE_CONFIG_DIR="$HOME/Library/Application Support/Claude"
CLAUDE_CONFIG_FILE="$CLAUDE_CONFIG_DIR/claude_desktop_config.json"
MCP_SERVER_NAME="mcp-desktop-gateway"
BACKUP_SUFFIX=".backup.$(date +%Y%m%d_%H%M%S)"

echo -e "${BLUE}🚀 MCP Desktop Gateway - Claude Desktop Configuration Installer${NC}"
echo ""

# Check if Claude Desktop config directory exists
if [ ! -d "$CLAUDE_CONFIG_DIR" ]; then
    echo -e "${YELLOW}⚠️  Claude Desktop config directory not found. Creating it...${NC}"
    mkdir -p "$CLAUDE_CONFIG_DIR"
fi

# Check if mcp-desktop-gateway is installed
if ! command -v mcp-desktop-gateway &> /dev/null; then
    echo -e "${RED}❌ mcp-desktop-gateway not found in PATH${NC}"
    echo "Please install it first with:"
    echo "  npm install -g @bobmatnyc/mcp-desktop-gateway"
    exit 1
fi

echo -e "${GREEN}✅ mcp-desktop-gateway found in PATH${NC}"

# Backup existing config if it exists
if [ -f "$CLAUDE_CONFIG_FILE" ]; then
    echo -e "${YELLOW}📋 Backing up existing Claude Desktop config...${NC}"
    cp "$CLAUDE_CONFIG_FILE" "${CLAUDE_CONFIG_FILE}${BACKUP_SUFFIX}"
    echo -e "${GREEN}✅ Backup created: ${CLAUDE_CONFIG_FILE}${BACKUP_SUFFIX}${NC}"
fi

# Create or update Claude Desktop config
if [ -f "$CLAUDE_CONFIG_FILE" ]; then
    # Check if config already exists
    if grep -q "$MCP_SERVER_NAME" "$CLAUDE_CONFIG_FILE" 2>/dev/null; then
        echo -e "${YELLOW}⚠️  MCP Desktop Gateway already configured in Claude Desktop${NC}"
        echo "Current configuration found. Would you like to update it? (y/N)"
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            echo -e "${BLUE}ℹ️  Configuration unchanged${NC}"
            exit 0
        fi
    fi
    
    # Parse existing JSON and add/update our server
    echo -e "${BLUE}🔧 Updating existing Claude Desktop configuration...${NC}"
    
    # Use Python to safely update JSON
    python3 - <<EOF
import json
import sys

config_file = "$CLAUDE_CONFIG_FILE"
server_name = "$MCP_SERVER_NAME"

try:
    # Read existing config
    with open(config_file, 'r') as f:
        config = json.load(f)
except (json.JSONDecodeError, FileNotFoundError):
    config = {}

# Ensure mcpServers exists
if 'mcpServers' not in config:
    config['mcpServers'] = {}

# Add/update our server
config['mcpServers'][server_name] = {
    "command": "mcp-desktop-gateway"
}

# Write updated config
with open(config_file, 'w') as f:
    json.dump(config, f, indent=2)

print("Configuration updated successfully")
EOF

else
    # Create new config file
    echo -e "${BLUE}🔧 Creating new Claude Desktop configuration...${NC}"
    cat > "$CLAUDE_CONFIG_FILE" << 'EOF'
{
  "mcpServers": {
    "mcp-desktop-gateway": {
      "command": "mcp-desktop-gateway"
    }
  }
}
EOF
fi

echo -e "${GREEN}✅ Claude Desktop configuration completed!${NC}"
echo ""
echo -e "${BLUE}📝 Configuration Details:${NC}"
echo "  Config file: $CLAUDE_CONFIG_FILE"
echo "  Server name: $MCP_SERVER_NAME"
echo "  Command: mcp-desktop-gateway"
echo ""

# Verify configuration
echo -e "${BLUE}🔍 Verifying configuration...${NC}"
if python3 -c "import json; json.load(open('$CLAUDE_CONFIG_FILE'))" 2>/dev/null; then
    echo -e "${GREEN}✅ Configuration file is valid JSON${NC}"
else
    echo -e "${RED}❌ Configuration file contains invalid JSON${NC}"
    if [ -f "${CLAUDE_CONFIG_FILE}${BACKUP_SUFFIX}" ]; then
        echo "Restoring backup..."
        cp "${CLAUDE_CONFIG_FILE}${BACKUP_SUFFIX}" "$CLAUDE_CONFIG_FILE"
    fi
    exit 1
fi

# Test the gateway
echo -e "${BLUE}🧪 Testing MCP Desktop Gateway...${NC}"
if timeout 5s mcp-desktop-gateway --help >/dev/null 2>&1; then
    echo -e "${GREEN}✅ MCP Desktop Gateway is working correctly${NC}"
else
    echo -e "${YELLOW}⚠️  Could not verify gateway functionality (this might be normal)${NC}"
fi

echo ""
echo -e "${GREEN}🎉 Installation Complete!${NC}"
echo ""
echo -e "${BLUE}Next Steps:${NC}"
echo "1. Restart Claude Desktop if it's currently running"
echo "2. Open Claude Desktop and start a new conversation"
echo "3. Try asking: 'What tools are available?' to verify the connection"
echo ""
echo -e "${BLUE}Useful Commands:${NC}"
echo "• Check available tools: 'List all available MCP tools'"
echo "• View system info: 'Show me system information'"
echo "• Run shell commands: 'Execute ls -la in my home directory'"
echo ""
echo -e "${YELLOW}Need help? Check the documentation:${NC}"
echo "• Getting Started: docs/examples/getting-started.md"
echo "• Full Documentation: docs/PROJECT.md"
echo "• NPM Package: https://www.npmjs.com/package/@bobmatnyc/mcp-desktop-gateway"