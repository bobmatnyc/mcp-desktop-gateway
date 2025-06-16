# MCP Gateway Development Guide

## Quick Start

```bash
# 1. Initial setup
make dev

# 2. Run in development mode
make run

# 3. Test NPM package
make test-npm
```

## Development Workflow

### 1. **Local Python Development**

```bash
# Activate virtual environment
source venv/bin/activate

# Run directly
python run_mcp_gateway.py

# Run with debug mode
MCP_DEV_MODE=true python run_mcp_gateway.py

# Run simple version for testing
python run_mcp_gateway_simple.py
```

### 2. **NPM Package Development**

```bash
# Install locally for testing
npm link

# Test the installed package
mcp-gateway

# Test specific commands
mcp-gateway setup
mcp-gateway config
```

### 3. **Testing in Claude Desktop**

Three simple commands to switch between configurations:

```bash
# Use local Python code (for development)
make use-local-code

# Use NPM package (test distribution)
make use-npm-package

# Return to your original config
make use-original
```

Your original configuration (eva-mcp-bridge, etc.) is automatically saved the first time you switch to local or NPM mode.

### 4. **Making Changes**

1. **Edit Python code** in `src/`
2. **Test locally**: `make run`
3. **Test NPM package**: `make test-npm`
4. **Check logs**: `make logs`

### 5. **Common Tasks**

```bash
# Watch logs in real-time
make watch-logs

# Clean everything
make clean

# Run tests
make test

# Build distribution package
make package
```

## Project Structure

```
mcp-gateway/
├── src/                    # Python source code
│   ├── core/              # Core functionality
│   └── connectors/        # Built-in connectors
├── lib/                   # NPM wrapper
│   └── cli.js            # Node.js CLI
├── config/               # Configuration files
│   ├── config.yaml       # Production config
│   └── config.dev.yaml   # Development config
├── venv/                 # Python virtual environment
├── run_mcp_gateway.py    # Main entry point
└── Makefile             # Development commands
```

## Testing Checklist

- [ ] Python runs directly: `python run_mcp_gateway.py`
- [ ] NPM package installs: `npm install`
- [ ] CLI works: `mcp-gateway help`
- [ ] Connects to Claude Desktop
- [ ] All tools appear in Claude
- [ ] Tools execute correctly
- [ ] Resources load properly
- [ ] Prompts work as expected

## Debugging

1. **Check logs**: `make logs`
2. **Enable debug mode**: `MCP_DEV_MODE=true`
3. **Test simple version**: `make run-simple`
4. **Verify Python path**: `which python3`

## Release Process

1. Test thoroughly in development
2. Update version in `package.json`
3. Build package: `make package`
4. Test package: `npm install mcp-gateway-*.tgz`
5. Publish: `npm publish`