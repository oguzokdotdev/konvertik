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

    ffmpeg_path: str = "ffmpeg"
    ffprobe_path: str = "ffprobe"
    ffprobe_timeout_seconds: int = 20
    ffmpeg_timeout_seconds: int = 1800

    max_parallel_conversions: int = 1
    cleanup_interval_seconds: int = 60

    free_file_ttl_minutes: int = 10
    pro_file_ttl_minutes: int = 30

    free_ffmpeg_threads: int = 1
    free_process_nice: int = 15
    pro_ffmpeg_threads: int = 2
    pro_process_nice: int = 5

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


settings = Settings()
