from datetime import UTC, datetime
from fastapi.testclient import TestClient
from app.api.dependencies import get_uow
from app.api.main import create_app


class SummaryRepository:
    def summarize(self, start, end):
        assert start.tzinfo == UTC and end.tzinfo == UTC
        return {"status_distribution": {}, "daily_executions": {}, "repositories_processed": 0,
            "finding_count": 0, "recent_executions": [], "findings_by_rule": []}


class Uow:
    dashboard_summary_repository = SummaryRepository()


def test_dashboard_summary_is_read_only_and_zero_fills_the_bounded_window():
    app = create_app(scheduler_enabled=False); app.dependency_overrides[get_uow] = lambda: Uow()
    client = TestClient(app)
    result = client.get("/api/v1/dashboard/summary")
    assert result.status_code == 200
    body = result.json()
    assert len(body["dailyExecutions"]) == 7
    assert all(item["count"] == 0 for item in body["dailyExecutions"])
    assert body["metrics"]["successRatePercent"] is None
    assert body["findingsByRule"] == []
    assert client.post("/api/v1/dashboard/summary").status_code == 405
