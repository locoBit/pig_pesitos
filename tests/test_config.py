import pytest

from pig_pesitos.config import (
    ConfigError,
    get_bot_token,
    get_database_url,
    get_environment,
    get_log_level,
    get_sentry_dsn,
    get_sentry_environment,
    get_settings,
)


def test_get_bot_token_raises_when_missing(monkeypatch) -> None:
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)

    with pytest.raises(ConfigError):
        get_bot_token.cache_clear()  # type: ignore[attr-defined]
        get_bot_token()


def test_get_database_url_raises_when_missing(monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(ConfigError):
        get_database_url.cache_clear()  # type: ignore[attr-defined]
        get_database_url()


def test_get_environment_defaults_to_development(monkeypatch) -> None:
    monkeypatch.delenv("APP_ENV", raising=False)

    get_environment.cache_clear()  # type: ignore[attr-defined]
    assert get_environment() == "development"


def test_get_environment_respects_app_env(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "Production")

    get_environment.cache_clear()  # type: ignore[attr-defined]
    assert get_environment() == "production"


def test_get_log_level_defaults_by_env(monkeypatch) -> None:
    # Development: default DEBUG
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    get_environment.cache_clear()  # type: ignore[attr-defined]
    get_log_level.cache_clear()  # type: ignore[attr-defined]
    assert get_log_level() == "DEBUG"

    # Production: default INFO
    monkeypatch.setenv("APP_ENV", "production")
    get_environment.cache_clear()  # type: ignore[attr-defined]
    get_log_level.cache_clear()  # type: ignore[attr-defined]
    assert get_log_level() == "INFO"


def test_get_log_level_respects_override(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("LOG_LEVEL", "warning")
    get_environment.cache_clear()  # type: ignore[attr-defined]
    get_log_level.cache_clear()  # type: ignore[attr-defined]

    assert get_log_level() == "WARNING"


def test_sentry_helpers(monkeypatch) -> None:
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    monkeypatch.delenv("SENTRY_ENVIRONMENT", raising=False)
    monkeypatch.setenv("APP_ENV", "staging")
    for fn in (get_sentry_dsn, get_sentry_environment):
        fn.cache_clear()  # type: ignore[attr-defined]
    get_environment.cache_clear()  # type: ignore[attr-defined]

    assert get_sentry_dsn() is None
    assert get_sentry_environment() == "staging"

    monkeypatch.setenv("SENTRY_DSN", "http://example.com/123")
    monkeypatch.setenv("SENTRY_ENVIRONMENT", "prod")
    for fn in (get_sentry_dsn, get_sentry_environment):
        fn.cache_clear()  # type: ignore[attr-defined]

    assert get_sentry_dsn() == "http://example.com/123"
    assert get_sentry_environment() == "prod"


def test_get_settings_collects_values(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:ABC")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/db")
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("LOG_LEVEL", "debug")
    monkeypatch.setenv("SENTRY_DSN", "")
    monkeypatch.delenv("SENTRY_ENVIRONMENT", raising=False)

    for fn in (
        get_bot_token,
        get_database_url,
        get_environment,
        get_log_level,
        get_sentry_dsn,
        get_sentry_environment,
        get_settings,
    ):
        fn.cache_clear()  # type: ignore[attr-defined]

    settings = get_settings()

    assert settings["environment"] == "development"
    assert settings["bot_token"] == "123:ABC"
    assert settings["database_url"].startswith("postgresql://")
    assert settings["log_level"] == "DEBUG"
    assert settings["sentry_dsn"] is None
    assert settings["sentry_environment"] == "development"
