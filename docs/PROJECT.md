# MCP Desktop Gateway Project Documentation

**Version**: 0.1.0 (Alpha)  
**License**: MIT  
**Status**: Active Development  
**NPM Package**: `@mcp/desktop-gateway`

## Overview

MCP Desktop Gateway is a Python-based Model Context Protocol (MCP) server that acts as a universal bridge between Claude Desktop and various tools and services. Distributed as an NPM package for easy installation, it provides built-in system automation capabilities and an extensible architecture for custom connectors.

## Key Features

- 🚀 **Easy Installation**: One-command setup via NPM
- 🔧 **Built-in Tools**: Shell commands, AppleScript automation, and more
- 🌐 **Extensible**: Support for custom connectors via HTTP API
- 🔐 **Secure**: Command filtering, timeouts, and sandboxing
- 📦 **Cross-platform**: Works on macOS, Linux, and Windows
- ⚡ **Performance**: Automatic bytecode compilation

## Architecture

```
┌─────────────────┐         ┌──────────────────────┐         ┌─────────────────┐
│                 │   MCP   │                      │  HTTP   │                 │
│  Claude Desktop │ ◄─────► │ MCP Desktop Gateway  │ ◄─────► │ Custom          │
│                 │  stdio  │    (Python)          │ (opt)   │ Connectors      │
└─────────────────┘         └──────────────────────┘         └─────────────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    │                │                │
              ┌─────▼─────┐   ┌─────▼─────┐   ┌─────▼─────┐
              │   Shell   │   │AppleScript│   │   Hello   │
              │ Connector │   │ Connector │   │   World   │
              └───────────┘   └───────────┘   └───────────┘
```

## Project Structure

```
mcp-desktop-gateway/
├── src/                        # Python source code
│   ├── core/                   # Core functionality
│   │   ├── base_connector.py   # Base connector class
│   │   ├── config.py          # Configuration management
│   │   ├── models.py          # Data models
│   │   └── registry.py        # Connector registry
│   └── connectors/            # Built-in connectors
│       ├── shell/             # System command execution
│       ├── applescript/       # macOS automation
│       ├── hello_world/       # Example connector
│       └── gateway_utils/     # Gateway management
├── lib/                       # NPM wrapper
│   └── cli.js                # Node.js CLI entry point
├── config/                    # Configuration files
│   ├── config.yaml           # Default configuration
│   └── config.dev.yaml       # Development configuration
├── docs/                      # Documentation
├── tests/                     # Test suite
├── scripts/                   # Utility scripts
│   └── version.py            # Version management
├── run_mcp_gateway.py        # Main Python entry point
├── package.json              # NPM package definition
├── requirements.txt          # Python dependencies
├── VERSION                   # Version file
├── CHANGELOG.md             # Version history
├── Makefile                 # Development commands
└── README.md               # User documentation
```

## Installation

### Via NPM (Recommended)

```bash
npm install -g @mcp/desktop-gateway
```

### Development Setup

```bash
# Clone repository
git clone https://github.com/mcp-desktop-gateway/mcp-desktop-gateway
cd mcp-desktop-gateway

# Set up development environment
make dev

# Run in development mode
make run
```

## Built-in Connectors

### 1. Shell Connector
- **Tools**: `execute_command`, `list_directory`, `get_system_info`
- **Resources**: `shell://env`, `shell://cwd`
- **Security**: Command filtering, timeout protection

### 2. AppleScript Connector (macOS)
- **Tools**: `run_applescript`, `system_notification`, `control_app`, `get_clipboard`, `set_clipboard`
- **Resources**: `applescript://apps`, `applescript://system`
- **Platform**: macOS only

### 3. Gateway Utils
- **Tools**: `list_connectors`, `gateway_health`, `reload_config`
- **Resources**: `gateway://utils/config`, `gateway://utils/manifest`
- **Purpose**: Gateway management and diagnostics

### 4. Hello World
- **Tools**: `hello_world`, `gateway_info`, `echo`
- **Resources**: `gateway://hello/status`, `gateway://hello/logs`
- **Purpose**: Example and testing

## Claude Desktop Integration

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "mcp-desktop-gateway": {
      "command": "mcp-desktop-gateway"
    }
  }
}
```

## Development Workflow

### Commands

```bash
make dev          # Set up development environment
make run          # Run in development mode
make test         # Run tests
make test-npm     # Test NPM package
make logs         # View logs
make package      # Build NPM package
```

### Version Management

```bash
# Show current version
python scripts/version.py show

# Bump version
python scripts/version.py bump patch    # 0.1.0 → 0.1.1
python scripts/version.py bump minor    # 0.1.0 → 0.2.0
python scripts/version.py bump major    # 0.1.0 → 1.0.0

# Create release tag
python scripts/version.py tag "Release message"
```

## API Reference

### Tool Definition

```python
class ToolDefinition:
    name: str                  # Unique tool identifier
    description: str           # Human-readable description
    input_schema: dict        # JSON Schema for parameters
```

### Resource Definition

```python
class ResourceDefinition:
    uri: str                  # Resource URI (e.g., "shell://env")
    name: str                 # Display name
    description: str          # Description
    mimeType: str            # Content type
```

### Creating Custom Connectors

1. Inherit from `BaseConnector`
2. Implement required methods:
   - `get_tools()` - Return tool definitions
   - `execute_tool()` - Handle tool execution
   - `get_resources()` - Return resource definitions (optional)
   - `read_resource()` - Handle resource reads (optional)
   - `get_prompts()` - Return prompt definitions (optional)
   - `execute_prompt()` - Handle prompt execution (optional)

## Performance

- Automatic Python bytecode compilation on install
- Optional PyPy support for 2-10x performance
- Nuitka compilation available for binary distribution

## Security

- Command filtering for dangerous operations
- Timeout protection (configurable, max 60s)
- Environment variable filtering
- No sudo/admin commands allowed
- Sandboxed execution environment

## Troubleshooting

### Common Issues

1. **Python not found**: Install Python 3.8+ 
2. **Permission errors**: Use `sudo npm install -g @mcp/desktop-gateway`
3. **Connection failed**: Check logs at `~/Library/Logs/Claude/mcp-server-mcp-desktop-gateway.log`

### Debug Mode

```bash
# Run with debug logging
MCP_DEV_MODE=true mcp-desktop-gateway

# Check logs
make logs
make watch-logs
```

## Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Make changes and test: `make test`
4. Update version: `python scripts/version.py bump patch`
5. Commit: `git commit -am 'Add amazing feature'`
6. Push: `git push origin feature/amazing-feature`
7. Create Pull Request

## Roadmap

### Version 0.2.0
- [ ] External connector HTTP API
- [ ] Connector marketplace
- [ ] Web UI for configuration

### Version 0.3.0
- [ ] Authentication system
- [ ] Rate limiting
- [ ] Metrics and monitoring

### Version 1.0.0
- [ ] Stable API
- [ ] Production ready
- [ ] Enterprise features

## License

MIT License - see LICENSE file for details.

## Support

- 📖 [Documentation](https://github.com/mcp-desktop-gateway/mcp-desktop-gateway/wiki)
- 🐛 [Issue Tracker](https://github.com/mcp-desktop-gateway/mcp-desktop-gateway/issues)
- 💬 [Discussions](https://github.com/mcp-desktop-gateway/mcp-desktop-gateway/discussions)
- 📧 [Email Support](mailto:support@mcp-gateway.org)