"""
Centralized environment configuration management
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load .env file if it exists
env_file = Path(__file__).parent.parent.parent / ".env"
if env_file.exists():
    load_dotenv(env_file)
    logger.info(f"Loaded environment from {env_file}")
else:
    logger.warning(f"No .env file found at {env_file}")


class EnvironmentConfig:
    """Centralized configuration from environment variables"""

    # API Keys
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY")

    # Google OAuth Credentials
    GOOGLE_GMAIL_CREDENTIALS_FILE: str = os.getenv(
        "GOOGLE_GMAIL_CREDENTIALS_FILE", "gmail_credentials.json"
    )
    GOOGLE_CALENDAR_CREDENTIALS_FILE: str = os.getenv(
        "GOOGLE_CALENDAR_CREDENTIALS_FILE", "gcal_credentials.json"
    )
    GOOGLE_TASKS_CREDENTIALS_FILE: str = os.getenv(
        "GOOGLE_TASKS_CREDENTIALS_FILE", "gtasks_credentials.json"
    )
    GOOGLE_DRIVE_CREDENTIALS_FILE: str = os.getenv(
        "GOOGLE_DRIVE_CREDENTIALS_FILE", "gdrive_credentials.json"
    )

    # Token Storage Paths
    GMAIL_TOKEN_FILE: str = os.getenv("GMAIL_TOKEN_FILE", "gmail_token.pickle")
    GCAL_TOKEN_FILE: str = os.getenv("GCAL_TOKEN_FILE", "gcal_token.pickle")
    GTASKS_TOKEN_FILE: str = os.getenv("GTASKS_TOKEN_FILE", "gtasks_token.pickle")
    GDRIVE_TOKEN_FILE: str = os.getenv("GDRIVE_TOKEN_FILE", "gdrive_token.pickle")

    # MongoDB Configuration
    MONGODB_HOST: str = os.getenv("MONGODB_HOST", "localhost")
    MONGODB_PORT: int = int(os.getenv("MONGODB_PORT", "27017"))
    MONGODB_DATABASE: str = os.getenv("MONGODB_DATABASE", "eva_agent")

    @property
    def mongodb_url(self) -> str:
        """Get MongoDB connection URL"""
        return f"mongodb://{self.MONGODB_HOST}:{self.MONGODB_PORT}/"

    # Qdrant Configuration
    QDRANT_HOST: str = os.getenv("QDRANT_HOST", "localhost")
    QDRANT_PORT: int = int(os.getenv("QDRANT_PORT", "6333"))
    QDRANT_COLLECTION: str = os.getenv("QDRANT_COLLECTION", "eva_memories")

    # Slack Configuration
    SLACK_APP_TOKEN: Optional[str] = os.getenv("SLACK_APP_TOKEN")
    SLACK_BOT_TOKEN: Optional[str] = os.getenv("SLACK_BOT_TOKEN")

    # Fireflies Configuration
    FIREFLIES_API_KEY: Optional[str] = os.getenv("FIREFLIES_API_KEY")

    # Server Configuration
    MCP_SERVER_HOST: str = os.getenv("MCP_SERVER_HOST", "localhost")
    MCP_SERVER_PORT: int = int(os.getenv("MCP_SERVER_PORT", "3000"))
    MCP_LOG_LEVEL: str = os.getenv("MCP_LOG_LEVEL", "INFO")

    # Eva Agent Configuration
    EVA_MODE: str = os.getenv("EVA_MODE", "training-wheels")
    EVA_LLM_PROVIDER: str = os.getenv("EVA_LLM_PROVIDER", "openai")
    EVA_DEFAULT_MODEL: str = os.getenv("EVA_DEFAULT_MODEL", "gpt-4-turbo")

    # Feature Flags
    ENABLE_MEMORY_SYSTEM: bool = os.getenv("ENABLE_MEMORY_SYSTEM", "true").lower() == "true"
    ENABLE_VECTOR_SEARCH: bool = os.getenv("ENABLE_VECTOR_SEARCH", "true").lower() == "true"
    ENABLE_ENVIRONMENTAL_AWARENESS: bool = (
        os.getenv("ENABLE_ENVIRONMENTAL_AWARENESS", "true").lower() == "true"
    )
    ENABLE_DEBUG_LOGGING: bool = os.getenv("ENABLE_DEBUG_LOGGING", "false").lower() == "true"

    @classmethod
    def validate(cls) -> Dict[str, Any]:
        """Validate configuration and return missing required variables"""
        missing = {}
        warnings = {}

        # Check required API keys based on provider
        if cls.EVA_LLM_PROVIDER == "openai" and not cls.OPENAI_API_KEY:
            missing["OPENAI_API_KEY"] = "Required for OpenAI provider"
        elif cls.EVA_LLM_PROVIDER == "anthropic" and not cls.ANTHROPIC_API_KEY:
            missing["ANTHROPIC_API_KEY"] = "Required for Anthropic provider"

        # Check Google credentials files
        google_creds = {
            "GOOGLE_GMAIL_CREDENTIALS_FILE": cls.GOOGLE_GMAIL_CREDENTIALS_FILE,
            "GOOGLE_CALENDAR_CREDENTIALS_FILE": cls.GOOGLE_CALENDAR_CREDENTIALS_FILE,
            "GOOGLE_TASKS_CREDENTIALS_FILE": cls.GOOGLE_TASKS_CREDENTIALS_FILE,
            "GOOGLE_DRIVE_CREDENTIALS_FILE": cls.GOOGLE_DRIVE_CREDENTIALS_FILE,
        }

        for var_name, file_path in google_creds.items():
            if file_path and not Path(file_path).exists():
                warnings[var_name] = f"File not found: {file_path}"

        return {"missing": missing, "warnings": warnings}

    @classmethod
    def get_safe_dict(cls) -> Dict[str, Any]:
        """Get configuration as dictionary with sensitive values masked"""
        config = {}
        for key in dir(cls):
            if key.startswith("_") or key in ["validate", "get_safe_dict", "mongodb_url"]:
                continue
            value = getattr(cls, key)
            if callable(value):
                continue

            # Mask sensitive values
            if "KEY" in key or "TOKEN" in key or "SECRET" in key:
                if value:
                    config[key] = f"***{value[-4:]}" if len(str(value)) > 4 else "***"
                else:
                    config[key] = None
            else:
                config[key] = value

        return config


# Create a singleton instance
config = EnvironmentConfig()
