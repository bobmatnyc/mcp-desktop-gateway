# MCP Gateway Development Workflow

**Version**: 1.1  
**Updated**: 2025-06-23  

This document defines the development workflow for the MCP Gateway project, including prompt training system development.

## 🔁 Git Workflow

### Branch Strategy

We use a simplified Git Flow:

- `main` - Stable, release-ready code
- `develop` - Integration branch for features
- `feature/*` - New features
- `fix/*` - Bug fixes
- `chore/*` - Maintenance tasks
- `docs/*` - Documentation updates

### Commit Convention

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

[optional body]

[optional footer(s)]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Code style (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding tests
- `chore`: Maintenance tasks

**Examples:**
```bash
feat(shell): add timeout configuration
feat(training): add automatic prompt training system
fix(gateway): handle connection errors properly
docs(readme): update installation instructions
chore(deps): update mcp to 0.2.0
```

### Development Flow

```bash
# 1. Start from develop
git checkout develop
git pull origin develop

# 2. Create feature branch
git checkout -b feature/external-connectors

# 3. Make changes and commit
git add .
git commit -m "feat(core): add HTTP connector support"

# 4. Keep up to date
git fetch origin
git rebase origin/develop

# 5. Push and create PR
git push -u origin feature/external-connectors
```

## 📋 Issue Management

### Issue Types

Use labels to categorize:

- `type:bug` - Something broken
- `type:feature` - New functionality
- `type:enhancement` - Improve existing feature
- `type:docs` - Documentation
- `type:test` - Testing improvements

### Priority Labels

- `priority:critical` - Show stopper
- `priority:high` - Important for release
- `priority:medium` - Should have
- `priority:low` - Nice to have

### Component Labels

- `component:core` - Core gateway functionality
- `component:connector` - Connector-related
- `component:training` - Prompt training system
- `component:cli` - NPM/CLI wrapper
- `component:docs` - Documentation

### Issue Template

```markdown
## Description
Brief description of the issue

## Expected Behavior
What should happen

## Actual Behavior
What actually happens

## Steps to Reproduce
1. Install gateway
2. Run command X
3. See error

## Environment
- OS: macOS 14.0
- Python: 3.11
- Node: 18.0
- MCP Gateway: 1.0.0

## Additional Context
Any other relevant information
```

## 🚀 Release Process

### Version Bumping

Use semantic versioning:

```bash
# Patch release (0.1.0 → 0.1.1)
make version-bump-patch

# Minor release (0.1.0 → 0.2.0)
make version-bump-minor

# Major release (0.1.0 → 1.0.0)
make version-bump-major
```

### Release Checklist

1. **Update version**
   ```bash
   python scripts/version.py bump minor
   ```

2. **Update CHANGELOG.md**
   - Add new version section
   - Move unreleased items
   - Credit contributors

3. **Run full test suite**
   ```bash
   make test
   make test-npm
   # Test prompt training system
   python -m prompt_training.cli init
   python -m prompt_training.cli train status
   ```

4. **Create release branch**
   ```bash
   git checkout -b release/0.2.0
   ```

5. **Create PR and merge**

6. **Tag release**
   ```bash
   git checkout main
   git pull origin main
   python scripts/version.py tag "Release v0.2.0"
   git push origin --tags
   ```

7. **Publish to NPM**
   ```bash
   npm publish --access public
   ```

8. **Create GitHub Release**
   - Use tag v0.2.0
   - Copy CHANGELOG section
   - Attach built package

## 🧪 Testing Requirements

### Before Every Commit

```bash
# Run Python tests
make test

# Test NPM package
make test-npm

# Check in Claude Desktop
make switch-dev
```

### Test Categories

1. **Unit Tests** - Individual components
2. **Integration Tests** - Component interactions
3. **E2E Tests** - Full gateway with Claude Desktop
4. **Performance Tests** - Response times, memory usage

### CI Requirements

All PRs must pass:
- ✅ Python tests (pytest)
- ✅ Linting (flake8)
- ✅ Type checking (mypy)
- ✅ NPM package build
- ✅ Documentation build

## 📝 Documentation Workflow

### Documentation Updates

1. **Code changes** → Update docstrings
2. **API changes** → Update PROJECT.md
3. **User-facing changes** → Update README.md
4. **New features** → Add to QUICKSTART.md
5. **Breaking changes** → Update migration guide

### Documentation Review

- All PRs with code changes need documentation review
- Examples must be tested and working
- Screenshots for UI changes

## 🔧 Development Setup

### Local Development

```bash
# Initial setup
make dev

# Run gateway
make run

# Watch logs
make watch-logs

# Switch configs
make switch-dev    # Development mode
make switch-npm    # NPM package mode
```

### Debug Workflow

1. **Enable debug logging**
   ```bash
   MCP_DEV_MODE=true make run
   ```

2. **Check logs**
   ```bash
   make logs
   make watch-logs
   ```

3. **Test specific connector**
   ```python
   # In Python REPL
   from src.connectors.shell.connector import ShellConnector
   connector = ShellConnector("shell", {})
   tools = connector.get_tools()
   ```

## 🏗️ Architecture Guidelines

### Adding New Connectors

1. **Create connector structure**
   ```
   src/connectors/my_connector/
   ├── __init__.py
   ├── connector.py
   └── README.md
   ```

2. **Implement BaseConnector**
   - Required: `get_tools()`, `execute_tool()`
   - Optional: `get_resources()`, `get_prompts()`

3. **Add to config**
   ```yaml
   connectors:
     - name: my_connector
       enabled: true
       config: {}
   ```

4. **Document usage**
   - Add examples to QUICKSTART.md
   - Update tool count in README.md

### Security Considerations

- Never execute user input directly
- Validate all inputs
- Use timeouts for external calls
- Filter sensitive environment variables
- Document security implications

## 🚨 Incident Response

### Bug Reports

1. **Verify** - Reproduce the issue
2. **Isolate** - Find minimal reproduction
3. **Document** - Create detailed issue
4. **Fix** - Create PR with tests
5. **Verify** - Test fix in multiple environments

### Security Issues

1. **Do NOT** create public issue
2. **Email** security@mcp-gateway.org
3. **Include** detailed report
4. **Wait** for acknowledgment
5. **Coordinate** disclosure timeline

## 📊 Metrics & Quality

### Code Quality Metrics

- Test coverage > 80%
- No critical security issues
- Documentation coverage 100%
- Type hints on all public APIs

### Performance Targets

- Startup time < 2s
- Tool execution < 100ms overhead
- Memory usage < 100MB base
- Support 100+ connectors

## 🎯 Development Priorities

### Current Focus (v0.1.x)
1. Core stability
2. Built-in connector improvements
3. Documentation completeness
4. NPM package reliability

### Next Phase (v0.2.x)
1. External connector API
2. Authentication system
3. Web UI for configuration
4. Connector marketplace

### Future (v1.0.0)
1. Production readiness
2. Enterprise features
3. Performance optimization
4. Extensive connector library

---

Remember: Clear commits, comprehensive tests, and good documentation make future development easier!