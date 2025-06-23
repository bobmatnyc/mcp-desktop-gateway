# Python Development Instructions

This document provides best practices and guidelines for Python development in microservices and desktop integration projects.

## Development Environment Setup

### Python Version Management
- Use Python 3.11+ for modern features and performance improvements
- Use `pyenv` or `asdf` for managing Python versions
- Always specify the exact Python version in `pyproject.toml`

### Virtual Environment
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
source venv/bin/activate  # Unix/macOS
venv\Scripts\activate     # Windows

# Install dependencies
pip install -e ".[dev]"
```

### IDE Configuration
- **VS Code**: Install Python, Pylance, and Ruff extensions
- **PyCharm**: Enable type checking and configure Ruff
- Configure auto-formatting on save
- Enable type checking in strict mode

## Code Style and Standards

### Code Formatting
- Use **Ruff** for linting and formatting (replaces Black, isort, flake8)
- Configure in `pyproject.toml`:
```toml
[tool.ruff]
line-length = 88
target-version = "py311"
select = ["E", "F", "UP", "B", "SIM", "I"]
```

### Type Hints
- Use type hints for all function signatures
- Use `from typing import` for complex types
- Enable strict type checking with mypy or pyright
```python
from typing import Optional, List, Dict, Any

def process_data(items: List[Dict[str, Any]]) -> Optional[str]:
    """Process a list of dictionaries and return result."""
    ...
```

### Docstrings
- Use Google-style docstrings for consistency
- Document all public functions, classes, and modules
```python
def calculate_score(value: float, weight: float = 1.0) -> float:
    """Calculate weighted score.
    
    Args:
        value: The base value to score
        weight: Optional weight multiplier (default: 1.0)
        
    Returns:
        The calculated weighted score
        
    Raises:
        ValueError: If value is negative
    """
```

## Project Structure

### Standard Layout
```
project/
├── src/
│   └── package_name/
│       ├── __init__.py
│       ├── main.py
│       ├── models/
│       ├── services/
│       ├── utils/
│       └── config.py
├── tests/
│   ├── unit/
│   ├── integration/
│   └── conftest.py
├── docs/
├── scripts/
├── pyproject.toml
├── README.md
└── .gitignore
```

### Module Organization
- Keep modules focused and single-purpose
- Use `__init__.py` to control public API
- Avoid circular imports
- Use relative imports within the package

## Async Programming

### AsyncIO Best Practices
```python
import asyncio
from typing import List

async def fetch_data(url: str) -> dict:
    """Fetch data from URL asynchronously."""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()

async def process_multiple(urls: List[str]) -> List[dict]:
    """Process multiple URLs concurrently."""
    tasks = [fetch_data(url) for url in urls]
    return await asyncio.gather(*tasks)
```

### Context Managers
```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def managed_resource():
    """Manage resource lifecycle."""
    resource = await acquire_resource()
    try:
        yield resource
    finally:
        await resource.cleanup()
```

## Error Handling

### Exception Hierarchy
```python
class AppError(Exception):
    """Base exception for application errors."""
    pass

class ValidationError(AppError):
    """Raised when validation fails."""
    pass

class ConnectionError(AppError):
    """Raised when connection fails."""
    pass
```

### Error Handling Patterns
```python
import logging
from typing import Optional

logger = logging.getLogger(__name__)

def safe_operation() -> Optional[str]:
    """Perform operation with proper error handling."""
    try:
        result = risky_operation()
        return result
    except ValidationError as e:
        logger.warning(f"Validation failed: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise AppError(f"Operation failed: {e}") from e
```

## Testing

### Test Structure
```python
import pytest
from unittest.mock import Mock, patch

class TestUserService:
    """Test cases for UserService."""
    
    @pytest.fixture
    def service(self):
        """Create service instance for testing."""
        return UserService(mock_db)
    
    def test_create_user(self, service):
        """Test user creation."""
        user = service.create_user("test@example.com")
        assert user.email == "test@example.com"
    
    @pytest.mark.asyncio
    async def test_async_operation(self, service):
        """Test async operation."""
        result = await service.async_method()
        assert result is not None
```

### Testing Best Practices
- Write tests first (TDD) when possible
- Aim for 80%+ code coverage
- Use fixtures for common test data
- Mock external dependencies
- Test edge cases and error conditions

## Configuration Management

### Environment Variables
```python
import os
from typing import Optional
from pydantic import BaseSettings

class Settings(BaseSettings):
    """Application settings."""
    
    app_name: str = "MyApp"
    debug: bool = False
    database_url: Optional[str] = None
    api_key: Optional[str] = None
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
```

### Configuration Files
- Use YAML or TOML for complex configurations
- Validate configurations at startup
- Provide sensible defaults
- Document all configuration options

## Logging

### Structured Logging
```python
import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    """Format logs as JSON."""
    
    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
        }
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_data)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger.addHandler(handler)
```

## Dependency Management

### Using pyproject.toml
```toml
[project]
name = "my-project"
version = "0.1.0"
description = "Project description"
dependencies = [
    "aiohttp>=3.8",
    "pydantic>=2.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-asyncio",
    "pytest-cov",
    "ruff",
    "mypy",
]

