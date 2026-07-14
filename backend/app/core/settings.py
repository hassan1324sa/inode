from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class JWTSettings(BaseSettings):
    secret: str = Field("super_secret_key_change_me", env="JWT_SECRET")
    algorithm: str = Field("HS256", env="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(30, env="REFRESH_TOKEN_EXPIRE_DAYS")

class DatabaseSettings(BaseSettings):
    mongo_uri: str = Field("mongodb://localhost:27017", env="MONGO_URI")
    database_name: str = Field("fluxa", env="DATABASE_NAME")

class Settings(BaseSettings):
    app_name: str = Field("Fluxa", env="APP_NAME")
    env: str = Field("development", env="ENV")
    
    jwt: JWTSettings = JWTSettings()
    db: DatabaseSettings = DatabaseSettings()

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
