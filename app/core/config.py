from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DATABASE_URL: str = (
        "postgresql+psycopg://postgres:postgres@127.0.0.1:5432/tokenledger"
    )
    API_KEY: str = Field(min_length=1)

    @property
    def database_url(self) -> str:
        return self.DATABASE_URL

    @property
    def api_key(self) -> str:
        return self.API_KEY


@lru_cache
def get_settings() -> Settings:
    return Settings()
