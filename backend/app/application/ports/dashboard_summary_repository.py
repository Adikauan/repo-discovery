from typing import Protocol
from datetime import datetime


class DashboardSummaryRepository(Protocol):
    def summarize(self, start: datetime, end: datetime) -> dict: ...
