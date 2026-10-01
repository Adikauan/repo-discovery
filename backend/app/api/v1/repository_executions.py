from uuid import UUID
from datetime import datetime
from math import ceil

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from app.api.dependencies import get_uow
from app.application.use_cases.get_repository_execution import GetRepositoryExecution
from app.application.use_cases.list_repository_executions import ListRepositoryExecutions

router = APIRouter(tags=["repository executions"])


class WireModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")


class RepositoryExecutionError(WireModel):
    code: str
    summary: str


class RepositoryExecutionResponse(WireModel):
    id: UUID
    mining_execution_id: UUID
    gitlab_project_id: int
    repository_name: str
    repository_full_path: str
    status: str
    started_at: datetime | None
    completed_at: datetime | None
    target_branch: str | None
    processed_branch: str | None
    file_count: int
    observed_extensions: list[str]
    extensions_truncated: bool
    finding_count: int
    error: "RepositoryExecutionError | None"

    @classmethod
    def from_entity(cls, item):
        values = {key: getattr(item, key) for key in cls.model_fields if key in {
            "id", "mining_execution_id", "gitlab_project_id", "repository_name", "repository_full_path",
            "status", "started_at", "completed_at", "target_branch", "processed_branch", "file_count", "observed_extensions",
            "extensions_truncated", "finding_count"}}
        values["error"] = RepositoryExecutionError(code=item.error_code, summary=item.error_summary) if item.error_code else None
        return cls(**values)


class RepositoryExecutionPage(WireModel):
    items: list[RepositoryExecutionResponse]
    page: int
    page_size: int
    total_items: int
    total_pages: int


@router.get("/executions/{execution_id}/repositories", response_model=RepositoryExecutionPage)
def list_repositories(execution_id: UUID, page: int = Query(1, ge=1), page_size: int = Query(25, alias="pageSize", ge=1, le=100), uow=Depends(get_uow)):
    result = ListRepositoryExecutions(uow).execute(execution_id, page=page, page_size=page_size)
    return RepositoryExecutionPage(items=[RepositoryExecutionResponse.from_entity(item) for item in result["items"]],
        page=page, page_size=page_size, total_items=result["total_items"], total_pages=ceil(result["total_items"] / page_size))


@router.get("/executions/{execution_id}/repositories/{repository_execution_id}", response_model=RepositoryExecutionResponse)
def get_repository(execution_id: UUID, repository_execution_id: UUID, uow=Depends(get_uow)):
    return RepositoryExecutionResponse.from_entity(GetRepositoryExecution(uow).execute(execution_id, repository_execution_id))
