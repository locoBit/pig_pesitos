import os
from datetime import datetime, timedelta

import pendulum
import pytest

from pig_pesitos.repositories.database import DatabaseError, DatabaseManager, ExpenseRecord


pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def db_url() -> str:
    url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL or DATABASE_URL must be set for DB integration tests")
    return url


@pytest.fixture(scope="module")
def db(db_url: str) -> DatabaseManager:
    manager = DatabaseManager(db_url)
    # For tests we accept using the legacy initializer instead of Alembic.
    # If the database is not reachable we skip the whole module to avoid
    # breaking local runs where Postgres is not running.
    try:
        manager.initialize()
    except DatabaseError:
        pytest.skip("Database not reachable for integration tests; skipping.")
    return manager


def test_insert_and_fetch_expense_roundtrip(db: DatabaseManager) -> None:
    now = pendulum.now("UTC")
    user_id = 9999

    db.insert_expense(
        user_id=user_id,
        amount=12.34,
        concept="test-int",
        category="alimentos",
        timestamp=now,
        ignore_conflicts=True,
    )

    start = now - timedelta(minutes=1)
    end = now + timedelta(minutes=1)
    records = db.get_expenses_between(user_id, start, end, ascending=True)

    assert any(
        isinstance(r, ExpenseRecord)
        and float(r.amount) == pytest.approx(12.34)
        and r.concept == "test-int"
        and r.category == "alimentos"
        for r in records
    )


def test_category_total_matches_sum(db: DatabaseManager) -> None:
    now = pendulum.now("UTC")
    user_id = 9998

    db.insert_expense(user_id, 5.0, "a", "servicios", now, ignore_conflicts=True)
    db.insert_expense(user_id, 7.5, "b", "servicios", now, ignore_conflicts=True)

    total = db.get_category_total(user_id, "servicios")

    assert total == pytest.approx(12.5)


def test_monthly_limit_upsert_and_get(db: DatabaseManager) -> None:
    user_id = 7777
    ts1 = datetime.utcnow()
    ts2 = datetime.utcnow() + timedelta(days=1)

    db.upsert_monthly_limit(user_id, 100.0, ts1)
    assert db.get_monthly_limit(user_id) == pytest.approx(100.0)

    # Update existing row
    db.upsert_monthly_limit(user_id, 150.0, ts2)
    assert db.get_monthly_limit(user_id) == pytest.approx(150.0)


def test_delete_user_data_clears_expenses_and_limit(db: DatabaseManager) -> None:
    now = pendulum.now("UTC")
    user_id = 5555

    db.insert_expense(user_id, 1.0, "x", "otros", now, ignore_conflicts=True)
    db.upsert_monthly_limit(user_id, 42.0, datetime.utcnow())

    # Sanity check before deletion
    start = now - timedelta(minutes=1)
    end = now + timedelta(minutes=1)
    assert db.get_expenses_between(user_id, start, end)
    assert db.get_monthly_limit(user_id) is not None

    db.delete_user_data(user_id)

    assert db.get_monthly_limit(user_id) is None
    assert db.get_expenses_between(user_id, start, end) == []
