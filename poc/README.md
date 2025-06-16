# MCP Gateway Hello World POC

This is a minimal "Hello World" implementation of the MCP Gateway that demonstrates core functionality and proper integration with Claude Desktop.

## Features

### Tools
- **hello_world** - Greet users with service information
- **diagnostics** - Get system diagnostics and service status
- **echo** - Echo messages with optional metadata

### Resources
- **gateway://config** - View current service configuration
- **gateway://status** - Check service health and metrics
- **gateway://logs** - Access recent activity logs

### Prompts
- **quick_test** - Test all features with a single prompt
- **debug_info** - Gather comprehensive debug information
- **connector_template** - Generate template for new connectors

## Quick Start

### 1. Install Dependencies

```bash
# Ensure Python 3.8+ is installed
python --version

# Install MCP package
pip install mcp
```

### 2. Run the POC

```bash
# Using the run script (recommended)
python poc/run_hello_world.py

# Or directly
python poc/hello_world_poc.py
```

### 3. Add to Claude Desktop

The run script will create a `claude_desktop_config.json` file. Add this configuration to your Claude Desktop:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
**Linux**: `~/.config/Claude/claude_desktop_config.json`

Example configuration:
```json
{
  "mcpServers": {
    "mcp-gateway-hello-world": {
      "command": "python",
      "args": [
        "/absolute/path/to/mcp-gateway/poc/hello_world_poc.py"
      ]
    }
  }
}
```

### 4. Restart Claude Desktop

After adding the configuration, restart Claude Desktop completely.

## Testing the POC

### Quick Test
In Claude, type:
```
Use the quick_test prompt from mcp-gateway-hello-world
```

This will run through all features automatically.

### Manual Testing

1. **Test Tools**:
   ```
   Use the hello_world tool from mcp-gateway-hello-world
   Use the diagnostics tool with verbose=true
   Use the echo tool to echo "Hello MCP!" with include_metadata=true
   ```

2. **Test Resources**:
   ```
   Read the gateway://config resource
   Read the gateway://status resource
   Read the gateway://logs resource
   ```

3. **Test Prompts**:
   ```
   Use the debug_info prompt
   Use the connector_template prompt with connector_name="my_service"
   ```

## Troubleshooting

### Service Not Appearing in Claude

1. Check Claude Desktop logs:
   - macOS: `~/Library/Logs/Claude/mcp*.log`
   - Windows: `%APPDATA%\Claude\logs\mcp*.log`

2. Verify configuration path is absolute

3. Ensure Python is in PATH

### Common Errors

**"MCP package not installed"**
```bash
pip install mcp
```

**"Python 3.8+ required"**
```bash
# Install Python 3.8 or later
```

**Service starts but tools don't work**
- Check the logs for Python tracebacks
- Verify all imports are available
- Run diagnostics tool for more info

## Development

### Project Structure
```
poc/
├── hello_world_poc.py      # Main implementation
├── run_hello_world.py      # Run script with diagnostics
├── README.md               # This file
└── claude_desktop_config.json  # Generated config
```

### Extending the POC

To add new features:

1. **Add a Tool**: Update `_setup_tools()` in `hello_world_poc.py`
2. **Add a Resource**: Update `_setup_resources()`
3. **Add a Prompt**: Update `_setup_prompts()`

### Creating Your Own Connector

Use the `connector_template` prompt to generate a starting template for your own MCP connector.

## Success Criteria

✅ Service appears in Claude Desktop as "mcp-gateway-hello-world"
✅ All 3 tools are accessible and functional
✅ All 3 resources return valid data
✅ All 3 prompts provide useful templates
✅ Diagnostics show meaningful information
✅ Error handling provides helpful messages
✅ Logs capture all activity

## Next Steps

1. Test OAuth integration
2. Add memory/persistence features
3. Implement connector registry
4. Create production-ready error handling
5. Add performance monitoring

## References

- [MCP Protocol Documentation](https://github.com/anthropics/mcp)
- [Claude Desktop Integration Guide](../docs/PROJECT.md#claude-desktop-integration)
- [Main Project Documentation](../docs/PROJECT.md)