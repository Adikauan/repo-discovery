from datetime import date, datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class DashboardWireModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")


class DashboardWindow(DashboardWireModel):
    start: datetime
    end: datetime
    timezone: str


class DashboardMetrics(DashboardWireModel):
    execution_count: int
    repositories_processed: int
    finding_count: int
    success_rate_percent: int | None
    terminal_execution_count: int


class DashboardStatusDistribution(DashboardWireModel):
    pending: int
    running: int
    completed: int
    partially_completed: int
    failed: int


class DashboardDay(DashboardWireModel):
    date: date
    count: int


class DashboardRecentExecution(DashboardWireModel):
    id: UUID
    configuration_name: str
    status: str
    trigger_type: str
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    duration_seconds: float | None
    finding_count: int


class DashboardFindingRule(DashboardWireModel):
    rule_id: str
    label: str
    count: int


class DashboardSummaryResponse(DashboardWireModel):
    window: DashboardWindow
    metrics: DashboardMetrics
    status_distribution: DashboardStatusDistribution
    daily_executions: list[DashboardDay]
    recent_executions: list[DashboardRecentExecution]
    findings_by_rule: list[DashboardFindingRule]
