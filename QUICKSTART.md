# MCP Desktop Gateway Quick Reference

## Installation (One Time)

```bash
npm install -g @mcp/desktop-gateway
mcp-desktop-gateway config
# Restart Claude Desktop
```

## Available Tools

### 🖥️ Shell Commands
```
execute_command(command="ls -la")
execute_command(command="pwd")
execute_command(command="ps aux | grep python")

list_directory(path="/Users/me/Documents")
list_directory(path=".", show_hidden=true)

get_system_info()
```

### 🍎 macOS Automation
```
system_notification(title="Done!", message="Task completed")

run_applescript(script='tell app "Safari" to activate')

get_running_apps()

control_app(app_name="Finder", action="activate")
control_app(app_name="TextEdit", action="quit")

get_clipboard()
set_clipboard(text="Hello from MCP Gateway!")
```

### 🔧 Gateway Management
```
list_connectors()
list_connectors(include_disabled=true)

gateway_health()

hello_world(name="Claude")
```

## Resources

Access system information:
```
// View environment variables
Read: shell://env

// Current directory info  
Read: shell://cwd

// Running applications (macOS)
Read: applescript://apps

// Gateway configuration
Read: gateway://utils/config
```

## Prompts

Get help and guidance:
```
// Shell help
Prompt: shell_help

// AppleScript help
Prompt: applescript_help

// Gateway troubleshooting
Prompt: troubleshoot_gateway
```

## Tips

1. **Command Safety**: Dangerous commands are blocked
2. **Timeouts**: Commands timeout after 30s (configurable)
3. **Output Limits**: Large outputs are truncated
4. **Platform**: AppleScript tools are macOS only

## Troubleshooting

```bash
# Check if running
mcp-gateway

# View logs
tail -f ~/Library/Logs/Claude/mcp-server-mcp-gateway.log

# Debug mode
MCP_DEV_MODE=true mcp-gateway
```

## Development

```bash
# Clone and setup
git clone https://github.com/mcp-gateway/mcp-gateway
cd mcp-gateway
make dev

# Run locally
make run

# Switch Claude to dev mode
make switch-dev
```