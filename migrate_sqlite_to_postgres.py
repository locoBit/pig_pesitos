from __future__ import annotations

import os
import sqlite3
from datetime import UTC, datetime

from config import get_database_url
from database_manager import VALID_CATEGORIES, DatabaseManager


def _read_sqlite_rows(sqlite_path: str, query: str) -> list[tuple]:
    with sqlite3.connect(sqlite_path) as conn:
        cursor = conn.cursor()
        cursor.execute(query)
        return cursor.fetchall()


def _parse_legacy_timestamp(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)


LEGACY_CATEGORY_ALIASES = {
    "food": "alimentos",
    "utilities": "servicios",
    "other": "otros",
    "escenciales": "servicios",
    "esenciales": "servicios",
    "1": "alimentos",
    "2": "alimentos",
    "3": "entretenimiento",
    "4": "otros",
}


def _normalize_legacy_category(category: object) -> str:
    normalized = str(category).strip().lower()
    if normalized in VALID_CATEGORIES:
        return normalized
    if normalized in LEGACY_CATEGORY_ALIASES:
        return LEGACY_CATEGORY_ALIASES[normalized]
    return "otros"


def migrate() -> None:
    sqlite_path = os.getenv("SQLITE_DB_PATH", "expense_data.db")
    postgres_db = DatabaseManager(get_database_url())
    postgres_db.initialize()

    expense_rows = _read_sqlite_rows(
        sqlite_path,
        "SELECT user_id, amount, concept, category, timestamp FROM expense ORDER BY timestamp ASC",
    )
    limit_rows = _read_sqlite_rows(
        sqlite_path,
        "SELECT user_id, limit_amount, updated_at FROM monthly_limit",
    )

    normalized_category_counts: dict[str, int] = {}

    for user_id, amount, concept, category, timestamp in expense_rows:
        normalized_category = _normalize_legacy_category(category)
        normalized_category_counts[normalized_category] = (
            normalized_category_counts.get(normalized_category, 0) + 1
        )
        postgres_db.insert_expense(
            user_id=int(user_id),
            amount=float(amount),
            concept=concept,
            category=normalized_category,
            timestamp=_parse_legacy_timestamp(timestamp),
            ignore_conflicts=True,
        )

    for user_id, limit_amount, updated_at in limit_rows:
        postgres_db.upsert_monthly_limit(
            user_id=int(user_id),
            limit_amount=float(limit_amount),
            updated_at=_parse_legacy_timestamp(updated_at),
        )

    print(
        f"Migrated {len(expense_rows)} expenses and {len(limit_rows)} monthly limits "
        f"from {sqlite_path} to PostgreSQL."
    )
    print("Normalized categories:", normalized_category_counts)


if __name__ == "__main__":
    migrate()
