import re
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Response
from pydantic import ValidationError

from app.api.dependencies import get_uow
from app.api.v1.schemas import (ConfigurationListItem, ConfigurationListResponse, ConfigurationResponse, CreateConfigurationRequest,
                                UpdateConfigurationRequest)
from app.application.use_cases.create_monitoring_configuration import CreateMonitoringConfiguration
from app.application.use_cases.get_monitoring_configuration import GetMonitoringConfiguration
from app.application.use_cases.list_monitoring_configurations import ListMonitoringConfigurations
from app.application.use_cases.retire_monitoring_configuration import RetireMonitoringConfiguration
from app.application.use_cases.update_monitoring_configuration import UpdateMonitoringConfiguration
from app.domain.errors import BadRequestError, FieldValidationError, MissingPreconditionError

router = APIRouter(prefix="/monitoring-configurations", tags=["monitoring-configurations"])
KEY_RE = re.compile(r"^[!-~]{1,128}$")


@router.post("", response_model=ConfigurationResponse, status_code=201)
def create_configuration(payload: CreateConfigurationRequest, response: Response,
                         uow=Depends(get_uow), idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None):
    if idempotency_key is not None and not KEY_RE.fullmatch(idempotency_key):
        raise BadRequestError("Use 1–128 visible ASCII characters without spaces.")
    result = CreateMonitoringConfiguration(uow).execute(payload.model_dump(), idempotency_key)
    body = ConfigurationResponse(**result.response_snapshot)
    response.headers["ETag"] = f'"{body.version}"'
    response.headers["Location"] = f"/api/v1/monitoring-configurations/{body.id}"
    return body


@router.get("", response_model=ConfigurationListResponse)
def list_configurations(search: str | None = Query(default=None), uow=Depends(get_uow)):
    return {"items": [ConfigurationListItem.from_projection(item, schedule)
                       for item, schedule in ListMonitoringConfigurations(uow).execute_with_schedule(search)]}


@router.get("/{identifier}", response_model=ConfigurationResponse)
def get_configuration(identifier: UUID, response: Response, uow=Depends(get_uow)):
    item = GetMonitoringConfiguration(uow).execute(identifier)
    response.headers["ETag"] = f'"{item.revision}"'
    return ConfigurationResponse.from_entity(item)


@router.put("/{identifier}", response_model=ConfigurationResponse)
def update_configuration(identifier: UUID, payload: UpdateConfigurationRequest, response: Response,
                         if_match: Annotated[str | None, Header(alias="If-Match")] = None, uow=Depends(get_uow)):
    if if_match is None: raise MissingPreconditionError("Provide the current ETag in If-Match.")
    try: revision = int(if_match.strip('"'))
    except ValueError: raise FieldValidationError("If-Match", "invalid", "Provide a valid configuration ETag.")
    item = UpdateMonitoringConfiguration(uow).execute(identifier, payload.model_dump(), revision)
    response.headers["ETag"] = f'"{item.revision}"'
    return ConfigurationResponse.from_entity(item)


@router.delete("/{identifier}", status_code=204)
def delete_configuration(identifier: UUID, uow=Depends(get_uow)):
    RetireMonitoringConfiguration(uow).execute(identifier)
    return Response(status_code=204)
