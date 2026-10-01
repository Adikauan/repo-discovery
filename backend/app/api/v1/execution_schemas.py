from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel
from app.domain.entities.mining_execution import MiningExecution, ExecutionStatus, TriggerType
from app.application.use_cases.get_execution import snapshot_projection


class WireModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra='forbid')


class ScopeGroupResponse(WireModel):
    gitlab_group_id: int
    name: str
    full_path: str


class ScopeRepositoryResponse(WireModel):
    gitlab_project_id: int
    name: str
    full_path: str


class ScopeResponse(WireModel):
    groups: list[ScopeGroupResponse]
    repositories: list[ScopeRepositoryResponse]


class SnapshotResponse(WireModel):
    configuration_id: UUID
    configuration_name: str
    configuration_enabled: bool
    gitlab_url: str
    configuration_revision: int | None
    scope: ScopeResponse


class ExecutionListItem(WireModel):
    id: UUID
    monitoring_configuration_id: UUID
    configuration_name: str
    trigger_type: TriggerType
    status: ExecutionStatus
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    duration_seconds: float | None
    finding_count: int = 0

    @classmethod
    def from_entity(cls, item: MiningExecution, finding_count: int | None = None):
        return cls(id=item.id, monitoring_configuration_id=item.monitoring_configuration_id,
            configuration_name=item.snapshot.configuration_name, trigger_type=item.trigger_type,
            status=item.status, created_at=item.created_at, started_at=item.started_at,
            completed_at=item.completed_at, duration_seconds=item.duration_seconds,
            finding_count=item.finding_count if finding_count is None else finding_count)


class ExecutionCounters(WireModel):
    repository_count: int
    successful_repository_count: int
    failed_repository_count: int
    finding_count: int
    scope_resolution_failure_count: int = 0


class ExecutionError(WireModel):
    code: str
    summary: str


class ExecutionDetail(ExecutionListItem):
    snapshot: SnapshotResponse
    counters: ExecutionCounters
    scope_resolution_failure_count: int
    error: ExecutionError | None
    completion_meaning: str | None

    @classmethod
    def from_entity(cls, item: MiningExecution):
        snapshot = SnapshotResponse(**snapshot_projection(item.snapshot))
        return cls(**ExecutionListItem.from_entity(item).model_dump(), snapshot=snapshot,
            counters=ExecutionCounters(repository_count=item.repository_count, successful_repository_count=item.successful_repository_count,
                failed_repository_count=item.failed_repository_count, finding_count=item.finding_count),
            scope_resolution_failure_count=item.scope_resolution_failure_count,
            error=ExecutionError(code=item.error_code, summary=item.error_summary) if item.error_code else None,
            completion_meaning=('Feature 006 orchestration completed; repository mining was not performed.'
                if item.status == 'completed' and not item.repository_mining_completed else
                'Repository processing completed successfully; the effective scope contained no repositories.'
                if item.status == 'completed' and item.repository_count == 0 else
                'Repository processing completed successfully.' if item.status == 'completed' else None))


class ExecutionPage(WireModel):
    items: list[ExecutionListItem]
    page: int
    page_size: int
    total_items: int
    total_pages: int
