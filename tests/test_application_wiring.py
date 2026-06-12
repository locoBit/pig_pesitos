import asyncio

from telegram.ext import Application

from pig_pesitos.bot.app import build_application, log_error


def run(coro):
    return asyncio.run(coro)


class DummyError:
    pass


def test_build_application_registers_handlers_and_error_handler(monkeypatch):
    """Smoke-test that build_application wires handlers and error handler.

    We monkeypatch out DB and token loading so we don't need real infra.
    """

    class DummyDB:
        def __init__(self, *_args, **_kwargs):  # pragma: no cover - trivial
            pass

        def initialize(self):  # pragma: no cover - trivial
            return None

    def fake_get_settings():  # pragma: no cover - trivial
        return {
            "database_url": "postgresql://user:pass@localhost:5432/db",
            "bot_token": "123:ABC",
            "environment": "test",
            "log_level": "DEBUG",
            "sentry_dsn": None,
            "sentry_environment": "test",
        }

    # Patch dependencies used inside build_application
    monkeypatch.setattr("pig_pesitos.bot.app.DatabaseManager", DummyDB)
    monkeypatch.setattr("pig_pesitos.bot.app.get_settings", fake_get_settings)

    app = build_application()
    assert isinstance(app, Application)

    # We expect several handler groups to be registered
    assert app.handlers  # not empty

    # Error handler should include our log_error function (stored as plain callbacks)
    assert log_error in app.error_handlers


def test_log_error_does_not_crash(caplog):
    class DummyUser:
        def __init__(self) -> None:
            self.id = 1

    class DummyUpdate:
        def __init__(self) -> None:
            self.effective_user = DummyUser()

    class DummyContext:
        def __init__(self) -> None:
            self.error = DummyError()

    update = DummyUpdate()
    context = DummyContext()

    with caplog.at_level("ERROR"):
        run(log_error(update, context))

    # Should have logged an exception message mentioning our DummyError
    assert any("DummyError" in message for message in caplog.text.splitlines())
