from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any
import logging
import time

import psycopg
from psycopg.rows import tuple_row

from pig_pesitos.constants import VALID_CATEGORIES


logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """Domain-level error for database operations.

    Wraps underlying psycopg errors so callers don't depend on driver-specific
    exceptions.
    """


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
        """Create a new database connection with a tiny retry strategy.

        This keeps transient connection issues from crashing individual bot
        requests while still failing fast enough on persistent problems.
        """

        last_error: psycopg.Error | None = None
        for attempt in range(3):
            try:
                return psycopg.connect(self.database_url, row_factory=tuple_row)
            except psycopg.Error as error:  # pragma: no cover - network/infra
                last_error = error
                logger.warning(
                    "Database connection attempt %d failed: %s", attempt + 1, error
                )
                time.sleep(0.1 * (attempt + 1))
        assert last_error is not None  # for type-checkers
        raise DatabaseError("Error connecting to the database") from last_error

    def initialize(self) -> None:
        category_values = ", ".join(f"'{category}'" for category in VALID_CATEGORIES)
        try:
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
        except psycopg.Error as error:  # pragma: no cover - network/infra
            logger.exception("Error initializing database schema: %s", error)
            raise DatabaseError("Error initializing database schema") from error

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
        try:
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
        except psycopg.Error as error:  # pragma: no cover - network/infra
            logger.exception("Error inserting expense: %s", error)
            raise DatabaseError("Error inserting expense") from error

    def get_expenses_between(
        self,
        user_id: int,
        start_range: datetime,
        end_range: datetime,
        *,
        ascending: bool = True,
    ) -> list[ExpenseRecord]:
        order_clause = "ASC" if ascending else "DESC"
        try:
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
        except psycopg.Error as error:  # pragma: no cover - network/infra
            logger.exception("Error fetching expenses for report: %s", error)
            raise DatabaseError("Error fetching expenses for report") from error
        return [ExpenseRecord(*row) for row in rows]

    def get_category_total(self, user_id: int, category: str) -> float:
        try:
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
        except psycopg.Error as error:  # pragma: no cover - network/infra
            logger.exception("Error calculating category total: %s", error)
            raise DatabaseError("Error calculating category total") from error
        return float(total)

    def get_monthly_limit(self, user_id: int) -> float | None:
        try:
            with self._connect() as conn, conn.cursor() as cursor:
                cursor.execute(
                    "SELECT limit_amount FROM monthly_limit WHERE user_id = %s",
                    (user_id,),
                )
                row = cursor.fetchone()
        except psycopg.Error as error:  # pragma: no cover - network/infra
            logger.exception("Error fetching monthly limit: %s", error)
            raise DatabaseError("Error fetching monthly limit") from error
        return float(row[0]) if row else None

    def upsert_monthly_limit(self, user_id: int, limit_amount: float, updated_at: datetime) -> None:
        try:
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
        except psycopg.Error as error:  # pragma: no cover - network/infra
            logger.exception("Error updating monthly limit: %s", error)
            raise DatabaseError("Error updating monthly limit") from error

    def delete_user_data(self, user_id: int) -> None:
        """Delete all persisted data for a given user.

        This supports basic data privacy / "forget me" flows. It is a hard
        delete; there is no recovery from this operation at the application
        level.
        """

        try:
            with self._connect() as conn, conn.cursor() as cursor:
                cursor.execute("DELETE FROM expense WHERE user_id = %s", (user_id,))
                cursor.execute("DELETE FROM monthly_limit WHERE user_id = %s", (user_id,))
                conn.commit()
        except psycopg.Error as error:  # pragma: no cover - network/infra
            logger.exception("Error deleting user data: %s", error)
            raise DatabaseError("Error deleting user data") from error

    def healthcheck(self) -> dict[str, Any]:
        try:
            with self._connect() as conn, conn.cursor() as cursor:
                cursor.execute("SELECT current_database(), version()")
                database_name, version = cursor.fetchone()
        except psycopg.Error as error:  # pragma: no cover - network/infra
            logger.exception("Error running database healthcheck: %s", error)
            raise DatabaseError("Error running database healthcheck") from error
        return {"database": database_name, "version": version}
