# Issue: MCP Gateway Hello World POC

**Issue Type:** Feature/POC  
**Priority:** High  
**Milestone:** v0.1.0-poc  

## Summary

Create a minimal "Hello World" MCP Gateway implementation that demonstrates core functionality with proper service identification, diagnostics, resources, and prompts capabilities visible in Claude Desktop.

## Background

We need a working POC that:
1. Successfully registers with Claude Desktop as a distinct, identifiable service
2. Implements basic MCP protocol features (tools, resources, prompts)
3. Provides diagnostic capabilities for troubleshooting
4. Serves as a foundation for future connector development

## Requirements

### 1. Service Identification
- [ ] Unique service name: "MCP Gateway Hello World"
- [ ] Clear service description visible in Claude Desktop
- [ ] Proper server metadata in MCP responses
- [ ] Version information (v0.1.0-poc)

### 2. Core MCP Features

#### Tools Implementation
- [ ] `hello_world` - Basic greeting tool
- [ ] `diagnostics` - System diagnostics tool
- [ ] `echo` - Echo back user input with metadata

#### Resources Implementation
- [ ] `gateway://config` - Current configuration
- [ ] `gateway://status` - Service status and health
- [ ] `gateway://logs` - Recent activity logs

#### Prompts Implementation
- [ ] `quick_test` - Pre-configured test prompt
- [ ] `debug_info` - Diagnostic information prompt
- [ ] `connector_template` - Template for new connectors

### 3. Diagnostics & Monitoring
- [ ] Startup diagnostics with clear success/failure messages
- [ ] Request/response logging with timestamps
- [ ] Error handling with descriptive messages
- [ ] Performance metrics (response times)

### 4. Configuration
- [ ] Simple YAML/JSON configuration
- [ ] Environment variable support
- [ ] Clear error messages for missing config

## Success Criteria

1. **Claude Desktop Integration**
   - Service appears in Claude with clear identification
   - All tools, resources, and prompts are accessible
   - No errors in MCP logs during normal operation

2. **Developer Experience**
   - Single command startup: `python run_hello_world.py`
   - Clear console output showing service status
   - Helpful error messages for common issues

3. **Functionality**
   - All tools execute successfully
   - Resources return valid data
   - Prompts provide useful templates

## Implementation Plan

### Phase 1: Basic Structure
1. Create minimal MCP server (`hello_world_poc.py`)
2. Implement server metadata and identification
3. Add basic logging infrastructure

### Phase 2: Core Features
1. Implement three tools (hello_world, diagnostics, echo)
2. Add three resources (config, status, logs)
3. Create three prompts (quick_test, debug_info, connector_template)

### Phase 3: Integration & Testing
1. Create startup script with diagnostics
2. Add Claude Desktop configuration template
3. Test all features in Claude Desktop
4. Document any issues and solutions

### Phase 4: Documentation
1. Create POC README with setup instructions
2. Add troubleshooting guide
3. Include example Claude Desktop config
4. Create demo video/screenshots

## Technical Specifications

### File Structure
```
mcp-gateway/
├── poc/
│   ├── hello_world_poc.py      # Main POC implementation
│   ├── run_hello_world.py      # Startup script
│   ├── config.yaml             # Configuration
│   └── README.md               # POC documentation
```

### Example Tool Response
```json
{
  "name": "hello_world",
  "description": "Greet the user with service information",
  "inputSchema": {
    "type": "object",
    "properties": {
      "name": {
        "type": "string",
        "description": "Name to greet"
      }
    }
  }
}
```

### Example Diagnostic Output
```
=== MCP Gateway Hello World POC ===
Version: v0.1.0-poc
Status: Starting...
✓ Configuration loaded
✓ MCP server initialized
✓ Tools registered: 3
✓ Resources registered: 3
✓ Prompts registered: 3
✓ Server ready on stdio
Service ID: mcp-gateway-hello-world
Waiting for requests...
```

## Dependencies
- Python 3.8+
- mcp package
- pyyaml (for config)
- No external services (pure local implementation)

## Testing Checklist
- [ ] Service starts without errors
- [ ] Appears in Claude Desktop with correct name
- [ ] All tools executable from Claude
- [ ] All resources accessible from Claude
- [ ] All prompts available in Claude
- [ ] Diagnostics show meaningful information
- [ ] Error handling works correctly
- [ ] Logs are readable and helpful

## Notes
- Keep implementation minimal and focused
- Prioritize clear error messages and diagnostics
- Use this as a template for future connectors
- Document any Claude Desktop quirks discovered

## References
- MCP Protocol Documentation
- Claude Desktop Integration Guide
- PROJECT.md - Architecture overview