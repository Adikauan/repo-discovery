from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, Header, Request, Response, Query
from app.api.dependencies import get_uow, get_credential_cipher, get_gitlab_repository_client, get_mining_worker_uow_factory
from app.api.v1.execution_schemas import ExecutionDetail, ExecutionPage, ExecutionListItem
from app.application.use_cases.list_executions import ListExecutions, ListConfigurationExecutions
from app.application.use_cases.get_execution import GetExecution
from app.domain.entities.mining_execution import ExecutionStatus, TriggerType
from app.api.v1.monitoring_configurations import KEY_RE
from app.application.use_cases.create_manual_execution import CreateManualExecution
from app.config import get_settings
from app.domain.errors import BadRequestError
from app.application.use_cases.process_mining_execution import ProcessMiningExecution

router = APIRouter(tags=['executions'])


async def no_request_body(request: Request):
    if await request.body():
        raise BadRequestError('This operation does not accept a request body.')


@router.post('/monitoring-configurations/{configuration_id}/executions', response_model=ExecutionDetail,
    status_code=201, dependencies=[Depends(no_request_body)])
def create_manual_execution(configuration_id: UUID, response: Response, uow=Depends(get_uow),
    idempotency_key: Annotated[str | None, Header(alias='Idempotency-Key')] = None,
    provider=Depends(get_gitlab_repository_client), cipher=Depends(get_credential_cipher),
    worker_uow_factory=Depends(get_mining_worker_uow_factory)):
    if idempotency_key is not None and not KEY_RE.fullmatch(idempotency_key):
        raise BadRequestError('Use 1-128 visible ASCII characters without spaces.')
    settings = get_settings()
    pipeline = ProcessMiningExecution(uow, provider, cipher,
        concurrency=settings.repository_mining_concurrency,
        max_file_bytes=settings.repository_mining_max_file_bytes,
        max_extensions=settings.repository_mining_max_extensions,
        max_commits=settings.mining_max_commits_per_repository_execution,
        worker_uow_factory=worker_uow_factory)
    item = CreateManualExecution(uow, threshold=settings.execution_staleness_threshold_seconds,
        mining_pipeline=pipeline).execute(configuration_id, idempotency_key)
    response.headers['Location'] = f'/api/v1/executions/{item.id}'
    return ExecutionDetail.from_entity(item)


def page_response(result, uow):
    ids = [item.id for item in result.items]
    finding_repository = getattr(uow, 'finding_repository', None)
    count_method = getattr(finding_repository, 'count_by_executions', None)
    counts = count_method(ids) if count_method else {}
    return ExecutionPage(items=[ExecutionListItem.from_entity(item, counts.get(item.id, 0)) for item in result.items],
        page=result.page, page_size=result.page_size, total_items=result.total_items, total_pages=result.total_pages)


@router.get('/executions', response_model=ExecutionPage)
def list_executions(page: int = Query(1, ge=1), page_size: int = Query(25, alias='pageSize', ge=1, le=100),
    status: ExecutionStatus | None = None, trigger_type: TriggerType | None = Query(None, alias='triggerType'),
    configuration_id: UUID | None = Query(None, alias='monitoringConfigurationId'), uow=Depends(get_uow)):
    return page_response(ListExecutions(uow).execute(page=page, page_size=page_size,
        configuration_id=configuration_id, status=status, trigger_type=trigger_type), uow)


@router.get('/monitoring-configurations/{configuration_id}/executions', response_model=ExecutionPage)
def list_configuration_executions(configuration_id: UUID, page: int = Query(1, ge=1),
    page_size: int = Query(25, alias='pageSize', ge=1, le=100), status: ExecutionStatus | None = None,
    trigger_type: TriggerType | None = Query(None, alias='triggerType'), uow=Depends(get_uow)):
    return page_response(ListConfigurationExecutions(uow).execute(configuration_id, page=page,
        page_size=page_size, status=status, trigger_type=trigger_type), uow)


@router.get('/executions/{execution_id}', response_model=ExecutionDetail)
def get_execution(execution_id: UUID, uow=Depends(get_uow)):
    return ExecutionDetail.from_entity(GetExecution(uow).execute(execution_id))
