# Copyright (c) 2026 Benjamin Marchand
# Licensed under the PolyForm Noncommercial License 1.0.0

# Centralized configuration for FableStack project

import logging
import logging.handlers
import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from dotenv import load_dotenv

from back.models.api.game import LLMConfig, WorldConfig

# Load environment variables from the root .env file
# We are in back/config.py, so root is two levels up if run as module,
# but cleaner to just look for .env in the parent of 'back' directory or current dir.
# The project root is the parent of the directory containing this file.
project_root = Path(__file__).parent.parent
load_dotenv(project_root / ".env")

class Config:
    """Centralized configuration class using a YAML file."""

    def __init__(self, config_file: str = "config.yaml"):
        self.config_file = Path(__file__).parent / config_file
        self._config: Dict[str, Any] = {}
        self._logger: Optional[logging.Logger] = None
        self._load_config()
        self._setup_logging()

    def _load_config(self) -> None:
        """Loads configuration from the YAML file."""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f) or {}
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file '{self.config_file}' not found")
        except yaml.YAMLError as e:
            raise ValueError(f"Syntax error in configuration file: {e}")

    def get_llm_config(self) -> LLMConfig:
        """
        ### get_llm_config
        **Description :** Retourne la configuration du modèle LLM.
        **Returns :**
        - (LLMConfig) : Configuration avec model, api_endpoint, api_key, token_limit, keep_last_n_messages
        """
        llm_config = self._config.get("llm", {})

        # Override with environment variables if they exist
        return LLMConfig(
            model=llm_config.get("model", os.environ.get("DEEPSEEK_API_MODEL")),
            api_endpoint=llm_config.get("api_endpoint", os.environ.get("DEEPSEEK_API_BASE_URL")),
            api_key=os.environ.get(llm_config.get("api_key")),
            token_limit=llm_config.get("token_limit", os.environ.get("LLM_TOKEN_LIMIT")),
            keep_last_n_messages=llm_config.get("keep_last_n_messages", os.environ.get("LLM_KEEP_LAST_N_MESSAGES"))
        )

    def get_data_dir(self) -> str:
        """
        ### get_data_dir
        **Description:** Returns the data directory path used by the application. Can be overridden by the DATA_DIR environment variable.
        **Parameters:**
        - None
        **Returns:**
        - (str): Absolute path of the data directory to use.
        """
        # Priority: environment variable > YAML config > default value
        data_dir = os.environ.get("DATA_DIR")
        if not data_dir:
            data_dir = self._config.get("data", {}).get("directory", "gamedata")

        return os.path.abspath(os.path.join(os.path.dirname(__file__), data_dir))

    def get_app_config(self) -> Dict[str, Any]:
        """
        ### get_app_config
        **Description:** Returns the application configuration.
        **Returns:**
        - (Dict[str, Any]): Application configuration
        """
        return self._config.get("app", {})

    def get_logging_config(self) -> Dict[str, Any]:
        """
        ### get_logging_config
        **Description:** Returns the logging configuration.
        **Returns:**
        - (Dict[str, Any]): Logging configuration
        """
        return self._config.get("logging", {})

    def _setup_logging(self) -> None:
        """Configures the logging system according to the YAML configuration."""
        logging_config = self.get_logging_config()

        # Log level
        log_level = getattr(logging, logging_config.get("level", "INFO").upper())

        # Log format
        if logging_config.get("format", "json").lower() == "json":
            # JSON format for Grafana/Loki
            log_format = '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}'
            formatter = logging.Formatter(log_format, datefmt='%Y-%m-%dT%H:%M:%S.%fZ')
        else:
            # Standard text format
            log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            formatter = logging.Formatter(log_format)

        # Root logger configuration
        logger = logging.getLogger()
        logger.setLevel(log_level)

        # Remove existing handlers
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # File handler (optional)
        log_file = logging_config.get("file")
        if log_file:
            # Create directory if necessary
            log_file_path = Path(log_file)
            log_file_path.parent.mkdir(parents=True, exist_ok=True)

            # Handler with rotation
            max_size = logging_config.get("max_file_size", 10 * 1024 * 1024)  # 10MB default
            backup_count = logging_config.get("backup_count", 5)

            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=max_size,
                backupCount=backup_count,
                encoding='utf-8'
            )
            file_handler.setLevel(log_level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        # Store configured logger
        self._logger = logger

    def get_logger(self, name: str):
        """
        ### get_logger
        **Description:** Returns a configured logger with the specified name.
        **Parameters:**
        - `name` (str): Logger name (usually __name__)
        **Returns:**
        - Configured logger
        """
        return logging.getLogger(name)

    def get_image_generation_config(self) -> Dict[str, Any]:
        """
        ### get_image_generation_config
        **Description:** Returns the image generation configuration.
        **Returns:**
        - (Dict[str, Any]): Image generation configuration
        """
        return self._config.get("image_generation", {})

    def get_auth_config(self) -> Dict[str, Any]:
        """
        ### get_auth_config
        **Description:** Returns the authentication configuration (JWT, etc.).
        **Returns:**
        - (Dict[str, Any]): Auth configuration (secret_key, algorithm, expire_minutes)
        """
        return self._config.get("auth", {})

    def get_world_config(self) -> Dict[str, Any]:
        """
        ### get_world_config
        **Description:** Returns the world configuration (lore, art_style).
        **Returns:**
        - (Dict[str, Any]): World configuration
        """
        return self._config.get("world", {})

    def get_smtp_config(self) -> Dict[str, Any]:
        """
        ### get_smtp_config
        **Description:** Returns the SMTP configuration, prioritizing environment variables for sensitive data.
        **Returns:**
        - (Dict[str, Any]): SMTP configuration
        """
        smtp_conf = self._config.get("smtp", {}).copy()
        
        # Override sensitive data with environment variables
        smtp_conf["user"] = os.environ.get("SMTP_USER", smtp_conf.get("user"))
        smtp_conf["password"] = os.environ.get("SMTP_PASSWORD", smtp_conf.get("password"))
        
        # Check enabled status (env var overrides yaml)
        # Convert string 'true'/'false' to boolean if coming from env
        env_enabled = os.environ.get("SMTP_ENABLED")
        if env_enabled is not None:
            smtp_conf["enabled"] = env_enabled.lower() == "true"
        elif "enabled" not in smtp_conf:
            # The sample will have it set to true.
            smtp_conf["enabled"] = False
        
        return smtp_conf

    @property
    def world(self) -> WorldConfig:
        """
        ### world
        **Description:** Accessor for world configuration as an object.
        **Returns:**
        - (WorldConfig): World configuration object
        """
        world_data = self.get_world_config()
        # Ensure defaults if missing (though they should be in yaml)
        return WorldConfig(
            lore=world_data.get("lore", "Default Lore"),
            art_style=world_data.get("art_style", "Default Style")
        )

# Global configuration instance
config = Config()

# Compatibility functions for existing code
def get_data_dir() -> str:
    """Compatibility function for get_data_dir."""
    return config.get_data_dir()

def get_llm_config() -> LLMConfig:
    """Compatibility function for LLM configuration."""
    return config.get_llm_config()

def get_logger(name: str):
    """Compatibility function to get a configured logger."""
    return config.get_logger(name)

# Module-level logging configuration
logger = get_logger(__name__)

def get_image_generation_config() -> Dict[str, Any]:
    """Compatibility function for image generation configuration."""
    return config.get_image_generation_config()

def get_world_config() -> Dict[str, Any]:
    """Compatibility function for world configuration."""
    return config.get_world_config()

def get_smtp_config() -> Dict[str, Any]:
    """Compatibility function for SMTP configuration."""
    return config.get_smtp_config()

def load_config() -> Dict[str, Any]:
    """Compatibility function to get the full configuration dictionary."""
    return config._config
