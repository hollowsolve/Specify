"""
Configuration management for the Specify API.

Environment-based configuration with sensible defaults for development
and production deployments.
"""

import os
from functools import lru_cache
from typing import List, Optional

from pydantic import validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # Basic app settings
    app_name: str = "Specify API"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000

    # CORS settings - can be overridden via SPECIFY_CORS_ORIGINS environment variable
    cors_origins: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "https://localhost:3000",
        "https://localhost:3001",
    ]

    # Security settings
    allowed_hosts: Optional[List[str]] = None
    api_key: Optional[str] = None

    # Session management
    session_timeout_minutes: int = 30
    max_sessions_per_user: int = 10
    session_cleanup_interval_minutes: int = 5

    # Redis settings (optional)
    redis_url: Optional[str] = None
    redis_enabled: bool = False

    # Rate limiting
    rate_limit_enabled: bool = True
    rate_limit_requests_per_minute: int = 100

    # Logging
    log_level: str = "INFO"
    log_file: str = "api.log"

    # LLM Configuration (inherited from existing system)
    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    default_llm_provider: str = "anthropic"

    # Processing settings
    max_parallel_agents: int = 4
    enable_parallel_execution: bool = True
    analysis_timeout_seconds: int = 300
    specification_timeout_seconds: int = 600
    refinement_timeout_seconds: int = 300
    dispatch_timeout_seconds: int = 1800

    # File upload settings
    max_file_size_mb: int = 50
    allowed_file_types: List[str] = [".txt", ".md", ".json", ".yaml", ".yml"]

    @validator("cors_origins", pre=True)
    def parse_cors_origins(cls, v):
        """Parse CORS origins from environment variable."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @validator("allowed_hosts", pre=True)
    def parse_allowed_hosts(cls, v):
        """Parse allowed hosts from environment variable."""
        if isinstance(v, str):
            return [host.strip() for host in v.split(",")]
        return v

    @validator("allowed_file_types", pre=True)
    def parse_file_types(cls, v):
        """Parse allowed file types from environment variable."""
        if isinstance(v, str):
            return [ext.strip() for ext in v.split(",")]
        return v

    class Config:
        env_file = ".env"
        env_prefix = "SPECIFY_"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()


# Development configuration
class DevelopmentSettings(Settings):
    """Development-specific settings."""
    debug: bool = True
    log_level: str = "DEBUG"
    cors_origins: List[str] = ["*"]  # Allow all origins in development


# Production configuration
class ProductionSettings(Settings):
    """Production-specific settings."""
    debug: bool = False
    log_level: str = "INFO"
    rate_limit_enabled: bool = True
    allowed_hosts: List[str] = []  # Should be set in production


def get_environment_settings() -> Settings:
    """Get settings based on environment."""
    env = os.getenv("SPECIFY_ENVIRONMENT", "development").lower()

    if env == "production":
        return ProductionSettings()
    elif env == "development":
        return DevelopmentSettings()
    else:
        return Settings()


# Export configuration functions
__all__ = [
    "Settings",
    "get_settings",
    "get_environment_settings",
    "DevelopmentSettings",
    "ProductionSettings"
]