from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from dotenv import load_dotenv
from typing import Optional
import os

load_dotenv()

class JWTSettings(BaseSettings):
    secret: str = Field(default_factory=lambda: os.getenv("JWT_SECRET", "super_secret_key_change_me"), validation_alias="JWT_SECRET")
    algorithm: str = Field(default_factory=lambda: os.getenv("JWT_ALGORITHM", "HS256"), validation_alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default_factory=lambda: int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")), validation_alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default_factory=lambda: int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30")), validation_alias="REFRESH_TOKEN_EXPIRE_DAYS")
    model_config = SettingsConfigDict(extra="ignore")

class DatabaseSettings(BaseSettings):
    mongo_uri: str = Field(default_factory=lambda: os.getenv("MONGO_URI", "mongodb://localhost:27017"), validation_alias="MONGO_URI")
    database_name: str = Field(default_factory=lambda: os.getenv("DATABASE_NAME", "fluxa"), validation_alias="DATABASE_NAME")

class CacheSettings(BaseSettings):
    ttl: int = Field(default_factory=lambda: int(os.getenv("CACHE_TTL", "300")), validation_alias="CACHE_TTL")

class TemporalSettings(BaseSettings):
    host: str = Field(default_factory=lambda: os.getenv("TEMPORAL_HOST", "localhost:7233"), validation_alias="TEMPORAL_HOST")

class OpenRouterSettings(BaseSettings):
    api_key: Optional[str] = Field(default=None, validation_alias="OPENROUTER_API_KEY")
    base_url: str = Field(default="https://openrouter.ai/api/v1", validation_alias="OPENROUTER_BASE_URL")
    model_config = SettingsConfigDict(extra="ignore")

class Settings(BaseSettings):
    app_name: str = Field(default_factory=lambda: os.getenv("APP_NAME", "Fluxa"), validation_alias="APP_NAME")
    env: str = Field(default_factory=lambda: os.getenv("ENV", "development"), validation_alias="ENV")
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173", "http://127.0.0.1:3000"],
        validation_alias="CORS_ORIGINS"
    )
    
    jwt: JWTSettings = JWTSettings()
    db: DatabaseSettings = DatabaseSettings()
    cache: CacheSettings = CacheSettings()
    temporal: TemporalSettings = TemporalSettings()
    openrouter: OpenRouterSettings = OpenRouterSettings()

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    def validate_production_configuration(self):
        """
        D.2 Complete Production Configuration Contract Validation (Fail-Closed).
        Verifies all mandatory production invariants: CORS, JWT secrets & strength,
        database URI, Temporal host, and debug/development environment parameters.
        Raises RuntimeError on any invariant violation.
        """
        env_val = str(self.env).lower()
        if env_val in ("production", "prod"):
            # Invariant 1: Block wildcard or localhost CORS origins in production
            if not self.cors_origins:
                raise RuntimeError("D.2 Production Config Violation: CORS_ORIGINS list cannot be empty in ENV=production.")
            for origin in self.cors_origins:
                if origin == "*" or "localhost" in origin or "127.0.0.1" in origin:
                    raise RuntimeError(
                        f"D.2 Production Config Violation: Unsafe CORS origin '{origin}' configured for ENV=production."
                    )
            
            # Invariant 2: JWT Secret strength and placeholder rejection
            insecure_placeholders = {
                "super_secret_key_change_me", "change_me", "secret", "123456",
                "admin", "password", "default", "fluxa_secret", "jwt_secret_key"
            }
            if not self.jwt.secret or self.jwt.secret.lower() in insecure_placeholders:
                raise RuntimeError("D.2 Production Config Violation: Insecure placeholder JWT_SECRET configured for ENV=production.")
            if len(self.jwt.secret) < 16:
                raise RuntimeError("D.2 Production Config Violation: Weak JWT_SECRET (must be at least 16 characters long) for ENV=production.")

            # Invariant 3: Mandatory Database Configuration Check
            if not self.db.mongo_uri or "localhost" in self.db.mongo_uri or "127.0.0.1" in self.db.mongo_uri:
                raise RuntimeError("D.2 Production Config Violation: Database MONGO_URI must not point to localhost/127.0.0.1 in ENV=production.")
            if not self.db.database_name:
                raise RuntimeError("D.2 Production Config Violation: DATABASE_NAME must be specified for ENV=production.")

            # Invariant 4: Mandatory Temporal Configuration Check
            if not self.temporal.host or "localhost" in self.temporal.host or "127.0.0.1" in self.temporal.host:
                raise RuntimeError("D.2 Production Config Violation: TEMPORAL_HOST must not point to localhost/127.0.0.1 in ENV=production.")

        # Always validate OpenRouter key format and fake values regardless of env
        if self.openrouter.api_key:
            fake_keys = {"sk-fake", "test-key", "mock-key", "dummy-key", "change-me", "super_secret_key_change_me"}
            if self.openrouter.api_key.lower() in fake_keys or len(self.openrouter.api_key) < 10:
                raise RuntimeError("OpenRouter API Key configuration error: Fake or insecure API key detected.")

settings = Settings()
settings.validate_production_configuration()


