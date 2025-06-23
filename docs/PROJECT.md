# MCP Desktop Gateway Project Documentation

**Version**: 1.1.0 (Stable)  
**License**: MIT  
**Status**: Active Development  
**NPM Package**: `@bobmatnyc/mcp-desktop-gateway`

## Overview

MCP Desktop Gateway is a Python-based Model Context Protocol (MCP) server that acts as a universal bridge between Claude Desktop and various tools and services. Distributed as an NPM package for easy installation, it provides built-in system automation capabilities, an advanced prompt training system, and an extensible architecture for custom connectors.

## Key Features

- 🚀 **Easy Installation**: One-command setup via NPM
- 🔧 **Built-in Tools**: Shell commands, AppleScript automation, and more
- 🧠 **Automatic Prompt Training**: LangChain-powered continuous improvement system
- 🎯 **Smart Feedback Learning**: Automatically improves based on user interactions and errors
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
│   ├── connectors/            # Built-in connectors
│   │   ├── shell/             # System command execution
│   │   ├── applescript/       # macOS automation
│   │   ├── hello_world/       # Example connector
│   │   └── gateway_utils/     # Gateway management
│   └── prompt_training/       # Prompt training system
│       ├── feedback_collector.py  # Feedback collection
│       ├── prompt_manager.py      # Version control
│       ├── prompt_trainer.py      # LangChain training
│       ├── auto_trainer.py        # Automatic training
│       ├── evaluation.py          # Testing framework
│       ├── integration.py         # MCP Gateway integration
│       ├── cli.py                 # Command line interface
│       └── models.py              # Training data models
├── prompt_training/           # Training data and config
│   ├── configs/              # Configuration files
│   ├── feedback/             # Collected feedback
│   ├── versions/             # Prompt versions
│   └── evaluation/           # Test suites and results
├── lib/                       # NPM wrapper
│   └── cli.js                # Node.js CLI entry point
├── config/                    # Configuration files
│   ├── config.yaml           # Default configuration
│   └── config.dev.yaml       # Development configuration
├── docs/                      # Documentation
│   ├── PROJECT.md            # This file
│   ├── ARCHITECTURE.md       # System architecture
│   ├── INSTRUCTIONS.md       # Development guidelines
│   └── WORKFLOW.md           # Development workflow
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
npm install -g @bobmatnyc/mcp-desktop-gateway
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
- **Purpose**: Script writing and quick command execution
- **Security**: Command filtering, timeout protection

### 2. AppleScript Connector (macOS)
- **Tools**: `run_applescript`, `system_notification`, `control_app`, `get_clipboard`, `set_clipboard`
- **Sub-connectors**: Safari, Contacts, Messages, Finder, Terminal
- **Resources**: `applescript://apps`, `applescript://system`
- **Purpose**: macOS automation and script execution with visual feedback
- **Platform**: macOS only

### 3. Prompt Training Connector
- **Tools**: `rate_response`, `suggest_improvement`, `report_issue`, `get_training_status`, `trigger_training`, `get_training_history`
- **Purpose**: Automatic prompt improvement using LangChain and ML
- **Features**: 
  - Automatic feedback collection from user interactions
  - Intelligent training approach selection (few-shot, reinforcement, meta-prompt, adversarial)
  - Continuous monitoring and improvement
  - Safe deployment with thorough evaluation

### 4. Gateway Utils
- **Tools**: `list_connectors`, `gateway_health`, `reload_config`
- **Resources**: `gateway://utils/config`, `gateway://utils/manifest`
- **Purpose**: Gateway management and diagnostics

### 5. Hello World
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

For prompt training features, also set your OpenAI API key:
```bash
export OPENAI_API_KEY=your-api-key
```

## Prompt Training System

The MCP Desktop Gateway includes an advanced prompt training system that automatically improves prompts based on user feedback and error patterns.

### Key Features

- **Automatic Feedback Collection**: Captures user ratings, errors, and success metrics from all interactions
- **Intelligent Training**: Four training approaches automatically selected based on feedback patterns:
  - **Few-shot Learning**: For prompts with many successful examples
  - **Reinforcement Learning**: For fixing low ratings and specific issues  
  - **Meta-prompt Optimization**: For incorporating user suggestions
  - **Adversarial Training**: For handling edge cases and robustness
- **Continuous Monitoring**: Checks all prompts hourly for training opportunities
- **Safe Deployment**: Thorough evaluation and optional auto-deployment with safety checks

### Training Triggers

The system automatically triggers training when:
- **Error Rate > 20%** → Uses adversarial training for robustness
- **Average Rating < 0.6** → Uses reinforcement learning for satisfaction
- **50+ Feedback Items** → Uses few-shot learning to leverage accumulated knowledge
- **3+ User Suggestions** → Uses meta-prompt optimization to incorporate feedback

### CLI Commands

```bash
# Initialize prompt training system
python -m prompt_training.cli init

# Check automatic training status
python -m prompt_training.cli train status

# Start automatic training service
python -m prompt_training.cli train start-auto

# Manually trigger training
python -m prompt_training.cli train trigger my_prompt --approach few_shot

# View training history
python -m prompt_training.cli train history my_prompt

# Export improved prompts
python -m prompt_training.cli prompt export ./external_prompts
```

### Configuration

Enable automatic training by adding to your configuration:

```yaml
connectors:
  - name: prompt_training
    type: prompt_training
    enabled: true
    config:
      auto_collect: true
      collect_errors: true
      collect_success: true
      prompt_improvement_enabled: true
      openai_api_key: ${OPENAI_API_KEY}
      config_path: "prompt_training/configs/auto_training.json"
```

For detailed documentation, see [`src/prompt_training/README.md`](../src/prompt_training/README.md).

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
2. **Permission errors**: Use `sudo npm install -g @bobmatnyc/mcp-desktop-gateway`
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