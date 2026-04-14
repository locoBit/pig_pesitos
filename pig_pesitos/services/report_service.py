from datetime import datetime

import pendulum

from pig_pesitos.constants import REPORT_PERIODS
from pig_pesitos.repositories.database import DatabaseManager, ExpenseRecord


class ReportService:
    def __init__(self, db: DatabaseManager):
        self.db = db

    def get_period_range(self, report_period: str) -> tuple[datetime, datetime]:
        now = pendulum.now("UTC")
        if report_period == "week":
            start = now.start_of("week")
            end = now.end_of("week")
        elif report_period == "month":
            start = now.start_of("month")
            end = now.end_of("month")
        else:
            start = now.start_of("day")
            end = now.end_of("day")
        return start, end

    def get_percentage_report_data(self, user_id: int, report_period: str) -> tuple[list[ExpenseRecord], str, float | None]:
        start_range, end_range = self.get_period_range(report_period)
        expenses = self.db.get_expenses_between(user_id, start_range, end_range, ascending=True)
        period_label = REPORT_PERIODS.get(report_period, report_period)
        monthly_limit = self.db.get_monthly_limit(user_id)
        return expenses, period_label, monthly_limit

    def get_detailed_report_data(self, user_id: int, report_period: str) -> tuple[list[ExpenseRecord], str, float | None]:
        start_range, end_range = self.get_period_range(report_period)
        rows = self.db.get_expenses_between(user_id, start_range, end_range, ascending=True)
        period_label = REPORT_PERIODS.get(report_period, report_period)
        monthly_limit = self.db.get_monthly_limit(user_id)
        return rows, period_label, monthly_limit
