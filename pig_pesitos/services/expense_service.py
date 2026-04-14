from datetime import datetime

import pendulum

from pig_pesitos.repositories.database import DatabaseManager


class ExpenseService:
    def __init__(self, db: DatabaseManager):
        self.db = db

    def create_expense(self, user_id: int, amount: float, concept: str, category: str) -> float:
        timestamp = pendulum.now("UTC")
        self.db.insert_expense(user_id, amount, concept, category.lower(), timestamp)
        return self.db.get_category_total(user_id, category.lower())

    def set_monthly_limit(self, user_id: int, amount: float) -> None:
        timestamp: datetime = pendulum.now("UTC")
        self.db.upsert_monthly_limit(user_id, amount, timestamp)

    def get_monthly_limit(self, user_id: int) -> float | None:
        return self.db.get_monthly_limit(user_id)