[build-system]
requires = ["setuptools>=61", "wheel"]
build-backend = "setuptools.build_meta"
```

### Dependency Best Practices
- Pin major versions in production
- Use optional dependencies for dev tools
- Regularly update dependencies
- Check for security vulnerabilities

## Security Best Practices

### Input Validation
```python
from pydantic import BaseModel, validator, EmailStr

class UserInput(BaseModel):
    """Validate user input."""
    
    email: EmailStr
    age: int
    
    @validator("age")
    def validate_age(cls, v):
        if v < 0 or v > 150:
            raise ValueError("Invalid age")
        return v
```

### Secrets Management
- Never hardcode secrets
- Use environment variables or secret managers
- Rotate secrets regularly
- Log security events

## Performance Optimization

### Profiling
```python
import cProfile
import pstats
from functools import wraps

def profile(func):
    """Profile function execution."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        profiler = cProfile.Profile()
        profiler.enable()
        result = func(*args, **kwargs)
        profiler.disable()
        stats = pstats.Stats(profiler)
        stats.sort_stats("cumulative")
        stats.print_stats(10)
        return result
    return wrapper
```

### Caching
```python
from functools import lru_cache
import asyncio

@lru_cache(maxsize=128)
def expensive_computation(n: int) -> int:
    """Cache expensive computation results."""
    return sum(i ** 2 for i in range(n))

# For async functions
from aiocache import cached

@cached(ttl=300)  # Cache for 5 minutes
async def fetch_user_data(user_id: str) -> dict:
    """Fetch and cache user data."""
    return await database.get_user(user_id)
```

## Documentation

### API Documentation
- Use docstrings for auto-generated docs
- Document all public APIs
- Include examples in docstrings
- Keep documentation up-to-date

### README Structure
1. Project overview
2. Installation instructions
3. Quick start guide
4. API reference
5. Contributing guidelines
6. License information

## Continuous Integration

### GitHub Actions Example
```yaml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12"]
    
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    - name: Install dependencies
      run: |
        pip install -e ".[dev]"
    - name: Run tests
      run: |
        pytest --cov=src --cov-report=xml
    - name: Run linting
      run: |
        ruff check .
        mypy src/
```

## Debugging Tips

### Using debugpy
```python
# For remote debugging
import debugpy
debugpy.listen(5678)
debugpy.wait_for_client()  # Pause until debugger connects
```

### Logging for Debugging
```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)
logger.debug(f"Variable state: {variable}")
```

## Common Pitfalls to Avoid

1. **Mutable Default Arguments**
   ```python
   # Bad
   def append_to_list(item, target=[]):
       target.append(item)
       return target
   
   # Good
   def append_to_list(item, target=None):
       if target is None:
           target = []
       target.append(item)
       return target
   ```

2. **Not Using Context Managers**
   ```python
   # Bad
   file = open("data.txt")
   data = file.read()
   file.close()
   
   # Good
   with open("data.txt") as file:
       data = file.read()
   ```

3. **Ignoring Async Context**
   ```python
   # Bad
   def sync_in_async():
       time.sleep(1)  # Blocks event loop
   
   # Good
   async def async_proper():
       await asyncio.sleep(1)  # Non-blocking
   ```

## Resources

- [Python Official Documentation](https://docs.python.org/3/)
- [Real Python Tutorials](https://realpython.com/)
- [Python Packaging Guide](https://packaging.python.org/)
- [Async IO Documentation](https://docs.python.org/3/library/asyncio.html)
- [Type Hints PEP 484](https://www.python.org/dev/peps/pep-0484/)