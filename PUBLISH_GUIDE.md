# Publishing Guide for @bobmatnyc/mcp-desktop-gateway

This guide walks through publishing the MCP Desktop Gateway to npm under your personal scope.

## Prerequisites ✅ Complete

- [x] Package updated to `@bobmatnyc/mcp-desktop-gateway`
- [x] All references updated in documentation
- [x] Version set to 1.0.0
- [x] Package.json configured with proper scripts and files
- [x] Tests passing
- [x] Package build validated with `npm pack --dry-run`

## Ready to Publish

### Step 1: Login to npm

```bash
# Login to npm (you'll need to do this)
npm login

# Verify you're logged in as bobmatnyc
npm whoami
```

### Step 2: Verify Scope Access

Since this is your first scoped package (`@bobmatnyc/*`), npm will automatically create the scope when you publish.

### Step 3: Final Pre-publish Checks

```bash
# Run final tests
npm run test:local

# Check package contents
npm pack --dry-run

# Check if package name is available (optional)
npm view @bobmatnyc/mcp-desktop-gateway
```

### Step 4: Publish the Package

```bash
# Publish with public access (required for scoped packages)
npm publish --access public

# Or if you want to test first with a tag
npm publish --access public --tag beta
```

### Step 5: Verify Publication

```bash
# Check your published package
npm view @bobmatnyc/mcp-desktop-gateway

# Test installation
npm install -g @bobmatnyc/mcp-desktop-gateway
```

## Package Details

**Package Name**: `@bobmatnyc/mcp-desktop-gateway`  
**Version**: `1.0.0`  
**Size**: ~445 KB (1.5 MB unpacked)  
**Files**: 158 files including:
- Python source code and bytecode
- Configuration files
- CLI wrapper
- Documentation

## Installation Command

Once published, users can install with:

```bash
npm install -g @bobmatnyc/mcp-desktop-gateway
```

## Claude Desktop Configuration

After installation, users add to their Claude Desktop config:

```json
{
  "mcpServers": {
    "mcp-desktop-gateway": {
      "command": "mcp-desktop-gateway"
    }
  }
}
```

## Version Management

For future releases:

```bash
# Patch release (1.0.0 → 1.0.1)
python scripts/version.py bump patch
npm publish --access public

# Minor release (1.0.0 → 1.1.0)  
python scripts/version.py bump minor
npm publish --access public

# Major release (1.0.0 → 2.0.0)
python scripts/version.py bump major
npm publish --access public
```

## Repository Setup

You may also want to:

1. **Create GitHub Repository**:
   ```bash
   # Create repo at: https://github.com/bobmatnyc/mcp-desktop-gateway
   git remote add origin https://github.com/bobmatnyc/mcp-desktop-gateway.git
   git push -u origin main --tags
   ```

2. **Update Package URLs**: Package.json already points to your GitHub repo

3. **Add README Badge**: Update npm badge URL in README.md after publishing

## Troubleshooting

### Common Issues

1. **401 Unauthorized**: Run `npm login` first
2. **Scope Permission**: First publish automatically creates scope
3. **Package Already Exists**: Check if name is taken with `npm view`
4. **Size Warnings**: Package is ~445KB, within npm limits

### Verification Commands

```bash
# Check auth status
npm whoami

# Validate package.json
npm pkg fix

# Check for issues
npm audit

# Test package locally
npm link
mcp-desktop-gateway --help
```

## Success Metrics

After publishing, you'll have:

✅ **Professional npm package** at `@bobmatnyc/mcp-desktop-gateway`  
✅ **Global CLI command** `mcp-desktop-gateway`  
✅ **Automatic Python setup** on installation  
✅ **Claude Desktop integration** ready  
✅ **Production-ready** MCP Gateway with 15 built-in tools

The package includes comprehensive connectors for shell automation, AppleScript (macOS), and gateway utilities, making it a complete solution for Claude Desktop automation.

## Next Steps After Publishing

1. **Test installation** from npm
2. **Update any external references** to use published package
3. **Share with community** via GitHub/npm
4. **Monitor download stats** on npmjs.com