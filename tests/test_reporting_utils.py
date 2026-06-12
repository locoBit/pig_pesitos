from datetime import datetime
from pathlib import Path

from pig_pesitos.repositories.database import ExpenseRecord
from pig_pesitos.utils.reporting import build_pdf_report, format_timestamp


def test_format_timestamp_uses_utc() -> None:
    ts = datetime(2024, 1, 1, 12, 0, 0)

    formatted = format_timestamp(ts)

    assert formatted.startswith("2024-01-01 12:00:")


def test_build_pdf_report_fallback(monkeypatch) -> None:
    # Force fallback path regardless of reportlab installation
    monkeypatch.setattr(
        "pig_pesitos.utils.reporting.REPORT_PDF_ENABLED", False, raising=False
    )

    record = ExpenseRecord(
        amount=10,
        concept="test",
        category="alimentos",
        timestamp=datetime.utcnow(),
    )

    result = build_pdf_report([record], "este mes", "No definido")

    assert result is None


def test_build_pdf_report_success(monkeypatch, tmp_path) -> None:
    # Fake canvas and letter so we don't depend on reportlab internals
    class DummyCanvas:
        def __init__(self, *_args, **_kwargs) -> None:
            self.calls = []

        def setFont(self, *args, **kwargs):  # noqa: N802
            self.calls.append(("setFont", args, kwargs))

        def drawString(self, *args, **kwargs):  # noqa: N802
            self.calls.append(("drawString", args, kwargs))

        def showPage(self, *args, **kwargs):  # noqa: N802
            self.calls.append(("showPage", args, kwargs))

        def save(self, *args, **kwargs):  # noqa: N802
            self.calls.append(("save", args, kwargs))

    monkeypatch.setattr(
        "pig_pesitos.utils.reporting.REPORT_PDF_ENABLED", True, raising=False
    )
    monkeypatch.setattr(
        "pig_pesitos.utils.reporting.canvas", type("C", (), {"Canvas": DummyCanvas})
    )
    monkeypatch.setattr("pig_pesitos.utils.reporting.letter", (0, 800))

    record = ExpenseRecord(
        amount=15,
        concept="comida",
        category="alimentos",
        timestamp=datetime.utcnow(),
    )

    pdf_path = build_pdf_report([record], "este mes", "No definido")

    assert pdf_path is not None
    assert Path(pdf_path).exists()
