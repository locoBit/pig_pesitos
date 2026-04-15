from datetime import datetime

import pendulum

from pig_pesitos.constants import REPORT_PERIODS
from pig_pesitos.repositories.database import ExpenseRecord
from pig_pesitos.services.report_service import ReportService


class FakeDB:
    def __init__(self) -> None:
        self._expenses: list[tuple[int, ExpenseRecord]] = []
        self._monthly_limits: dict[int, float] = {}

    def add_expense(self, user_id: int, record: ExpenseRecord) -> None:
        self._expenses.append((user_id, record))

    def set_monthly_limit(self, user_id: int, limit: float) -> None:
        self._monthly_limits[user_id] = limit

    def get_expenses_between(self, user_id, start_range, end_range, *, ascending=True):
        rows = [
            record
            for uid, record in self._expenses
            if uid == user_id and start_range <= record.timestamp <= end_range
        ]
        return sorted(rows, key=lambda r: r.timestamp, reverse=not ascending)

    def get_monthly_limit(self, user_id: int):
        return self._monthly_limits.get(user_id)


def test_get_period_range_day(monkeypatch) -> None:
    fixed_now = pendulum.datetime(2024, 1, 15, 12, 0, tz="UTC")
    monkeypatch.setattr("pig_pesitos.services.report_service.pendulum.now", lambda *_: fixed_now)

    service = ReportService(FakeDB())

    start, end = service.get_period_range("day")

    assert start == fixed_now.start_of("day")
    assert end == fixed_now.end_of("day")


def test_get_period_range_month(monkeypatch) -> None:
    fixed_now = pendulum.datetime(2024, 1, 15, 12, 0, tz="UTC")
    monkeypatch.setattr("pig_pesitos.services.report_service.pendulum.now", lambda *_: fixed_now)

    service = ReportService(FakeDB())

    start, end = service.get_period_range("month")

    assert start == fixed_now.start_of("month")
    assert end == fixed_now.end_of("month")


def test_get_percentage_report_data_includes_limit_and_label(monkeypatch) -> None:
    fixed_now = pendulum.datetime(2024, 1, 10, 12, 0, tz="UTC")
    monkeypatch.setattr("pig_pesitos.services.report_service.pendulum.now", lambda *_: fixed_now)

    db = FakeDB()
    service = ReportService(db)

    record = ExpenseRecord(
        amount=10,
        concept="test",
        category="alimentos",
        timestamp=fixed_now,
    )
    db.add_expense(user_id=1, record=record)
    db.set_monthly_limit(1, 100.0)

    expenses, period_label, monthly_limit = service.get_percentage_report_data(1, "month")

    assert expenses == [record]
    assert period_label == REPORT_PERIODS["month"]
    assert monthly_limit == 100.0


def test_get_detailed_report_data_uses_same_range(monkeypatch) -> None:
    fixed_now = pendulum.datetime(2024, 1, 10, 12, 0, tz="UTC")
    monkeypatch.setattr("pig_pesitos.services.report_service.pendulum.now", lambda *_: fixed_now)

    db = FakeDB()
    service = ReportService(db)

    record = ExpenseRecord(
        amount=20,
        concept="otro",
        category="servicios",
        timestamp=fixed_now,
    )
    db.add_expense(user_id=2, record=record)
    db.set_monthly_limit(2, 50.0)

    rows, period_label, monthly_limit = service.get_detailed_report_data(2, "month")

    assert rows == [record]
    assert period_label == REPORT_PERIODS["month"]
    assert monthly_limit == 50.0
