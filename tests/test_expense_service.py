import pendulum
import pytest

from pig_pesitos.services.expense_service import ExpenseService


class FakeDB:
    def __init__(self) -> None:
        self.inserted = []
        self.category_totals: dict[tuple[int, str], float] = {}
        self.monthly_limits: dict[int, float] = {}
        self.expenses_by_user: dict[int, list] = {}

    def insert_expense(self, user_id, amount, concept, category, timestamp, **_):
        self.inserted.append((user_id, amount, concept, category, timestamp))
        key = (user_id, category)
        self.category_totals[key] = self.category_totals.get(key, 0.0) + float(amount)
        self.expenses_by_user.setdefault(user_id, []).append((amount, timestamp))

    def get_category_total(self, user_id, category):
        return self.category_totals.get((user_id, category), 0.0)

    def upsert_monthly_limit(self, user_id, amount, timestamp):
        self.monthly_limits[user_id] = float(amount)

    def get_monthly_limit(self, user_id):
        return self.monthly_limits.get(user_id)

    def delete_user_data(self, user_id):
        self.monthly_limits.pop(user_id, None)
        self.expenses_by_user.pop(user_id, None)

    def get_expenses_between(self, user_id, start_range, end_range, *, ascending=True):
        rows = [
            SimpleExpense(amount, ts)
            for amount, ts in self.expenses_by_user.get(user_id, [])
            if start_range <= ts <= end_range
        ]
        return sorted(rows, key=lambda r: r.timestamp, reverse=not ascending)


class SimpleExpense:
    def __init__(self, amount, timestamp):
        self.amount = amount
        self.timestamp = timestamp


def test_create_expense_updates_category_total(monkeypatch) -> None:
    fixed_now = pendulum.datetime(2024, 1, 10, 12, 0, tz="UTC")
    monkeypatch.setattr(
        "pig_pesitos.services.expense_service.pendulum.now", lambda *_: fixed_now
    )

    db = FakeDB()
    service = ExpenseService(db)

    total = service.create_expense(1, 10.0, "test", "alimentos")

    assert db.inserted[0][:4] == (1, 10.0, "test", "alimentos")
    assert total == 10.0


def test_get_monthly_usage_without_limit(monkeypatch) -> None:
    fixed_now = pendulum.datetime(2024, 1, 10, 12, 0, tz="UTC")
    monkeypatch.setattr(
        "pig_pesitos.services.expense_service.pendulum.now", lambda *_: fixed_now
    )

    db = FakeDB()
    service = ExpenseService(db)

    limit, total = service.get_monthly_usage(1)

    assert limit is None
    assert total == 0.0


def test_get_monthly_usage_with_expenses(monkeypatch) -> None:
    fixed_now = pendulum.datetime(2024, 1, 15, 12, 0, tz="UTC")
    monkeypatch.setattr(
        "pig_pesitos.services.expense_service.pendulum.now", lambda *_: fixed_now
    )

    db = FakeDB()
    service = ExpenseService(db)

    # Expenses in the same month
    ts1 = fixed_now.start_of("month").add(days=1)
    ts2 = fixed_now.start_of("month").add(days=2)
    db.expenses_by_user[1] = [(5.0, ts1), (7.5, ts2)]
    db.monthly_limits[1] = 100.0

    limit, total = service.get_monthly_usage(1)

    assert limit == 100.0
    assert total == pytest.approx(12.5)


def test_set_and_get_monthly_limit(monkeypatch) -> None:
    fixed_now = pendulum.datetime(2024, 1, 10, 12, 0, tz="UTC")
    monkeypatch.setattr(
        "pig_pesitos.services.expense_service.pendulum.now", lambda *_: fixed_now
    )

    db = FakeDB()
    service = ExpenseService(db)

    service.set_monthly_limit(1, 200.0)
    assert db.monthly_limits[1] == 200.0
    assert service.get_monthly_limit(1) == 200.0


def test_delete_user_data_delegates_to_db() -> None:
    db = FakeDB()
    db.monthly_limits[1] = 50.0
    db.expenses_by_user[1] = [(5.0, pendulum.now("UTC"))]

    service = ExpenseService(db)
    service.delete_user_data(1)

    assert 1 not in db.monthly_limits
    assert 1 not in db.expenses_by_user
