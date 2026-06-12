import asyncio

import pytest

from pig_pesitos.bot.handlers import BotHandlers
from pig_pesitos.constants import (
    AMOUNT,
    CATEGORY,
    CONCEPT,
    LIMIT_AMOUNT,
    REPORT_PERIOD,
    REPORT_TYPE,
)


def run(coro):
    """Run an async coroutine in a fresh event loop.

    We keep tests sync-style so we don't depend on pytest-asyncio in all
    environments, but still exercise the real async handlers.
    """

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

    async def reply_document(self, *args, **kwargs) -> None:  # type: ignore[override]
        # For handler tests we don't care about actual documents
        self.replies.append(("<document>", kwargs))


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


class FakeExpenseService:
    def __init__(self) -> None:
        self.created: list[tuple[int, float, str, str]] = []
        self.limits: dict[int, float] = {}

    def create_expense(self, user_id: int, amount: float, concept: str, category: str) -> float:
        self.created.append((user_id, amount, concept, category))
        # Just echo amount as total for testing
        return amount

    def set_monthly_limit(self, user_id: int, amount: float) -> None:
        self.limits[user_id] = amount

    def get_monthly_limit(self, user_id: int):  # pragma: no cover - helper
        return self.limits.get(user_id)

    def get_monthly_usage(self, user_id: int):  # used by _check_monthly_limit_and_warn
        limit = self.limits.get(user_id)
        if limit is None:
            return None, 0.0
        # Default to 50% usage to avoid warnings unless tests override it.
        usage_ratio = getattr(self, "usage_ratio", 0.5)
        return limit, limit * usage_ratio

    def delete_user_data(self, user_id: int) -> None:  # pragma: no cover - not used here
        self.limits.pop(user_id, None)


class FakeReportService:
    def __init__(self) -> None:
        self.percentage_calls: list[tuple[int, str]] = []
        self.detail_calls: list[tuple[int, str]] = []

    def get_percentage_report_data(self, user_id: int, report_period: str):
        self.percentage_calls.append((user_id, report_period))
        return [], "este mes", None

    def get_detailed_report_data(self, user_id: int, report_period: str):
        self.detail_calls.append((user_id, report_period))
        return [], "este mes", None


def test_start_handler_sends_welcome_message() -> None:
    handlers = BotHandlers(FakeExpenseService(), FakeReportService())
    update = DummyUpdate(text="/start", user_id=42)
    context = DummyContext()

    run(handlers.start(update, context))

    assert len(update.message.replies) == 1
    text, kwargs = update.message.replies[0]
    assert "Hola" in text
    assert "Usa /gasto" in text


def test_expense_flow_happy_path() -> None:
    expense_service = FakeExpenseService()
    handlers = BotHandlers(expense_service, FakeReportService())
    context = DummyContext()

    # /gasto
    update = DummyUpdate(text="/gasto")
    state = run(handlers.expense_command(update, context))
    assert state == AMOUNT
    assert "Por favor escribe el monto" in update.message.replies[0][0]

    # amount_input
    update_amount = DummyUpdate(text="25.50")
    state = run(handlers.amount_input(update_amount, context))
    assert state == CONCEPT
    assert context.user_data["amount"] == 25.50

    # concept_input
    update_concept = DummyUpdate(text="comida")
    state = run(handlers.concept_input(update_concept, context))
    assert state == CATEGORY

    # category_input
    update_category = DummyUpdate(text="alimentos")
    state = run(handlers.category_input(update_category, context))
    assert state == -1  # ConversationHandler.END == -1

    # Expense service should have been called once
    assert len(expense_service.created) == 1
    user_id, amount, concept, category = expense_service.created[0]
    assert amount == 25.50
    assert concept == "comida"
    assert category == "alimentos"


def test_expense_flow_invalid_amount_stays_in_state() -> None:
    handlers = BotHandlers(FakeExpenseService(), FakeReportService())
    context = DummyContext()

    update = DummyUpdate(text="not-a-number")

    state = run(handlers.amount_input(update, context))

    assert state == AMOUNT
    text, _ = update.message.replies[0]
    assert "Formato inválido" in text


def test_report_flow_percentage_calls_service() -> None:
    report_service = FakeReportService()
    handlers = BotHandlers(FakeExpenseService(), report_service)
    context = DummyContext()

    # /reporte
    update = DummyUpdate(text="/reporte")
    state = run(handlers.report_command(update, context))
    assert state == REPORT_PERIOD

    # choose month (matching REPORT_PERIODS values)
    update_period = DummyUpdate(text="Este mes")
    state = run(handlers.report_period_input(update_period, context))
    assert state == REPORT_TYPE

    # choose percentage
    update_type = DummyUpdate(text="Porcentajes")
    state = run(handlers.report_type_input(update_type, context))
    assert state == -1  # ConversationHandler.END

    assert report_service.percentage_calls == [(1, "month")]


def test_limit_flow_happy_path() -> None:
    expense_service = FakeExpenseService()
    handlers = BotHandlers(expense_service, FakeReportService())
    context = DummyContext()

    # /limite
    update = DummyUpdate(text="/limite")
    state = run(handlers.limit_command(update, context))
    assert state == LIMIT_AMOUNT

    # provide valid limit
    update_limit = DummyUpdate(text="1000.00")
    state = run(handlers.limit_amount_input(update_limit, context))
    assert state == -1  # ConversationHandler.END

    assert expense_service.limits[1] == 1000.00
