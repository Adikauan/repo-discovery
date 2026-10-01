from datetime import UTC, datetime
from app.application.use_cases.get_dashboard_summary import GetDashboardSummary


class Repository:
    def __init__(self, result): self.result = result; self.bounds = None
    def summarize(self, start, end): self.bounds = (start, end); return self.result


def test_summary_uses_seven_utc_days_and_derives_terminal_success_rate():
    repository = Repository({
        "status_distribution": {"completed": 2, "partially_completed": 1, "failed": 1, "running": 1},
        "daily_executions": {"2026-09-30": 2}, "repositories_processed": 3, "finding_count": 2,
        "recent_executions": [], "findings_by_rule": [],
    })
    result = GetDashboardSummary(type("Uow", (), {"dashboard_summary_repository": repository})(),
        clock=lambda: datetime(2026, 9, 30, 12, tzinfo=UTC)).execute()
    assert repository.bounds == (datetime(2026, 9, 24, tzinfo=UTC), datetime(2026, 9, 30, 12, tzinfo=UTC))
    assert len(result["daily_executions"]) == 7
    assert result["daily_executions"][0] == {"date": "2026-09-24", "count": 0}
    assert result["metrics"]["success_rate_percent"] == 50
    assert result["metrics"]["terminal_execution_count"] == 4
    assert result["metrics"]["repositories_processed"] == 3
    assert result["metrics"]["finding_count"] == 2


def test_summary_returns_null_success_rate_without_terminal_executions():
    repository = Repository({"status_distribution": {"running": 1}, "daily_executions": {},
        "repositories_processed": 0, "finding_count": 0, "recent_executions": [], "findings_by_rule": []})
    result = GetDashboardSummary(type("Uow", (), {"dashboard_summary_repository": repository})(),
        clock=lambda: datetime(2026, 9, 30, tzinfo=UTC)).execute()
    assert result["metrics"]["success_rate_percent"] is None
