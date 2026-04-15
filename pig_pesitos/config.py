import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


class ConfigError(RuntimeError):
    """Raised when a required configuration value is missing."""


@lru_cache(maxsize=1)
def get_bot_token() -> str:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise ConfigError(
            "Missing TELEGRAM_BOT_TOKEN. Add it to your environment or a local .env "
            "file."
        )
    return token


@lru_cache(maxsize=1)
def get_database_url() -> str:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        raise ConfigError(
            "Missing DATABASE_URL. Use a PostgreSQL connection string in your "
            "environment or .env file."
        )
    return database_url
