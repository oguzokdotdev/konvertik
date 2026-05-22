from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    app_name: str = "Konvertik"
    app_version: str = "0.1.0"
    debug: bool = False

    sqlite_db_path: str = "./data/konvertik.db"
    uploads_dir: str = "./uploads"

    free_max_file_size_mb: int = 500
    free_max_daily_conversions: int = 100

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


settings = Settings()