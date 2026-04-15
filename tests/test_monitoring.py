import os

from pig_pesitos.utils.monitoring import init_sentry


class DummySentry:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def __call__(self, **kwargs):
        self.calls.append(kwargs)


def test_init_sentry_no_dsn(monkeypatch) -> None:
    monkeypatch.delenv("SENTRY_DSN", raising=False)

    # Should be a no-op without raising
    init_sentry()


def test_init_sentry_with_dsn(monkeypatch) -> None:
    dummy = DummySentry()
    monkeypatch.setenv("SENTRY_DSN", "http://example.com/123")
    monkeypatch.setenv("SENTRY_ENVIRONMENT", "test")
    monkeypatch.setattr("pig_pesitos.utils.monitoring.sentry_sdk.init", dummy)

    init_sentry()

    assert len(dummy.calls) == 1
    call = dummy.calls[0]
    assert call["dsn"] == "http://example.com/123"
    assert call["environment"] == "test"
    assert call["traces_sample_rate"] == 0.0
