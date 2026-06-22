from pydantic import AnyUrl, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="forbid",
    )

    database_url: PostgresDsn
    rabbitmq_url: AnyUrl
    api_key: str
    debug: bool = False

    @field_validator("api_key")
    @classmethod
    def api_key_must_not_be_default(cls, v: str) -> str:
        if v == "change-me-to-a-real-secret":
            raise ValueError("API_KEY must not be the default value. Set a real secret in .env")
        if len(v) < 16:
            raise ValueError("API_KEY must be at least 16 characters long.")
        return v


settings = Settings()
