"""
Configuration management for SmartExamAI.
"""
from pydantic_settings import BaseSettings
from pydantic import Field, ConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # LLM Configuration
    openrouter_api_key: str = Field(default="dummy_key_for_testing", description="API key for OpenRouter")
    openrouter_base_url: str = Field(default="https://openrouter.ai/api/v1")
    qwen_coder_model: str = Field(default="qwen/qwen2.5-coder-32b-instruct")

    # Docker Sandbox Images
    docker_image_python: str = Field(default="python:3.11-slim")
    docker_image_c: str = Field(default="gcc:13")
    docker_image_java: str = Field(default="eclipse-temurin:17-jdk")
    docker_image_php: str = Field(default="php:8.2-cli")

    # Sandbox Resource Limits
    sandbox_cpu_limit: float = Field(default=1.0)
    sandbox_memory_limit: str = Field(default="256m")
    sandbox_timeout_seconds: int = Field(default=10)

    # Logging
    log_level: str = Field(default="INFO")
    log_file: str = Field(default="smartexamai.log")

    # Pydantic V2 Configuration
    # extra="ignore" tells Pydantic to safely ignore other environment variables 
    # (like 'api_key' or 'openrouter_key') that exist on your system but aren't defined here.
    model_config = ConfigDict(
        env_file=".env",
        env_prefix="SMARTEXAM_",
        case_sensitive=False,
        extra="ignore"  # <--- THIS FIXES THE ERROR
    )


# Instantiate settings for global access across the application
settings = Settings()