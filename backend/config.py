"""
Centralized Configuration for Marei Mekomos V7
==============================================

Single source of truth for all environment variables and settings.
Uses Pydantic for validation and type safety.
"""

import os

from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field, validator
from pathlib import Path


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables and .env file.

    Environment variables take precedence over .env file values.
    """

    # ==========================================
    #  API KEYS (Required)
    # ==========================================

    anthropic_api_key: str = Field(
        ...,
        description="Claude API key from anthropic.com",
        env="ANTHROPIC_API_KEY"
    )

    # ==========================================
    #  APPLICATION SETTINGS
    # ==========================================

    app_name: str = "Marei Mekomos"
    app_version: str = "7.0.0"
    environment: str = Field("production", env="ENVIRONMENT")

    # ==========================================
    #  SERVER SETTINGS
    # ==========================================

    host: str = Field("0.0.0.0", env="HOST")
    port: int = Field(8000, env="PORT")

    # CORS origins (comma-separated)
    cors_origins: str = Field(
        "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173",
        env="CORS_ORIGINS"
    )

    # ==========================================
    #  SEFARIA API
    # ==========================================

    sefaria_base_url: str = Field(
        "https://www.sefaria.org/api",
        env="SEFARIA_BASE_URL"
    )

    sefaria_timeout: int = Field(30, env="SEFARIA_TIMEOUT")
    sefaria_max_retries: int = Field(3, env="SEFARIA_MAX_RETRIES")

    # ==========================================
    #  CACHING
    # ==========================================

    use_cache: bool = Field(True, env="USE_CACHE")
    cache_dir: Path = Field(
        Path(__file__).parent / "cache",
        env="CACHE_DIR"
    )
    dictionary_file: Path = Field(
        Path(__file__).parent / "data" / "word_dictionary.json",
        env="DICTIONARY_FILE"
    )

    # ==========================================
    #  LOGGING
    # ==========================================

    log_level: str = Field("INFO", env="LOG_LEVEL")
    log_dir: Path = Field(
        Path(__file__).parent / "logs",
        env="LOG_DIR"
    )
    log_format: str = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    log_date_format: str = "%H:%M:%S"

    # ==========================================
    #  PIPELINE SETTINGS
    # ==========================================

    # Step 1: Transliteration
    transliteration_max_variants: int = Field(15, env="TRANSLITERATION_MAX_VARIANTS")
    transliteration_min_hits: int = Field(1, env="TRANSLITERATION_MIN_HITS")

    # Step 2: Understanding
    claude_model: str = Field("claude-sonnet-4-5-20250929", env="CLAUDE_MODEL")
    claude_max_tokens: int = Field(4000, env="CLAUDE_MAX_TOKENS")
    claude_temperature: float = Field(0.7, env="CLAUDE_TEMPERATURE")

    # Step 3: Search
    default_search_depth: str = Field("standard", env="DEFAULT_SEARCH_DEPTH")
    max_sources_per_level: int = Field(10, env="MAX_SOURCES_PER_LEVEL")

    # ==========================================
    #  TESTING/DEVELOPMENT
    # ==========================================

    test_mode: bool = Field(False, env="TEST_MODE")
    debug: bool = Field(False, env="DEBUG")
    dev_mode: bool = Field(False, env="DEV_MODE")

    # ==========================================
    #  VALIDATORS
    # ==========================================

    @validator('cors_origins')
    def parse_cors_origins(cls, v):
        """Convert comma-separated string to list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(',')]
        return v

    @validator('log_level')
    def validate_log_level(cls, v):
        """Ensure log level is valid."""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f'log_level must be one of {valid_levels}')
        return v_upper

    @validator('environment')
    def validate_environment(cls, v):
        """Ensure environment is valid."""
        valid_envs = ['development', 'staging', 'production', 'test']
        v_lower = v.lower()
        if v_lower not in valid_envs:
            raise ValueError(f'environment must be one of {valid_envs}')
        return v_lower

    @validator('anthropic_api_key')
    def validate_api_key(cls, v):
        """Ensure API key is not empty and looks valid."""
        if not v or len(v) < 10:
            raise ValueError(
                'ANTHROPIC_API_KEY is required and must be valid. '
                'Get your key from https://console.anthropic.com/'
            )
        return v

    # ==========================================
    #  COMPUTED PROPERTIES
    # ==========================================

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment == 'development' or self.dev_mode

    @property
    def is_testing(self) -> bool:
        """Check if running in test mode."""
        return self.test_mode or self.environment == 'test'

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment == 'production' and not self.dev_mode

    def ensure_directories(self):
        """Ensure all required directories exist."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.dictionary_file.parent.mkdir(parents=True, exist_ok=True)

    # ==========================================
    #  PYDANTIC CONFIG
    # ==========================================

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

        # Allow extra fields for forward compatibility
        extra = "ignore"


# ==========================================
#  GLOBAL SETTINGS INSTANCE
# ==========================================

_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Get global settings instance (singleton pattern).

    This ensures we only load the .env file once and validate once.
    """
    global _settings

    if _settings is None:
        _settings = Settings()
        _settings.ensure_directories()

    return _settings


def reload_settings() -> Settings:
    """
    Reload settings (useful for testing).
    """
    global _settings
    _settings = None
    return get_settings()


# ==========================================
#  CONVENIENCE FUNCTIONS
# ==========================================

def get_api_key() -> str:
    """Get Anthropic API key."""
    return get_settings().anthropic_api_key


def is_development() -> bool:
    """Check if in development mode."""
    return get_settings().is_development


def is_testing() -> bool:
    """Check if in test mode."""
    return get_settings().is_testing


# ==========================================
#  USAGE EXAMPLE
# ==========================================

if __name__ == "__main__":
    print("=" * 60)
    print("Marei Mekomos V7 - Configuration")
    print("=" * 60)

    try:
        settings = get_settings()

        print(f"\nEnvironment: {settings.environment}")
        print(f"Version: {settings.app_version}")
        print(f"Debug Mode: {settings.debug}")
        print(f"Test Mode: {settings.test_mode}")

        print(f"\nServer:")
        print(f"  Host: {settings.host}:{settings.port}")
        print(f"  CORS Origins: {settings.cors_origins}")

        print(f"\nAPI:")
        print(f"  Anthropic Key: {'*' * 20}...{settings.anthropic_api_key[-4:]}")
        print(f"  Claude Model: {settings.claude_model}")
        print(f"  Sefaria URL: {settings.sefaria_base_url}")

        print(f"\nPaths:")
        print(f"  Cache: {settings.cache_dir}")
        print(f"  Logs: {settings.log_dir}")
        print(f"  Dictionary: {settings.dictionary_file}")

        print(f"\nLogging:")
        print(f"  Level: {settings.log_level}")

        print("\n✅ Configuration loaded successfully!")

    except Exception as e:
        print(f"\n❌ Configuration error: {e}")
        print("\nMake sure you have a .env file with ANTHROPIC_API_KEY set.")
        exit(1)
