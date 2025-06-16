# MCP Desktop Gateway

Universal MCP (Model Context Protocol) Gateway for Claude Desktop - a Python-based bridge with built-in tools for system automation.

## Features

- 🔧 **Built-in Connectors**: Shell commands, AppleScript automation, and more
- 🌐 **Extensible Architecture**: Add custom connectors via HTTP API
- 🚀 **Easy Installation**: One-command setup via NPM
- 🔐 **Security Features**: Command filtering, timeouts, and sandboxing
- 📦 **Zero Config**: Works out of the box with sensible defaults

## Quick Start

### 1. Install via NPM

```bash
npm install -g @bobmatnyc/mcp-desktop-gateway
```

This will:
- Install the MCP Gateway CLI
- Set up a Python virtual environment
- Install all Python dependencies automatically

### 2. Configure Claude Desktop

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "mcp-desktop-gateway": {
      "command": "mcp-desktop-gateway"
    }
  }
}
```

Or use the built-in config helper:

```bash
mcp-desktop-gateway config
```

### 3. Restart Claude Desktop

The gateway is now available with these built-in tools:

#### Shell Tools
- `execute_command` - Run shell commands safely
- `list_directory` - Browse the filesystem
- `get_system_info` - Get system information

#### AppleScript Tools (macOS only)
- `run_applescript` - Execute AppleScript code
- `system_notification` - Show notifications
- `control_app` - Control applications
- `get_clipboard`/`set_clipboard` - Manage clipboard

#### Gateway Tools
- `list_connectors` - List active connectors
- `gateway_health` - Check gateway status
- `hello_world` - Test the connection

## Usage Examples

In Claude Desktop, you can now:

```
// List files in current directory
execute_command(command="ls -la")

// Show a notification (macOS)
system_notification(title="Task Complete", message="Your build finished!")

// Get system information
get_system_info()
```

## Advanced Usage

### Custom Configuration

Create a `config/config.yaml` file:

```yaml
server:
  name: "mcp-desktop-gateway"
  version: "1.0.0"
  log_level: "INFO"

connectors:
  - name: shell
    enabled: true
    config:
      timeout: 30
      working_directory: "/Users/me/projects"
```

### Adding Custom Connectors

MCP Gateway supports external connectors via HTTP. See the [documentation](https://github.com/user/mcp-desktop-gateway) for details on creating custom connectors.

## Troubleshooting

### Python Not Found

MCP Gateway requires Python 3.8+. Install it from:
- macOS: `brew install python3`
- Ubuntu/Debian: `sudo apt install python3 python3-pip python3-venv`
- Windows: Download from [python.org](https://python.org)

### Permission Errors

If you get permission errors during installation:

```bash
sudo npm install -g @bobmatnyc/mcp-desktop-gateway
```

### Gateway Not Connecting

1. Check the logs: `~/Library/Logs/Claude/mcp-server-mcp-desktop-gateway.log`
2. Verify Python path: `mcp-desktop-gateway setup`
3. Test manually: `mcp-desktop-gateway`

## Development

```bash
# Clone the repository
git clone https://github.com/user/mcp-desktop-gateway
cd mcp-desktop-gateway

# Install in development mode
npm install
npm run setup

# Run tests
npm test
```

## License

MIT - See LICENSE file for details

## Contributing

Contributions are welcome! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

## Support

- 📖 [Documentation](https://github.com/user/mcp-desktop-gateway/wiki)
- 🐛 [Issue Tracker](https://github.com/user/mcp-desktop-gateway/issues)
- 💬 [Discussions](https://github.com/user/mcp-desktop-gateway/discussions)