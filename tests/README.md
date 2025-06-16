# MCP Desktop Gateway Test Suite

This directory contains comprehensive tests for the MCP Desktop Gateway project.

## Test Structure

```
tests/
├── unit/                      # Unit tests
│   ├── core/                  # Core component tests
│   │   ├── test_registry_simple.py      # ConnectorRegistry tests
│   │   ├── test_base_connector.py       # BaseConnector tests
│   │   └── test_config.py               # Configuration management tests
│   └── connectors/            # Connector-specific tests
│       ├── hello_world/
│       │   └── test_hello_world_connector.py
│       ├── shell/
│       │   └── test_shell_connector.py
│       ├── applescript/       # (TODO)
│       └── gateway_utils/     # (TODO)
├── integration/               # Integration tests (TODO)
├── fixtures/                  # Test fixtures and data
└── conftest.py               # Common fixtures and configuration
```

## Running Tests

### Quick Commands

```bash
# Run all tests
make test

# Run only unit tests
make test-unit

# Run with coverage
make test-coverage

# Run specific test file
python scripts/run_tests.py tests/unit/core/test_registry_simple.py -v
```

### Test Categories

- **Unit Tests** (`tests/unit/`): Test individual components in isolation
- **Integration Tests** (`tests/integration/`): Test component interactions
- **Connector Tests** (`tests/unit/connectors/`): Test specific connector implementations

## Test Coverage Status

### ✅ Completed Tests

#### Core Components
- **ConnectorRegistry** (`test_registry_simple.py`)
  - Connector registration and discovery
  - Tool execution routing
  - Connector lifecycle management
  - Error handling

- **BaseConnector** (`test_base_connector.py`)
  - Tool validation and execution
  - Resource management
  - Prompt handling
  - Usage statistics

- **Configuration** (`test_config.py`)
  - YAML/JSON config loading
  - Environment variable handling
  - Config validation

#### Connectors
- **HelloWorld Connector** (`test_hello_world_connector.py`)
  - All tool executions (hello_world, diagnostics, echo)
  - Resource reading (config, status, logs)
  - Prompt execution
  - Activity logging

- **Shell Connector** (`test_shell_connector.py`)
  - Command execution with safety checks
  - Directory listing
  - System information
  - Timeout and output handling
  - Security validation

### 🔄 In Progress

- AppleScript connector tests
- Gateway Utils connector tests
- Integration tests for MCP protocol

### 📊 Coverage Metrics

Current estimated coverage:
- **Core Components**: ~85% covered
- **HelloWorld Connector**: ~90% covered
- **Shell Connector**: ~80% covered
- **Overall Project**: ~60% covered

## Test Infrastructure

### Fixtures (`conftest.py`)
- Mock connectors for testing
- Temporary config files
- Sample MCP requests
- Async test helpers

### Test Utilities (`scripts/run_tests.py`)
- Automated test runner with proper PYTHONPATH
- Support for pytest arguments
- Environment setup

### Pytest Configuration (`pytest.ini`)
- Async test support
- Custom markers for test categories
- Proper warning handling

## Writing New Tests

### Test File Naming
- Use descriptive names: `test_{component}_connector.py`
- Follow pytest naming conventions
- Avoid naming conflicts between modules

### Test Structure
```python
@pytest.mark.{category}  # core, connector, integration
class Test{ComponentName}:
    """Test {Component} functionality."""
    
    @pytest.fixture
    def component(self):
        \"\"\"Create component instance for testing.\"\"\"
        return ComponentClass(name="test", config={})
    
    def test_{specific_functionality}(self, component):
        \"\"\"Test specific functionality.\"\"\"
        # Arrange
        # Act
        # Assert
```

### Async Tests
```python
@pytest.mark.asyncio
async def test_async_operation(self, component):
    \"\"\"Test async operation.\"\"\"
    result = await component.async_method()
    assert result is not None
```

### Mocking External Dependencies
```python
@patch('external.module.function')
def test_with_mock(self, mock_function, component):
    \"\"\"Test with mocked external dependency.\"\"\"
    mock_function.return_value = "mocked_result"
    # Test code
```

## Best Practices

1. **Test Isolation**: Each test should be independent
2. **Clear Naming**: Test names should describe what they test
3. **Arrange-Act-Assert**: Structure tests clearly
4. **Mock External Dependencies**: Don't test external services
5. **Test Error Conditions**: Include negative test cases
6. **Use Fixtures**: Reuse common test setup
7. **Async Testing**: Proper async/await patterns for async code

## Continuous Integration

Tests are designed to run in CI environments:
- No external dependencies required
- Isolated test execution
- Proper cleanup after tests
- Platform-independent where possible

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure `PYTHONPATH` includes `src/`
2. **Async Warnings**: Use `@pytest.mark.asyncio` for async tests
3. **Module Conflicts**: Use unique test file names
4. **Cache Issues**: Clear `__pycache__` directories

### Debug Commands
```bash
# Run single test with full output
python scripts/run_tests.py tests/unit/core/test_registry_simple.py::TestConnectorRegistry::test_registry_initialization -v -s

# Run with pdb debugger
python scripts/run_tests.py tests/unit/core/test_registry_simple.py --pdb

# Show test coverage
make test-coverage
```

## Contributing

When adding new components:
1. Create corresponding test files
2. Aim for >80% coverage
3. Include both positive and negative test cases
4. Update this README with new test status
5. Ensure tests pass in CI

## Future Improvements

- [ ] Integration tests for full MCP protocol flow
- [ ] Performance benchmarking tests
- [ ] Security-focused tests
- [ ] Cross-platform compatibility tests
- [ ] Load testing for connector registry
- [ ] Property-based testing for complex scenarios