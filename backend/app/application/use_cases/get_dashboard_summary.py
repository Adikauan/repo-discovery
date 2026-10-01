from datetime import UTC, datetime, time, timedelta


class GetDashboardSummary:
    """Build the fixed seven-UTC-day presentation projection from persisted rows."""
    def __init__(self, uow, clock=lambda: datetime.now(UTC)):
        self.uow = uow
        self.clock = clock

    def execute(self):
        now = self.clock().astimezone(UTC)
        today = now.date()
        start = datetime.combine(today - timedelta(days=6), time.min, tzinfo=UTC)
        result = self.uow.dashboard_summary_repository.summarize(start, now)
        statuses = {key: result["status_distribution"].get(key, 0) for key in
                    ("pending", "running", "completed", "partially_completed", "failed")}
        terminal = statuses["completed"] + statuses["partially_completed"] + statuses["failed"]
        result["window"] = {"start": start, "end": now, "timezone": "UTC"}
        result["metrics"] = {
            "execution_count": sum(statuses.values()),
            "repositories_processed": result.pop("repositories_processed"),
            "finding_count": result.pop("finding_count"),
            "success_rate_percent": round(statuses["completed"] / terminal * 100) if terminal else None,
            "terminal_execution_count": terminal,
        }
        result["status_distribution"] = statuses
        result["daily_executions"] = [
            {"date": (today - timedelta(days=6 - index)).isoformat(),
             "count": result["daily_executions"].get((today - timedelta(days=6 - index)).isoformat(), 0)}
            for index in range(7)
        ]
        return result
