import asyncio

from pig_pesitos.bot.handlers import BotHandlers
from pig_pesitos.constants import LIMIT_AMOUNT


def run(coro):
    return asyncio.run(coro)


class DummyUser:
    def __init__(self, user_id: int = 1, first_name: str = "Test") -> None:
        self.id = user_id
        self.first_name = first_name


class DummyMessage:
    def __init__(self, text: str = "") -> None:
        self.text = text
        self.replies: list[tuple[str, dict]] = []

    async def reply_text(self, text: str, **kwargs) -> None:  # type: ignore[override]
        self.replies.append((text, kwargs))


class DummyUpdate:
    def __init__(self, text: str = "", user_id: int = 1) -> None:
        self._user = DummyUser(user_id=user_id)
        self.message = DummyMessage(text)

    @property
    def effective_user(self) -> DummyUser:  # type: ignore[override]
        return self._user


class DummyContext:
    def __init__(self) -> None:
        self.user_data: dict = {}
        self.chat_data: dict = {}


class FailingExpenseService:
    def __init__(self, *, fail_on="create_expense") -> None:
        self.fail_on = fail_on
        self.delete_calls: list[int] = []

    def create_expense(self, *_args, **_kwargs):  # pragma: no cover - helper
        from pig_pesitos.repositories.database import DatabaseError

        if self.fail_on == "create_expense":
            raise DatabaseError("boom")

    def set_monthly_limit(self, *_args, **_kwargs):  # pragma: no cover - helper
        from pig_pesitos.repositories.database import DatabaseError

        if self.fail_on == "set_monthly_limit":
            raise DatabaseError("boom")

    def get_monthly_usage(self, *_args, **_kwargs):  # pragma: no cover - helper
        return None, 0.0

    def delete_user_data(self, user_id: int) -> None:  # pragma: no cover - helper
        from pig_pesitos.repositories.database import DatabaseError

        self.delete_calls.append(user_id)
        if self.fail_on == "delete_user_data":
            raise DatabaseError("boom")


class DummyReportService:
    def get_percentage_report_data(self, *_args, **_kwargs):  # pragma: no cover
        from pig_pesitos.repositories.database import DatabaseError

        raise DatabaseError("boom")

    def get_detailed_report_data(self, *_args, **_kwargs):  # pragma: no cover
        from pig_pesitos.repositories.database import DatabaseError

        raise DatabaseError("boom")


def test_cancel_handler_clears_state_and_replies() -> None:
    handlers = BotHandlers(FailingExpenseService(), DummyReportService())
    update = DummyUpdate(text="/cancelar", user_id=1)
    context = DummyContext()
    context.user_data["amount"] = 10

    state = run(handlers.cancel(update, context))

    assert state == -1  # ConversationHandler.END
    assert context.user_data == {}
    text, _ = update.message.replies[0]
    lower = text.lower()
    assert "cancel" in lower
    assert "gasto" in lower


def test_limit_amount_db_failure_shows_friendly_message() -> None:
    expense_service = FailingExpenseService(fail_on="set_monthly_limit")
    handlers = BotHandlers(expense_service, DummyReportService())
    update = DummyUpdate(text="100.0", user_id=1)
    context = DummyContext()

    state = run(handlers.limit_amount_input(update, context))

    assert state == -1
    text, _ = update.message.replies[0]
    assert "no pudimos actualizar tu límite mensual".lower() in text.lower()


def test_forget_me_flow_confirm_yes_deletes_data() -> None:
    expense_service = FailingExpenseService(fail_on="none")
    handlers = BotHandlers(expense_service, DummyReportService())
    context = DummyContext()

    # Start flow
    update_start = DummyUpdate(text="/olvidame", user_id=5)
    state = run(handlers.forget_me(update_start, context))
    assert state == 30  # FORGET_CONFIRM

    # Confirm deletion
    update_confirm = DummyUpdate(text="Sí, borrar todo", user_id=5)
    state = run(handlers.forget_me_confirm(update_confirm, context))
    assert state == -1
    assert expense_service.delete_calls == [5]
    text, _ = update_confirm.message.replies[-1]
    assert "borramos todos tus gastos".lower() in text.lower()


def test_forget_me_flow_confirm_no_keeps_data() -> None:
    expense_service = FailingExpenseService(fail_on="none")
    handlers = BotHandlers(expense_service, DummyReportService())
    context = DummyContext()

    # Start flow
    update_start = DummyUpdate(text="/olvidame", user_id=5)
    state = run(handlers.forget_me(update_start, context))
    assert state == 30

    # Cancel deletion
    update_cancel = DummyUpdate(text="No, cancelar", user_id=5)
    state = run(handlers.forget_me_confirm(update_cancel, context))
    assert state == -1
    assert expense_service.delete_calls == []
    text, _ = update_cancel.message.replies[-1]
    assert "no borramos nada".lower() in text.lower()


def test_forget_me_flow_invalid_answer_reasks() -> None:
    handlers = BotHandlers(FailingExpenseService(fail_on="none"), DummyReportService())
    context = DummyContext()

    # Start flow
    update_start = DummyUpdate(text="/olvidame", user_id=5)
    state = run(handlers.forget_me(update_start, context))
    assert state == 30

    # Invalid answer
    update_invalid = DummyUpdate(text="tal vez", user_id=5)
    state = run(handlers.forget_me_confirm(update_invalid, context))
    assert state == 30
    text, _ = update_invalid.message.replies[-1]
    assert "por favor selecciona una de las opciones".lower() in text.lower()


def test_forget_me_flow_db_failure_on_delete() -> None:
    expense_service = FailingExpenseService(fail_on="delete_user_data")
    handlers = BotHandlers(expense_service, DummyReportService())
    context = DummyContext()

    # Start flow
    update_start = DummyUpdate(text="/olvidame", user_id=5)
    state = run(handlers.forget_me(update_start, context))
    assert state == 30

    # Confirm deletion
    update_confirm = DummyUpdate(text="Sí, borrar todo", user_id=5)
    state = run(handlers.forget_me_confirm(update_confirm, context))
    assert state == -1
    # Service was still called
    assert expense_service.delete_calls == [5]
    text, _ = update_confirm.message.replies[-1]
    assert "no pudimos borrar tus datos".lower() in text.lower()
