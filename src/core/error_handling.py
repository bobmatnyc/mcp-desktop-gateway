"""
Centralized error handling utilities for MCP Bridge
"""

import asyncio
import functools
import logging
import random
import time
from enum import Enum
from typing import Any, Callable, Optional, Tuple, Type, TypeVar, Union

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ErrorSeverity(Enum):
    """Error severity levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MCPError(Exception):
    """Base exception for MCP Bridge errors"""

    def __init__(
        self,
        message: str,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        details: Optional[dict] = None,
    ):
        super().__init__(message)
        self.severity = severity
        self.details = details or {}
        self.timestamp = time.time()


class ExternalServiceError(MCPError):
    """Error when interacting with external services"""

    pass


class AuthenticationError(MCPError):
    """Authentication related errors"""

    def __init__(self, message: str, service: str, details: Optional[dict] = None):
        super().__init__(message, ErrorSeverity.HIGH, details)
        self.service = service


class ValidationError(MCPError):
    """Data validation errors"""

    def __init__(self, message: str, field: str, value: Any, details: Optional[dict] = None):
        super().__init__(message, ErrorSeverity.LOW, details)
        self.field = field
        self.value = value


class ResourceError(MCPError):
    """Resource management errors"""

    pass


def handle_errors(
    *exceptions: Type[Exception],
    default_return: Any = None,
    log_errors: bool = True,
    raise_on: Optional[Tuple[Type[Exception], ...]] = None,
) -> Callable:
    """
    Decorator for comprehensive error handling

    Args:
        exceptions: Exception types to catch
        default_return: Default value to return on error
        log_errors: Whether to log errors
        raise_on: Exception types that should be re-raised
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except exceptions as e:
                if raise_on and isinstance(e, raise_on):
                    raise

                if log_errors:
                    logger.error(
                        f"Error in {func.__name__}: {str(e)}",
                        exc_info=True,
                        extra={
                            "function": func.__name__,
                            "module": func.__module__,
                            "error_type": type(e).__name__,
                        },
                    )

                if isinstance(e, MCPError):
                    # Handle our custom errors specially
                    if e.severity == ErrorSeverity.CRITICAL:
                        raise

                return default_return

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except exceptions as e:
                if raise_on and isinstance(e, raise_on):
                    raise

                if log_errors:
                    logger.error(
                        f"Error in {func.__name__}: {str(e)}",
                        exc_info=True,
                        extra={
                            "function": func.__name__,
                            "module": func.__module__,
                            "error_type": type(e).__name__,
                        },
                    )

                if isinstance(e, MCPError):
                    # Handle our custom errors specially
                    if e.severity == ErrorSeverity.CRITICAL:
                        raise

                return default_return

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator


def retry_with_backoff(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
) -> Callable:
    """
    Decorator for retrying functions with exponential backoff

    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Initial delay between retries
        max_delay: Maximum delay between retries
        exponential_base: Base for exponential backoff
        jitter: Add random jitter to prevent thundering herd
        exceptions: Exception types to retry on
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt == max_attempts - 1:
                        logger.error(
                            f"Max retries ({max_attempts}) reached for {func.__name__}",
                            extra={"last_error": str(e)},
                        )
                        raise

                    # Calculate delay with exponential backoff
                    delay = min(base_delay * (exponential_base**attempt), max_delay)

                    # Add jitter
                    if jitter:
                        delay *= 0.5 + random.random()

                    logger.warning(
                        f"Retry {attempt + 1}/{max_attempts} for {func.__name__} after {delay:.2f}s",
                        extra={"error": str(e)},
                    )

                    await asyncio.sleep(delay)

            raise last_exception

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt == max_attempts - 1:
                        logger.error(
                            f"Max retries ({max_attempts}) reached for {func.__name__}",
                            extra={"last_error": str(e)},
                        )
                        raise

                    # Calculate delay with exponential backoff
                    delay = min(base_delay * (exponential_base**attempt), max_delay)

                    # Add jitter
                    if jitter:
                        delay *= 0.5 + random.random()

                    logger.warning(
                        f"Retry {attempt + 1}/{max_attempts} for {func.__name__} after {delay:.2f}s",
                        extra={"error": str(e)},
                    )

                    time.sleep(delay)

            raise last_exception

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator


class ErrorContext:
    """Context manager for structured error handling"""

    def __init__(
        self,
        operation: str,
        service: Optional[str] = None,
        reraise: bool = True,
        default_return: Any = None,
    ):
        self.operation = operation
        self.service = service
        self.reraise = reraise
        self.default_return = default_return
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            return False

        duration = time.time() - self.start_time

        logger.error(
            f"Error in {self.operation}",
            exc_info=True,
            extra={
                "operation": self.operation,
                "service": self.service,
                "duration": duration,
                "error_type": exc_type.__name__,
                "error_message": str(exc_val),
            },
        )

        if not self.reraise:
            return True

        # Convert to our custom error types if needed
        if issubclass(exc_type, (ConnectionError, TimeoutError)):
            raise ExternalServiceError(
                f"Failed to connect to {self.service or 'external service'}: {exc_val}",
                details={"original_error": exc_type.__name__},
            )

        return False

    async def __aenter__(self):
        self.start_time = time.time()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return self.__exit__(exc_type, exc_val, exc_tb)


def validate_required_fields(**fields: Any) -> None:
    """
    Validate that required fields are not None or empty

    Args:
        **fields: Field name to value mapping

    Raises:
        ValidationError: If any field is None or empty
    """
    for field_name, value in fields.items():
        if value is None:
            raise ValidationError(
                f"Required field '{field_name}' is None", field=field_name, value=value
            )

        if isinstance(value, str) and not value.strip():
            raise ValidationError(
                f"Required field '{field_name}' is empty", field=field_name, value=value
            )

        if isinstance(value, (list, dict)) and not value:
            raise ValidationError(
                f"Required field '{field_name}' is empty", field=field_name, value=value
            )
