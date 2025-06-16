# MCP Desktop Gateway

[![npm version](https://img.shields.io/npm/v/@mcp/desktop-gateway.svg)](https://www.npmjs.com/package/@mcp/desktop-gateway)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Node.js 16+](https://img.shields.io/badge/node-16+-green.svg)](https://nodejs.org)

Universal MCP Gateway for Claude Desktop - Python-based bridge with built-in system automation tools.

## ✨ Features

- 🚀 **One-command installation** via NPM
- 🔧 **15 built-in tools** for system automation
- 🌐 **Cross-platform** support (macOS, Linux, Windows)
- 🔐 **Security features** including command filtering and timeouts
- 📦 **Zero configuration** - works out of the box
- ⚡ **Performance optimized** with automatic bytecode compilation
- 🔌 **Extensible** architecture for custom connectors

## 🚀 Quick Start

### Installation

```bash
# Install globally via NPM
npm install -g @mcp/desktop-gateway

# Configure Claude Desktop
mcp-desktop-gateway config

# Restart Claude Desktop
```

That's it! The gateway is now available in Claude Desktop with all built-in tools.

### Basic Usage

In Claude Desktop, you can now use commands like:

```
// Execute shell commands
execute_command(command="ls -la")

// Show system notifications (macOS)
system_notification(title="Hello", message="Task completed!")

// Get system information
get_system_info()

// List running applications (macOS)
get_running_apps()
```

## 🛠 Built-in Tools

### Shell Tools (Cross-platform)
- `execute_command` - Run shell commands safely
- `list_directory` - Browse the filesystem  
- `get_system_info` - Get system information

### AppleScript Tools (macOS only)
- `run_applescript` - Execute AppleScript code
- `system_notification` - Display system notifications
- `get_running_apps` - List running applications
- `control_app` - Control applications (activate, quit, hide)
- `get_clipboard` / `set_clipboard` - Clipboard management

### Gateway Management
- `list_connectors` - Show active connectors
- `gateway_health` - Check gateway status
- `hello_world` - Test the connection

## 📋 Resources & Prompts

The gateway also provides:
- **10 resources** for accessing system information
- **8 prompts** for guided assistance and help

## 🔧 Configuration

Create a custom configuration at `config/config.yaml`:

```yaml
server:
  name: "mcp-desktop-gateway"
  version: "0.1.0"
  log_level: "INFO"

connectors:
  - name: shell
    enabled: true
    config:
      timeout: 30
      working_directory: "/path/to/projects"
```

## 🧪 Development

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/mcp-desktop-gateway/mcp-desktop-gateway
cd mcp-desktop-gateway

# Set up development environment
make dev

# Run in development mode  
make run

# Run tests
make test
```

### Development Commands

```bash
make help         # Show all commands
make run          # Run gateway in dev mode
make test         # Run test suite
make test-npm     # Test NPM package
make logs         # View logs
make clean        # Clean build artifacts

# Configuration management (3 simple commands)
make use-local-code  # Use MCP Gateway from local Python code
make use-npm-package # Use MCP Gateway from NPM package  
make use-original    # Restore your original config (eva-mcp-bridge, etc)
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
python scripts/version.py tag
```

## 🏗 Architecture

```
┌─────────────────┐         ┌──────────────────────┐         ┌─────────────────┐
│                 │   MCP   │                      │  HTTP   │                 │
│  Claude Desktop │ ◄─────► │    MCP Gateway       │ ◄─────► │ Custom          │
│                 │  stdio  │    (Python)          │ (opt)   │ Connectors      │
└─────────────────┘         └──────────────────────┘         └─────────────────┘
```

## 🔒 Security

- Command filtering prevents dangerous operations
- Configurable timeouts (max 60 seconds)
- Environment variable filtering removes sensitive data
- No sudo or administrative commands allowed
- Sandboxed execution environment

## 🐛 Troubleshooting

### Common Issues

1. **Python not found**
   ```bash
   # macOS
   brew install python3
   
   # Ubuntu/Debian  
   sudo apt install python3 python3-pip python3-venv
   
   # Windows
   # Download from python.org
   ```

2. **Permission errors**
   ```bash
   sudo npm install -g @mcp/desktop-gateway
   ```

3. **Gateway not connecting**
   - Check logs: `~/Library/Logs/Claude/mcp-server-mcp-desktop-gateway.log`
   - Run in debug mode: `MCP_DEV_MODE=true mcp-desktop-gateway`

## 📚 Documentation

- [Project Documentation](docs/PROJECT.md) - Detailed architecture and API
- [Development Guide](DEVELOPMENT.md) - Development workflow
- [Changelog](CHANGELOG.md) - Version history
- [Examples](examples/) - Example connectors

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📈 Roadmap

- **v0.2.0** - External connector HTTP API, connector marketplace
- **v0.3.0** - Authentication system, rate limiting, metrics
- **v1.0.0** - Stable API, production ready, enterprise features

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

Built for use with [Claude Desktop](https://claude.ai) and the [Model Context Protocol](https://modelcontextprotocol.io).

## 📧 Support

- 📖 [Documentation](https://github.com/mcp-desktop-gateway/mcp-desktop-gateway/wiki)
- 🐛 [Issue Tracker](https://github.com/mcp-desktop-gateway/mcp-desktop-gateway/issues)
- 💬 [Discussions](https://github.com/mcp-desktop-gateway/mcp-desktop-gateway/discussions)
- 📧 [Email](mailto:support@mcp-desktop-gateway.org)