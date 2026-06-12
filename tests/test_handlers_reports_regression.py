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
        self.documents: list[tuple[str, dict]] = []

    async def reply_text(self, text: str, **kwargs) -> None:  # type: ignore[override]
        self.replies.append((text, kwargs))

    async def reply_document(self, *args, **kwargs) -> None:  # type: ignore[override]
        # We only care that this is called, not about actual files
        self.documents.append(("<document>", kwargs))


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


class FakeExpenseRecord:
    def __init__(self, amount: float, concept: str, category: str, timestamp) -> None:
        self.amount = amount
        self.concept = concept
        self.category = category
        self.timestamp = timestamp


class ReportServiceWithData:
    def __init__(self, expenses, period_label: str = "este mes", limit: float | None = None):
        self.expenses = expenses
        self.period_label = period_label
        self.limit = limit

    def get_percentage_report_data(self, user_id: int, report_period: str):
        return self.expenses, self.period_label, self.limit

    def get_detailed_report_data(self, user_id: int, report_period: str):
        return self.expenses, self.period_label, self.limit


class NoOpExpenseService:
    def get_monthly_usage(self, user_id: int):  # pragma: no cover - trivial
        return None, 0.0


def test_percentage_report_includes_limit_and_percentages(monkeypatch) -> None:
    # Single category, easy percentage math
    from datetime import datetime

    expenses = [
        FakeExpenseRecord(10.0, "a", "alimentos", datetime(2024, 1, 1)),
        FakeExpenseRecord(20.0, "b", "alimentos", datetime(2024, 1, 2)),
    ]
    report_service = ReportServiceWithData(expenses, period_label="este mes", limit=100.0)
    handlers = BotHandlers(NoOpExpenseService(), report_service)

    update = DummyUpdate(text="Porcentajes", user_id=1)
    context = DummyContext()
    context.user_data["report_period"] = "month"

    # Call the internal percentage_report helper directly
    run(handlers.percentage_report(update, 1, "month", "req-1"))

    assert update.message.replies, "Handler should respond"
    text, _ = update.message.replies[-1]
    lower = text.lower()
    assert "reporte porcentual" in lower
    assert "limite mensual" in lower or "límite mensual" in lower
    assert "30.00" in text  # category total
    assert "%" in text  # percentage marker


def test_detailed_report_sends_text_and_pdf(monkeypatch, tmp_path) -> None:
    from datetime import datetime

    # Two expenses, different categories to exercise sorting and formatting
    expenses = [
        FakeExpenseRecord(5.0, "cena", "alimentos", datetime(2024, 1, 3)),
        FakeExpenseRecord(15.5, "luz", "servicios", datetime(2024, 1, 4)),
    ]
    report_service = ReportServiceWithData(expenses, period_label="este mes", limit=None)
    handlers = BotHandlers(NoOpExpenseService(), report_service)

    # Patch build_pdf_report to create a dummy file
    from pig_pesitos.utils import reporting as reporting_module

    dummy_pdf = tmp_path / "dummy.pdf"
    dummy_pdf.write_bytes(b"fake-pdf")

    def fake_build_pdf_report(rows, period_label, limit_text):  # pragma: no cover - simple stub
        assert rows == expenses
        return str(dummy_pdf)

    monkeypatch.setattr(reporting_module, "build_pdf_report", fake_build_pdf_report)

    update = DummyUpdate(text="Detalle", user_id=1)
    context = DummyContext()
    context.user_data["report_period"] = "month"

    run(handlers.detailed_report(update, 1, "month", "req-2"))

    # First we should have a text reply with a table-like structure
    assert update.message.replies, "Handler should send a text report"
    text, kwargs = update.message.replies[0]
    assert "Reporte detallado" in text
    assert "Total del periodo" in text

    # And then a document with the PDF
    assert update.message.documents, "Handler should send a PDF document"
