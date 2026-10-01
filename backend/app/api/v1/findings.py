from math import ceil
from uuid import UUID
from typing import Literal
from fastapi import APIRouter, Depends, Query, Request
from app.api.dependencies import get_uow, get_credential_cipher, get_gitlab_repository_client
from app.api.v1.finding_schemas import FindingCommitDiffResponse, FindingPage, FindingResponse
from app.application.use_cases.get_finding_commit_diff import GetFindingCommitDiff
from app.application.use_cases.get_finding import GetFinding
from app.application.use_cases.list_execution_findings import ListExecutionFindings
from app.application.use_cases.list_repository_findings import ListRepositoryFindings
from app.config import get_settings
from app.domain.errors import BadRequestError

router = APIRouter(tags=["findings"])


def page_response(result, page, page_size, repository_paths=None):
    paths = repository_paths or {}
    values = []
    for item in result["items"]:
        details = paths.get(item.repository_execution_id)
        if details is None:
            repository = result.get("repository")
            details = (repository.repository_full_path, repository.repository_name, repository.mining_execution_id,
                       repository.processed_branch) if repository else ("", "", None, None)
        values.append(FindingResponse.from_entity(item, *details))
    total = result["total_items"]
    return FindingPage(items=values, page=page, page_size=page_size, total_items=total,
                       total_pages=ceil(total / page_size))


@router.get("/executions/{execution_id}/findings", response_model=FindingPage)
def list_execution_findings(execution_id: UUID, page: int = Query(1, ge=1),
    page_size: int = Query(25, alias="pageSize", ge=1, le=100), repository_id: UUID | None = Query(None, alias="repositoryExecutionId"),
    rule_id: str | None = Query(None, alias="ruleId", min_length=1, max_length=100),
    severity: Literal["warning"] | None = Query(None), uow=Depends(get_uow)):
    result = ListExecutionFindings(uow).execute(execution_id, page=page, page_size=page_size,
        repository_id=repository_id, rule_id=rule_id, severity=severity)
    return page_response(result, page, page_size, result["repository_paths"])


@router.get("/executions/{execution_id}/repositories/{repository_execution_id}/findings", response_model=FindingPage)
def list_repository_findings(execution_id: UUID, repository_execution_id: UUID, page: int = Query(1, ge=1),
    page_size: int = Query(25, alias="pageSize", ge=1, le=100),
    rule_id: str | None = Query(None, alias="ruleId", min_length=1, max_length=100),
    severity: Literal["warning"] | None = Query(None), uow=Depends(get_uow)):
    result = ListRepositoryFindings(uow).execute(execution_id, repository_execution_id,
        page=page, page_size=page_size, rule_id=rule_id, severity=severity)
    result["repository"] = uow.repository_execution_repository.get(repository_execution_id, execution_id)
    return page_response(result, page, page_size)


@router.get("/findings/{finding_id}", response_model=FindingResponse)
def get_finding(finding_id: UUID, uow=Depends(get_uow)):
    item, repository = GetFinding(uow).execute(finding_id)
    return FindingResponse.from_entity(item, repository.repository_full_path, repository.repository_name,
                                       repository.mining_execution_id, repository.processed_branch)


async def finding_diff_request_shape(request: Request):
    if request.query_params or (await request.body()):
        raise BadRequestError("Finding diff requests accept only the Finding identifier.")


@router.get("/findings/{finding_id}/diff", response_model=FindingCommitDiffResponse,
            dependencies=[Depends(finding_diff_request_shape)])
def get_finding_diff(finding_id: UUID, uow=Depends(get_uow),
                     provider=Depends(get_gitlab_repository_client), cipher=Depends(get_credential_cipher)):
    result = GetFindingCommitDiff(uow, provider, cipher, get_settings()).execute(finding_id)
    return FindingCommitDiffResponse.from_entity(result)
