import re
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Header, Response

from app.api.dependencies import get_uow
from app.api.v1.schemas import (MonitoringScheduleResponse, NextOccurrenceResponse,
                                SchedulePreviewRequest, SchedulePreviewResponse,
                                ScheduleRequest, ScheduleResponse, ScheduleTimezonesResponse)
from app.application.use_cases.get_monitoring_schedule import GetMonitoringSchedule
from app.application.use_cases.list_schedule_timezones import ListScheduleTimezones
from app.application.use_cases.preview_monitoring_schedule import PreviewMonitoringSchedule
from app.application.use_cases.replace_monitoring_schedule import ReplaceMonitoringSchedule
from app.domain.errors import BadRequestError, MissingPreconditionError

router = APIRouter(tags=["monitoring-schedules"])
_ETAG = re.compile(r'^"?(0|[1-9][0-9]*)"?$')


def _expected_version(value: str | None) -> int:
    if value is None:
        raise MissingPreconditionError("Provide the current schedule ETag in If-Match.")
    match = _ETAG.fullmatch(value.strip())
    if not match:
        raise BadRequestError("Provide a valid schedule ETag.")
    return int(match.group(1))


def _occurrence(calculated, timezone):
    if calculated is None:
        return None
    zone = ZoneInfo(timezone)
    local = calculated.astimezone(zone)
    return NextOccurrenceResponse(
        instant=calculated.isoformat().replace("+00:00", "Z"), timezone=timezone,
        local_date_time=local.replace(tzinfo=None).isoformat(timespec="seconds"),
    )


@router.get("/schedule-timezones", response_model=ScheduleTimezonesResponse)
def list_schedule_timezones():
    return ScheduleTimezonesResponse(timezones=ListScheduleTimezones().execute())


@router.get("/monitoring-configurations/{configuration_id}/schedule", response_model=MonitoringScheduleResponse)
def get_schedule(configuration_id: UUID, response: Response, uow=Depends(get_uow)):
    result = GetMonitoringSchedule(uow).execute(configuration_id)
    response.headers["ETag"] = f'"{result.version}"'
    return MonitoringScheduleResponse(
        schedule=ScheduleResponse.from_entity(result.schedule) if result.schedule else None,
        next_occurrence=_occurrence(result.next_occurrence, result.schedule.timezone)
        if result.schedule else None,
    )


@router.put("/monitoring-configurations/{configuration_id}/schedule", response_model=MonitoringScheduleResponse)
def replace_schedule(configuration_id: UUID, payload: ScheduleRequest, response: Response,
                     if_match: Annotated[str | None, Header(alias="If-Match")] = None,
                     uow=Depends(get_uow)):
    expected = _expected_version(if_match)
    reference = datetime.now(UTC)
    result = ReplaceMonitoringSchedule(uow, now=lambda: reference).execute(
        configuration_id, payload.model_dump(), expected)
    response.headers["ETag"] = f'"{result.schedule.version}"'
    return MonitoringScheduleResponse(schedule=ScheduleResponse.from_entity(result.schedule),
                                      next_occurrence=_occurrence(result.next_occurrence, result.schedule.timezone))


@router.post("/monitoring-configurations/{configuration_id}/schedule/preview",
             response_model=SchedulePreviewResponse)
def preview_schedule(configuration_id: UUID, payload: SchedulePreviewRequest, uow=Depends(get_uow)):
    reference = payload.reference_instant
    result = PreviewMonitoringSchedule(uow).execute(configuration_id, {
        "schedule": payload.schedule.model_dump(), "reference_instant": reference,
    })
    return SchedulePreviewResponse(next_occurrence=_occurrence(result, payload.schedule.timezone) if result else None)


@router.delete("/monitoring-configurations/{configuration_id}/schedule", status_code=204)
def remove_schedule(configuration_id: UUID, response: Response,
                    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
                    uow=Depends(get_uow)):
    expected = _expected_version(if_match)
    from app.application.use_cases.remove_monitoring_schedule import RemoveMonitoringSchedule
    version = RemoveMonitoringSchedule(uow).execute(configuration_id, expected)
    response.headers["ETag"] = f'"{version}"'
    return Response(status_code=204, headers={"ETag": f'"{version}"'})
