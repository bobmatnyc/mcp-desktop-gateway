# Contributing to MCP Gateway

Thank you for your interest in contributing to MCP Gateway! This document provides guidelines and instructions for contributing.

## Code of Conduct

By participating in this project, you agree to abide by our Code of Conduct:
- Be respectful and inclusive
- Welcome newcomers and help them get started
- Focus on constructive criticism
- Respect differing viewpoints and experiences

## How to Contribute

### Reporting Issues

1. Check if the issue already exists
2. Use the issue template
3. Include:
   - Clear description
   - Steps to reproduce
   - Expected vs actual behavior
   - System information (OS, Python version, etc.)
   - Relevant logs

### Suggesting Features

1. Check existing feature requests
2. Open a discussion first for major features
3. Explain the use case and benefits
4. Consider implementation complexity

### Pull Requests

#### Setup Development Environment

```bash
# Fork and clone the repository
git clone https://github.com/your-username/mcp-gateway.git
cd mcp-gateway

# Create a branch
git checkout -b feature/your-feature-name

# Set up development environment
make dev
```

#### Development Workflow

1. **Make changes**
   - Follow existing code style
   - Add tests for new functionality
   - Update documentation as needed

2. **Test your changes**
   ```bash
   # Run tests
   make test
   
   # Test NPM package
   make test-npm
   
   # Test in Claude Desktop
   make switch-dev
   ```

3. **Update version** (if needed)
   ```bash
   python scripts/version.py bump patch
   ```

4. **Commit your changes**
   ```bash
   git add .
   git commit -m "feat: add amazing feature"
   ```

   Use conventional commits:
   - `feat:` New feature
   - `fix:` Bug fix
   - `docs:` Documentation
   - `style:` Code style
   - `refactor:` Refactoring
   - `test:` Tests
   - `chore:` Maintenance

5. **Push and create PR**
   ```bash
   git push origin feature/your-feature-name
   ```

### Code Style

#### Python
- Follow PEP 8
- Use type hints where appropriate
- Maximum line length: 100 characters
- Use descriptive variable names

```python
# Good
async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> ToolResult:
    """Execute a tool with given arguments."""
    
# Bad
async def exec(self, n, args):
    pass
```

#### Documentation
- Use docstrings for all public methods
- Include examples in docstrings
- Update README.md for user-facing changes
- Update PROJECT.md for architectural changes

### Testing

#### Writing Tests

```python
# tests/test_connector.py
import pytest
from src.core.base_connector import BaseConnector

class TestConnector:
    def test_connector_initialization(self):
        connector = BaseConnector("test", {})
        assert connector.name == "test"
    
    @pytest.mark.asyncio
    async def test_async_method(self):
        # Test async methods
        result = await connector.some_async_method()
        assert result is not None
```

#### Running Tests

```bash
# Run all tests
make test

# Run specific test
pytest tests/test_connector.py::TestConnector::test_connector_initialization

# Run with coverage
pytest --cov=src tests/
```

### Documentation

#### Adding Examples

Create examples in the `examples/` directory:

```python
# examples/custom_connector.py
"""
Example: Creating a custom connector
"""

from src.core.base_connector import BaseConnector
from src.core.models import ToolDefinition, ToolResult

class WeatherConnector(BaseConnector):
    """Example weather connector."""
    
    def get_tools(self):
        return [
            ToolDefinition(
                name="get_weather",
                description="Get current weather",
                input_schema={
                    "type": "object",
                    "properties": {
                        "city": {"type": "string"}
                    },
                    "required": ["city"]
                }
            )
        ]
```

### Release Process

1. **Version bump**
   ```bash
   python scripts/version.py bump minor
   ```

2. **Update CHANGELOG.md**
   - Add version section
   - List all changes
   - Credit contributors

3. **Create release PR**
   - Title: "Release v0.2.0"
   - Include changelog in description

4. **After merge**
   ```bash
   # Tag release
   python scripts/version.py tag "Release v0.2.0"
   
   # Push tags
   git push --tags
   
   # Publish to NPM
   npm publish
   ```

## Connector Development

### Creating a Built-in Connector

1. Create connector directory:
   ```bash
   mkdir -p src/connectors/my_connector
   touch src/connectors/my_connector/__init__.py
   touch src/connectors/my_connector/connector.py
   ```

2. Implement connector:
   ```python
   from core.base_connector import BaseConnector
   
   class MyConnector(BaseConnector):
       """My custom connector."""
       
       def get_tools(self):
           return [...]
   ```

3. Add to config:
   ```yaml
   connectors:
     - name: my_connector
       enabled: true
       config: {}
   ```

### Best Practices

1. **Error Handling**
   ```python
   try:
       result = await dangerous_operation()
   except SpecificError as e:
       return ToolResult(
           content=[ToolContent(type="text", text=f"Error: {e}")],
           type=ToolResultType.ERROR
       )
   ```

2. **Logging**
   ```python
   import logging
   logger = logging.getLogger(f"connector.{self.name}")
   logger.info("Operation completed")
   ```

3. **Security**
   - Validate all inputs
   - Use timeouts for external calls
   - Filter sensitive data
   - Never execute untrusted code

## Questions?

- Open a [Discussion](https://github.com/mcp-gateway/mcp-gateway/discussions)
- Join our community chat
- Email: contributors@mcp-gateway.org

Thank you for contributing to MCP Gateway! 🎉