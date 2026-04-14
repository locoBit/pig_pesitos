from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

import psycopg
from psycopg.rows import tuple_row


VALID_CATEGORIES = (
    "transporte",
    "vestimenta",
    "alimentos",
    "entretenimiento",
    "servicios",
    "salud",
    "otros",
)


@dataclass(frozen=True)
class ExpenseRecord:
    amount: Decimal
    concept: str
    category: str
    timestamp: datetime


class DatabaseManager:
    def __init__(self, database_url: str):
        self.database_url = database_url

    def _connect(self):
        return psycopg.connect(self.database_url, row_factory=tuple_row)

    def initialize(self) -> None:
        category_values = ", ".join(f"'{category}'" for category in VALID_CATEGORIES)
        with self._connect() as conn, conn.cursor() as cursor:
            cursor.execute(
                f"""
                CREATE TABLE IF NOT EXISTS expense (
                    id BIGSERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    amount NUMERIC(12, 2) NOT NULL CHECK (amount > 0),
                    concept VARCHAR(15) NOT NULL,
                    category TEXT NOT NULL CHECK (category IN ({category_values})),
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    UNIQUE (user_id, created_at)
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS monthly_limit (
                    user_id BIGINT PRIMARY KEY,
                    limit_amount NUMERIC(12, 2) NOT NULL CHECK (limit_amount > 0),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_expense_user_created_at
                ON expense (user_id, created_at DESC)
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_expense_user_category_created_at
                ON expense (user_id, category, created_at DESC)
                """
            )
            conn.commit()

    def insert_expense(
        self,
        user_id: int,
        amount: float,
        concept: str,
        category: str,
        timestamp: datetime,
        *,
        ignore_conflicts: bool = False,
    ) -> None:
        conflict_clause = "ON CONFLICT (user_id, created_at) DO NOTHING" if ignore_conflicts else ""
        with self._connect() as conn, conn.cursor() as cursor:
            cursor.execute(
                f"""
                INSERT INTO expense (user_id, amount, concept, category, created_at)
                VALUES (%s, %s, %s, %s, %s)
                {conflict_clause}
                """,
                (user_id, amount, concept, category, timestamp),
            )
            conn.commit()

    def get_expenses_between(
        self,
        user_id: int,
        start_range: datetime,
        end_range: datetime,
        *,
        ascending: bool = True,
    ) -> list[ExpenseRecord]:
        order_clause = "ASC" if ascending else "DESC"
        with self._connect() as conn, conn.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT amount, concept, category, created_at
                FROM expense
                WHERE user_id = %s AND created_at BETWEEN %s AND %s
                ORDER BY created_at {order_clause}
                """,
                (user_id, start_range, end_range),
            )
            rows = cursor.fetchall()
        return [ExpenseRecord(*row) for row in rows]

    def get_category_total(self, user_id: int, category: str) -> float:
        with self._connect() as conn, conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT COALESCE(SUM(amount), 0)
                FROM expense
                WHERE user_id = %s AND category = %s
                """,
                (user_id, category),
            )
            (total,) = cursor.fetchone()
        return float(total)

    def get_monthly_limit(self, user_id: int) -> float | None:
        with self._connect() as conn, conn.cursor() as cursor:
            cursor.execute(
                "SELECT limit_amount FROM monthly_limit WHERE user_id = %s",
                (user_id,),
            )
            row = cursor.fetchone()
        return float(row[0]) if row else None

    def upsert_monthly_limit(self, user_id: int, limit_amount: float, updated_at: datetime) -> None:
        with self._connect() as conn, conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO monthly_limit (user_id, limit_amount, updated_at)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE SET
                    limit_amount = EXCLUDED.limit_amount,
                    updated_at = EXCLUDED.updated_at
                """,
                (user_id, limit_amount, updated_at),
            )
            conn.commit()

    def healthcheck(self) -> dict[str, Any]:
        with self._connect() as conn, conn.cursor() as cursor:
            cursor.execute("SELECT current_database(), version()")
            database_name, version = cursor.fetchone()
        return {"database": database_name, "version": version}
