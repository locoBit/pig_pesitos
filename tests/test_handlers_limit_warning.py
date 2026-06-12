import asyncio

from pig_pesitos.bot.handlers import BotHandlers


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


class LimitAwareExpenseService:
    def __init__(self) -> None:
        self.created: list[tuple[int, float, str, str]] = []
        self.limits: dict[int, float] = {}
        # Default usage ratio; tests can override.
        self.usage_ratio = 0.95

    def create_expense(self, user_id: int, amount: float, concept: str, category: str) -> float:
        self.created.append((user_id, amount, concept, category))
        return amount

    def set_monthly_limit(self, user_id: int, amount: float) -> None:
        self.limits[user_id] = amount

    def get_monthly_usage(self, user_id: int):
        limit = self.limits.get(user_id)
        if limit is None:
            return None, 0.0
        return limit, limit * self.usage_ratio

    def delete_user_data(self, user_id: int) -> None:  # pragma: no cover - unused
        self.limits.pop(user_id, None)


class DummyReportService:
    def get_percentage_report_data(self, *_args, **_kwargs):  # pragma: no cover
        return [], "este mes", None

    def get_detailed_report_data(self, *_args, **_kwargs):  # pragma: no cover
        return [], "este mes", None


def test_limit_warning_triggered_after_expense() -> None:
    expense_service = LimitAwareExpenseService()
    expense_service.set_monthly_limit(1, 100.0)
    handlers = BotHandlers(expense_service, DummyReportService())
    context = DummyContext()

    # Prepare user_data as if we've already collected amount/concept
    context.user_data["amount"] = 10.0
    context.user_data["concept"] = "test"

    update = DummyUpdate(text="alimentos", user_id=1)

    state = run(handlers.category_input(update, context))

    assert state == -1
    # Last reply should be the warning or at least include the warning prefix
    texts = [text for text, _ in update.message.replies]
    assert any("90%" in t for t in texts)
