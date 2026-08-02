from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from dotenv import load_dotenv
import os

load_dotenv()

class JWTSettings(BaseSettings):
    secret: str = Field(default_factory=lambda: os.getenv("JWT_SECRET", "super_secret_key_change_me"), validation_alias="JWT_SECRET")
    algorithm: str = Field(default_factory=lambda: os.getenv("JWT_ALGORITHM", "HS256"), validation_alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default_factory=lambda: int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")), validation_alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default_factory=lambda: int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30")), validation_alias="REFRESH_TOKEN_EXPIRE_DAYS")

class DatabaseSettings(BaseSettings):
    mongo_uri: str = Field(default_factory=lambda: os.getenv("MONGO_URI", "mongodb://localhost:27017"), validation_alias="MONGO_URI")
    database_name: str = Field(default_factory=lambda: os.getenv("DATABASE_NAME", "fluxa"), validation_alias="DATABASE_NAME")

class CacheSettings(BaseSettings):
    ttl: int = Field(default_factory=lambda: int(os.getenv("CACHE_TTL", "300")), validation_alias="CACHE_TTL")

class TemporalSettings(BaseSettings):
    host: str = Field(default_factory=lambda: os.getenv("TEMPORAL_HOST", "localhost:7233"), validation_alias="TEMPORAL_HOST")

class Settings(BaseSettings):
    app_name: str = Field(default_factory=lambda: os.getenv("APP_NAME", "Fluxa"), validation_alias="APP_NAME")
    env: str = Field(default_factory=lambda: os.getenv("ENV", "development"), validation_alias="ENV")
    cors_origins: list[str] = Field(
        default=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173", "http://127.0.0.1:3000"],
        validation_alias="CORS_ORIGINS"
    )
    
    jwt: JWTSettings = JWTSettings()
    db: DatabaseSettings = DatabaseSettings()
    cache: CacheSettings = CacheSettings()
    temporal: TemporalSettings = TemporalSettings()

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()


