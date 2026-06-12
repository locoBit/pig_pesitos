import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


class ConfigError(RuntimeError):
    """Raised when a required configuration value is missing."""


def _get_required_env(key: str) -> str:
    """Fetch a required environment variable or raise ConfigError.

    This keeps all the "read from os.environ and validate" logic in one place
    so the rest of the code can stay nice and dumb.
    """

    value = os.getenv(key, "").strip()
    if not value:
        raise ConfigError(f"Missing {key}. Add it to your environment or .env file.")
    return value


@lru_cache(maxsize=1)
def get_bot_token() -> str:
    """Return the Telegram bot token.

    Exists as a thin wrapper for backwards compatibility; new code should
    prefer :func:`get_settings` when multiple values are needed.
    """

    return _get_required_env("TELEGRAM_BOT_TOKEN")


@lru_cache(maxsize=1)
def get_database_url() -> str:
    """Return the PostgreSQL database URL.

    As with :func:`get_bot_token`, this is primarily kept for compatibility.
    """

    return _get_required_env("DATABASE_URL")


@lru_cache(maxsize=1)
def get_environment() -> str:
    """Return the current runtime environment name.

    Defaults to ``"development"`` when not explicitly set. Valid values are
    not enforced here; callers can decide how strict they want to be.
    """

    value = os.getenv("APP_ENV", "development").strip().lower()
    return value or "development"


@lru_cache(maxsize=1)
def get_log_level() -> str:
    """Return the desired log level name.

    If LOG_LEVEL is not defined, we default to DEBUG in development and INFO
    otherwise. The value is normalized to upper-case.
    """

    env = get_environment()
    default = "DEBUG" if env == "development" else "INFO"
    value = os.getenv("LOG_LEVEL", default).strip().upper()
    return value or default


@lru_cache(maxsize=1)
def get_sentry_dsn() -> str | None:
    """Return the Sentry DSN if configured, otherwise ``None``."""

    dsn = os.getenv("SENTRY_DSN", "").strip()
    return dsn or None


@lru_cache(maxsize=1)
def get_sentry_environment() -> str:
    """Return the environment name to use for Sentry.

    Falls back to :func:`get_environment` when SENTRY_ENVIRONMENT is not set.
    """

    explicit = os.getenv("SENTRY_ENVIRONMENT", "").strip()
    if explicit:
        return explicit
    return get_environment()


@lru_cache(maxsize=1)
def get_settings() -> dict[str, object]:
    """Return a simple, centralized view of runtime settings.

    This deliberately returns a dict instead of a custom class to keep things
    lightweight and avoid over-engineering. Most code can still rely on the
    more focused helpers above, but when several values are needed together
    this offers a single access point.
    """

    return {
        "environment": get_environment(),
        "bot_token": get_bot_token(),
        "database_url": get_database_url(),
        "log_level": get_log_level(),
        "sentry_dsn": get_sentry_dsn(),
        "sentry_environment": get_sentry_environment(),
    }
