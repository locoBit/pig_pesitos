from datetime import datetime

import pendulum

from pig_pesitos.repositories.database import DatabaseError, DatabaseManager


class ExpenseService:
    def __init__(self, db: DatabaseManager):
        self.db = db

    def create_expense(self, user_id: int, amount: float, concept: str, category: str) -> float:
        """Create an expense and return the updated category total.

        Any low-level database errors are surfaced as DatabaseError so callers
        can decide how to react (e.g. show a friendly message instead of
        crashing the bot).
        """

        timestamp = pendulum.now("UTC")
        try:
            self.db.insert_expense(user_id, amount, concept, category.lower(), timestamp)
            return self.db.get_category_total(user_id, category.lower())
        except DatabaseError:
            # Bubble up; handler layer is responsible for translating this to
            # user-facing errors. Keeping this layer thin preserves SRP.
            raise

    def set_monthly_limit(self, user_id: int, amount: float) -> None:
        timestamp: datetime = pendulum.now("UTC")
        try:
            self.db.upsert_monthly_limit(user_id, amount, timestamp)
        except DatabaseError:
            raise

    def get_monthly_limit(self, user_id: int) -> float | None:
        try:
            return self.db.get_monthly_limit(user_id)
        except DatabaseError:
            raise

    def delete_user_data(self, user_id: int) -> None:
        """Permanently delete all data associated with a user.

        This is intended to support basic "forget me" / privacy flows.
        """

        try:
            self.db.delete_user_data(user_id)
        except DatabaseError:
            raise
