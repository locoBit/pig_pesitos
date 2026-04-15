import os

import pytest

from pig_pesitos.config import ConfigError, get_bot_token, get_database_url


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
