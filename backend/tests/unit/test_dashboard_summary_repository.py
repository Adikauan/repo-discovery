from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from sqlalchemy.dialects import postgresql

from app.infrastructure.database.sqlalchemy_repositories import SqlAlchemyDashboardSummaryRepository


class Result:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class Session:
    def __init__(self):
        now = datetime(2026, 9, 30, 12, tzinfo=UTC)
        executions = [
            SimpleNamespace(id=uuid4(), snapshot={"configuration_name": f"Config {index}"},
                status="completed", trigger_type="manual", created_at=now,
                started_at=now, completed_at=now)
            for index in range(5)
        ]
        self.expected_recent_ids = [execution.id for execution in executions]
        self.execute_rows = [
            [("completed", 5), ("failed", 1)],
            [(now.date(), 5)],
            [("unauthorized_commit_author", 2)],
            [(execution, 1) for execution in executions],
        ]
        self.scalar_values = [3, 2]
        self.statements = []

    def execute(self, statement):
        self.statements.append(statement)
        return Result(self.execute_rows.pop(0))

    def scalar(self, statement):
        self.statements.append(statement)
        return self.scalar_values.pop(0)


def test_dashboard_projection_uses_distinct_repositories_persisted_findings_and_bounded_recent_rows():
    session = Session()
    result = SqlAlchemyDashboardSummaryRepository(session).summarize(
        datetime(2026, 9, 24, tzinfo=UTC), datetime(2026, 10, 1, tzinfo=UTC)
    )

    assert result["repositories_processed"] == 3
    assert result["finding_count"] == 2
    assert result["findings_by_rule"] == [
        {"rule_id": "unauthorized_commit_author", "label": "Unauthorized commit author", "count": 2}
    ]
    assert len(result["recent_executions"]) == 5
    assert [item["id"] for item in result["recent_executions"]] == session.expected_recent_ids

    statements = [str(statement.compile(dialect=postgresql.dialect())) for statement in session.statements]
    assert any("count(DISTINCT repository_executions.gitlab_project_id)" in sql for sql in statements)
    assert any("findings." in sql for sql in statements)
    assert any("LIMIT" in sql and "created_at DESC" in sql and "id ASC" in sql for sql in statements)
    daily_sql = statements[1]
    assert daily_sql.count("timezone('UTC', mining_executions.created_at)") == 2
    assert "timezone(%(" not in daily_sql
