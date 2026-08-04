from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Take Home Assessment API"
    app_version: str = "0.1.0"
    upload_dir: str = "uploads"
    max_upload_size_mb: int = 100

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
