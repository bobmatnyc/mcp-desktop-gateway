"""
Configuration management for MCP Bridge
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from .models import BridgeConfig, ConnectorConfig, ServerConfig

logger = logging.getLogger(__name__)


class ConfigManager:
    """Manages configuration for MCP Bridge"""

    DEFAULT_CONFIG = {
        "server": {"name": "mcp-bridge", "version": "1.0.0", "log_level": "INFO"},
        "connectors": [],
    }

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration manager

        Args:
            config_path: Path to configuration file (defaults to config/config.yaml)
        """
        self.config_path = config_path or self._get_default_config_path()
        self.config_data: Dict[str, Any] = {}
        self.bridge_config: Optional[BridgeConfig] = None
        self._load_config()

    def _get_default_config_path(self) -> str:
        """Get default configuration file path"""
        # Look for config in these locations (in order):
        # 1. Environment variable
        # 2. config/config.yaml relative to project root
        # 3. ~/.mcp-bridge/config.yaml

        if env_path := os.getenv("MCP_BRIDGE_CONFIG"):
            return env_path

        # Try relative to project root
        project_root = Path(__file__).parent.parent.parent
        config_file = project_root / "config" / "config.yaml"
        if config_file.exists():
            return str(config_file)

        # Try user home directory
        home_config = Path.home() / ".mcp-bridge" / "config.yaml"
        return str(home_config)

    def _load_config(self) -> None:
        """Load configuration from file"""
        config_path = Path(self.config_path)

        if config_path.exists():
            try:
                with open(config_path, "r") as f:
                    self.config_data = yaml.safe_load(f) or {}
                logger.info(f"Loaded configuration from {config_path}")
            except Exception as e:
                logger.warning(f"Failed to load config from {config_path}: {e}")
                self.config_data = {}
        else:
            logger.info(f"No config file found at {config_path}, using defaults")
            self.config_data = {}
            self._create_default_config()

        # Merge with defaults
        self.config_data = self._merge_with_defaults(self.config_data)

        # Expand environment variables
        self.config_data = self._expand_env_vars(self.config_data)

        # Create Pydantic model
        self.bridge_config = BridgeConfig(**self.config_data)

    def _create_default_config(self) -> None:
        """Create default configuration file"""
        config_path = Path(self.config_path)

        # Create directory if it doesn't exist
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # Write default configuration
        default_yaml = """# MCP Bridge Configuration
server:
  name: "mcp-bridge"
  version: "1.0.0"
  log_level: "INFO"

connectors:
  # Example connector configuration
  # - name: hello
  #   enabled: true
  #   config: {}
"""

        try:
            with open(config_path, "w") as f:
                f.write(default_yaml)
            logger.info(f"Created default configuration at {config_path}")
        except Exception as e:
            logger.warning(f"Failed to create default config: {e}")

    def _merge_with_defaults(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Merge configuration with defaults"""
        merged = self.DEFAULT_CONFIG.copy()

        # Deep merge
        if "server" in config:
            merged["server"].update(config["server"])

        if "connectors" in config:
            merged["connectors"] = config["connectors"]

        return merged

    def _expand_env_vars(self, obj: Any) -> Any:
        """Recursively expand environment variables in configuration"""
        if isinstance(obj, str):
            # Expand ${VAR} or $VAR patterns
            if obj.startswith("${") and obj.endswith("}"):
                var_name = obj[2:-1]
                return os.getenv(var_name, obj)
            elif obj.startswith("$"):
                var_name = obj[1:]
                return os.getenv(var_name, obj)
            return obj
        elif isinstance(obj, dict):
            return {k: self._expand_env_vars(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._expand_env_vars(item) for item in obj]
        return obj

    def get_server_config(self) -> ServerConfig:
        """Get server configuration"""
        if not self.bridge_config:
            raise RuntimeError("Configuration not loaded")
        return self.bridge_config.server

    def get_connector_configs(self) -> List[ConnectorConfig]:
        """Get all connector configurations"""
        if not self.bridge_config:
            raise RuntimeError("Configuration not loaded")
        return self.bridge_config.connectors

    def get_enabled_connectors(self) -> List[ConnectorConfig]:
        """Get only enabled connector configurations"""
        return [c for c in self.get_connector_configs() if c.enabled]

    def get_connector_config(self, name: str) -> Optional[ConnectorConfig]:
        """Get configuration for a specific connector"""
        for connector in self.get_connector_configs():
            if connector.name == name:
                return connector
        return None

    def reload(self) -> None:
        """Reload configuration from file"""
        logger.info("Reloading configuration...")
        self._load_config()

    def save(self) -> None:
        """Save current configuration to file"""
        config_path = Path(self.config_path)

        # Convert to dict for YAML serialization
        config_dict = {
            "server": self.bridge_config.server.model_dump() if self.bridge_config else {},
            "connectors": [c.model_dump() for c in self.get_connector_configs()],
        }

        try:
            with open(config_path, "w") as f:
                yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)
            logger.info(f"Saved configuration to {config_path}")
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            raise

    def __str__(self) -> str:
        return f"ConfigManager(path='{self.config_path}')"

    def __repr__(self) -> str:
        return f"ConfigManager(config_path='{self.config_path}', loaded={self.bridge_config is not None})"
