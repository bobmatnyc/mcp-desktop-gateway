"""
Centralized logging configuration for MCP Bridge
"""

import json
import logging
import logging.handlers
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from .env_config import config as env_config


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging"""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add extra fields
        if hasattr(record, "extra"):
            for key, value in record.extra.items():
                if key not in ["message", "asctime"]:
                    log_data[key] = value

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


class ColoredFormatter(logging.Formatter):
    """Colored formatter for console output"""

    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors"""
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{self.RESET}"
        return super().format(record)


def setup_logging(
    log_level: Optional[str] = None,
    log_file: Optional[Path] = None,
    use_json: bool = False,
    console_enabled: bool = True,
    file_enabled: bool = True,
) -> None:
    """
    Setup centralized logging configuration

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file
        use_json: Use JSON formatting for logs
        console_enabled: Enable console logging
        file_enabled: Enable file logging
    """
    # Get log level from environment or parameter
    if log_level is None:
        log_level = env_config.MCP_LOG_LEVEL

    # Convert to logging level
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Create logs directory if needed
    if log_file is None:
        log_dir = Path(__file__).parent.parent.parent / "logs"
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / f"mcp_bridge_{datetime.now().strftime('%Y%m%d')}.log"
    else:
        log_file.parent.mkdir(parents=True, exist_ok=True)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Remove existing handlers
    root_logger.handlers.clear()

    # Console handler
    if console_enabled and sys.stdin.isatty():  # Only enable console if NOT in MCP mode
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)

        if use_json:
            console_handler.setFormatter(StructuredFormatter())
        else:
            # Use colored formatter for console if not JSON
            if sys.stdout.isatty():  # Check if output is terminal
                formatter = ColoredFormatter(
                    "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                )
            else:
                formatter = logging.Formatter(
                    "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                )
            console_handler.setFormatter(formatter)

        root_logger.addHandler(console_handler)

    # File handler with rotation
    if file_enabled:
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"  # 10MB
        )
        file_handler.setLevel(numeric_level)

        # Always use structured format for files
        file_handler.setFormatter(StructuredFormatter())
        root_logger.addHandler(file_handler)

    # Configure specific loggers
    configure_module_loggers(numeric_level)

    # Log startup message
    logger = logging.getLogger(__name__)
    logger.info(
        "Logging configured",
        extra={
            "log_level": log_level,
            "log_file": str(log_file) if file_enabled else None,
            "console_enabled": console_enabled,
            "file_enabled": file_enabled,
            "use_json": use_json,
        },
    )


def configure_module_loggers(default_level: int) -> None:
    """Configure logging levels for specific modules"""
    # Quiet down noisy libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("googleapiclient").setLevel(logging.WARNING)
    logging.getLogger("google.auth").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)

    # Set custom levels for our modules
    module_levels = {
        "src.connectors": default_level,
        "src.core": default_level,
        "eva-agent": default_level,
        "src.mcp_server": default_level,
    }

    for module, level in module_levels.items():
        logging.getLogger(module).setLevel(level)


class LoggerAdapter(logging.LoggerAdapter):
    """Custom logger adapter for adding context"""

    def __init__(self, logger: logging.Logger, service: str):
        super().__init__(logger, {})
        self.service = service

    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple:
        """Add service context to all logs"""
        extra = kwargs.get("extra", {})
        extra["service"] = self.service
        kwargs["extra"] = extra
        return msg, kwargs


def get_logger(name: str, service: Optional[str] = None) -> logging.Logger:
    """
    Get a logger instance

    Args:
        name: Logger name (usually __name__)
        service: Optional service name for context

    Returns:
        Logger instance
    """
    logger = logging.getLogger(name)

    if service:
        return LoggerAdapter(logger, service)

    return logger


# Initialize logging on import if not already done
if not logging.getLogger().handlers:
    setup_logging()
