from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
import os

class Settings(BaseSettings):
    APP_NAME: str = "DriftGuard AI"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DATABASE_URL: str = "sqlite:///./driftguard.db"
    SECRET_KEY: str = "driftguard_hackathon_super_secret_key_2026"
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000"

    # Simulation defaults
    SIMULATION_INTERVAL_MS: int = 500
    FEEDBACK_DELAY_MS: int = 3000
    ADAPTIVE_LEARNING_ENABLED: bool = False
    ACTIVE_FRAUD_PATTERN: str = "standard"  # standard, high_velocity_micro, geo_mismatch, midnight_burst

    @property
    def cors_origins(self) -> List[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]

    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
