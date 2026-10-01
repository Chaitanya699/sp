"""
NIM Sentinel Core Configuration Module

Loads and validates all configuration from YAML files and environment variables.
Uses Pydantic Settings for type-safe configuration management.
"""

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ModelConfig(BaseSettings):
    """Configuration for a single model role."""
    primary: str
    fallback: str = ""
    primary_unverified: bool = False
    fallback_unverified: bool = False
    temperature: float = 0.1
    max_tokens: int = 4096
    timeout_seconds: int = 30
    max_retries: int = 3
    note: str = ""

    model_config = SettingsConfigDict(extra="allow")


class ModelRegistryConfig(BaseSettings):
    """Complete model registry configuration."""
    model_registry: dict[str, ModelConfig] = Field(default_factory=dict)
    model_metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = SettingsConfigDict(extra="allow")


class GuardrailsConfig(BaseSettings):
    """Guardrails configuration."""
    input_guards: dict[str, Any] = Field(default_factory=dict)
    output_guards: dict[str, Any] = Field(default_factory=dict)
    tool_safety: dict[str, Any] = Field(default_factory=dict)
    governance: dict[str, Any] = Field(default_factory=dict)

    model_config = SettingsConfigDict(extra="allow")


class AgentsConfig(BaseSettings):
    """Agent configuration."""
    supervisor: dict[str, Any] = Field(default_factory=dict)
    rag_agent: dict[str, Any] = Field(default_factory=dict)
    data_analyst: dict[str, Any] = Field(default_factory=dict)
    vision_agent: dict[str, Any] = Field(default_factory=dict)
    speech_agent: dict[str, Any] = Field(default_factory=dict)
    web_research_agent: dict[str, Any] = Field(default_factory=dict)
    action_agent: dict[str, Any] = Field(default_factory=dict)
    critic: dict[str, Any] = Field(default_factory=dict)
    memory: dict[str, Any] = Field(default_factory=dict)
    hitl: dict[str, Any] = Field(default_factory=dict)

    model_config = SettingsConfigDict(extra="allow")


class EvalThresholdsConfig(BaseSettings):
    """Evaluation thresholds configuration."""
    components: dict[str, Any] = Field(default_factory=dict)
    end_to_end: dict[str, Any] = Field(default_factory=dict)
    regression: dict[str, Any] = Field(default_factory=dict)
    redteam: dict[str, Any] = Field(default_factory=dict)
    settings: dict[str, Any] = Field(default_factory=dict)

    model_config = SettingsConfigDict(extra="allow")


class Settings(BaseSettings):
    """Main application settings loaded from environment and .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # NVIDIA API
    nvidia_api_key: str = Field(default="", description="NVIDIA API Key from build.nvidia.com")

    # LangSmith
    langsmith_api_key: str = Field(default="", description="LangSmith API Key")
    langsmith_tracing: bool = Field(default=True, description="Enable LangSmith tracing")
    langsmith_project: str = Field(default="nim-sentinel-dev", description="LangSmith project name")
    langsmith_endpoint: str = Field(default="https://api.smith.langchain.com", description="LangSmith endpoint")

    # MongoDB
    mongodb_uri: str = Field(default="mongodb://localhost:27017", description="MongoDB connection URI")
    mongodb_database: str = Field(default="nim_sentinel", description="MongoDB database name")

    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0", description="Redis connection URL")

    # JWT Authentication
    jwt_secret_key: str = Field(default="", description="JWT secret key")
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    jwt_expiration_minutes: int = Field(default=60, description="JWT token expiration in minutes")

    # API
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, description="API port")
    api_workers: int = Field(default=4, description="Number of API workers")
    api_reload: bool = Field(default=True, description="Enable auto-reload in development")

    # Logging
    log_level: str = Field(default="INFO", description="Log level")
    log_format: str = Field(default="json", description="Log format (json/console)")

    # Guardrails
    guardrails_enabled: bool = Field(default=True, description="Enable guardrails")
    guardrails_config_path: str = Field(default="configs/guardrails.yaml", description="Guardrails config path")

    # Evaluation
    eval_enabled: bool = Field(default=True, description="Enable evaluation")
    eval_thresholds_path: str = Field(default="configs/eval_thresholds.yaml", description="Eval thresholds config path")

    # Feature Flags
    feature_vision: bool = Field(default=True, description="Enable vision agent")
    feature_speech: bool = Field(default=False, description="Enable speech agent")
    feature_web_research: bool = Field(default=True, description="Enable web research agent")
    feature_action_agent: bool = Field(default=True, description="Enable action agent")

    # Computed paths
    config_dir: Path = Field(default=Path("configs"), description="Config directory")

    @field_validator("nvidia_api_key", "jwt_secret_key", mode="before")
    @classmethod
    def validate_required(cls, v: str) -> str:
        if not v or v.startswith("your_") or v == "change-in-production":
            raise ValueError("Required secret not configured - check .env file")
        return v


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


def load_yaml_config(path: str | Path) -> dict[str, Any]:
    """Load YAML configuration file."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@lru_cache
def get_model_registry() -> ModelRegistryConfig:
    """Load model registry from YAML."""
    settings = get_settings()
    config_path = settings.config_dir / "models.yaml"
    data = load_yaml_config(config_path)
    return ModelRegistryConfig(**data)


@lru_cache
def get_guardrails_config() -> GuardrailsConfig:
    """Load guardrails configuration from YAML."""
    settings = get_settings()
    config_path = settings.config_dir / "guardrails.yaml"
    data = load_yaml_config(config_path)
    return GuardrailsConfig(**data)


@lru_cache
def get_agents_config() -> AgentsConfig:
    """Load agents configuration from YAML."""
    settings = get_settings()
    config_path = settings.config_dir / "agents.yaml"
    data = load_yaml_config(config_path)
    return AgentsConfig(**data)


@lru_cache
def get_eval_thresholds() -> EvalThresholdsConfig:
    """Load evaluation thresholds from YAML."""
    settings = get_settings()
    config_path = settings.config_dir / "eval_thresholds.yaml"
    data = load_yaml_config(config_path)
    return EvalThresholdsConfig(**data)


def get_model_config(role: str) -> ModelConfig:
    """Get model configuration for a specific role."""
    registry = get_model_registry()
    if role not in registry.model_registry:
        raise ValueError(f"Unknown model role: {role}. Available: {list(registry.model_registry.keys())}")
    return registry.model_registry[role]


def get_available_model_roles() -> list[str]:
    """Get list of all configured model roles."""
    registry = get_model_registry()
    return list(registry.model_registry.keys())
