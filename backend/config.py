from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    database_url: str | None = None
    postgres_user: str = "vista_user"
    postgres_password: str = "change_me"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "vista"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "llama3.2:3b"
    indictrans2_model_name: str = ""
    indictrans2_cache_dir: str | None = None
    indictrans2_local_files_only: bool = True
    indictrans2_device: str = "auto"
    indictrans2_onnx_path: str | None = None
    phrase_bank_path: str | None = None
    vosk_model_path: str | None = None
    vosk_english_model_path: str | None = None
    vosk_sample_rate: int = 16000

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
    )

    @property
    def sqlalchemy_database_url(self) -> str:
        return f"sqlite:///{PROJECT_ROOT / 'data' / 'vista.db'}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
