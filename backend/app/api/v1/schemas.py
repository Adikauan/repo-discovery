from datetime import datetime, time
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _camel(name: str) -> str:
    first, *rest = name.split("_")
    return first + "".join(part.capitalize() for part in rest)


class ScheduleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", alias_generator=_camel, populate_by_name=True)
    recurrence_type: Literal["daily", "weekly", "monthly"]
    enabled: bool
    execution_time: str
    timezone: str = Field(min_length=1)
    day_of_week: int | None = None
    day_of_month: int | None = None

    @field_validator("execution_time")
    @classmethod
    def valid_execution_time(cls, value: str) -> str:
        import re
        if not re.fullmatch(r"(?:[01][0-9]|2[0-3]):[0-5][0-9]", value):
            raise ValueError("invalid time")
        return value


class ScheduleResponse(BaseModel):
    model_config = ConfigDict(alias_generator=_camel, populate_by_name=True)
    recurrence_type: str
    enabled: bool
    execution_time: str
    timezone: str
    day_of_week: int | None
    day_of_month: int | None

    @classmethod
    def from_entity(cls, item):
        return cls(recurrence_type=item.recurrence_type.value, enabled=item.enabled,
                   execution_time=item.execution_time.strftime("%H:%M"), timezone=item.timezone,
                   day_of_week=item.day_of_week, day_of_month=item.day_of_month)


class NextOccurrenceResponse(BaseModel):
    model_config = ConfigDict(alias_generator=_camel, populate_by_name=True)
    instant: str
    timezone: str
    local_date_time: str


class MonitoringScheduleResponse(BaseModel):
    model_config = ConfigDict(alias_generator=_camel, populate_by_name=True)
    schedule: ScheduleResponse | None
    next_occurrence: NextOccurrenceResponse | None


class SchedulePreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", alias_generator=_camel, populate_by_name=True)
    schedule: ScheduleRequest
    reference_instant: datetime | None = None


class SchedulePreviewResponse(BaseModel):
    model_config = ConfigDict(alias_generator=_camel, populate_by_name=True)
    next_occurrence: NextOccurrenceResponse | None


class ScheduleTimezonesResponse(BaseModel):
    timezones: list[str]


class CreateConfigurationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=1)
    description: str | None = None
    gitlab_url: str = Field(min_length=1)
    allowed_author_emails: list[str] = Field(default_factory=list, max_length=500)


class UpdateConfigurationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=1)
    description: str | None = None
    gitlab_url: str = Field(min_length=1)
    enabled: bool
    allowed_author_emails: list[str] | None = Field(default=None, max_length=500)


class ConfigurationResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    gitlab_url: str
    enabled: bool
    created_at: datetime
    updated_at: datetime
    version: str
    allowed_author_emails: list[str] = Field(default_factory=list)

    @classmethod
    def from_entity(cls, item):
        return cls(id=item.id, name=item.name, description=item.description, gitlab_url=item.gitlab_url,
                   enabled=item.enabled, created_at=item.created_at, updated_at=item.updated_at,
                   version=str(item.revision), allowed_author_emails=list(item.allowed_author_emails))


class ConfigurationScheduleSummary(BaseModel):
    model_config = ConfigDict(alias_generator=_camel, populate_by_name=True)
    recurrence_type: str
    enabled: bool
    execution_time: str
    timezone: str
    day_of_week: int | None
    day_of_month: int | None

    @classmethod
    def from_record(cls, row):
        return cls(recurrence_type=row.recurrence_type, enabled=row.enabled,
                   execution_time=row.execution_time.strftime("%H:%M"), timezone=row.timezone,
                   day_of_week=row.day_of_week, day_of_month=row.day_of_month)


class ConfigurationListItem(ConfigurationResponse):
    model_config = ConfigDict(populate_by_name=True)
    schedule_summary: ConfigurationScheduleSummary | None = Field(default=None, alias="scheduleSummary")

    @classmethod
    def from_projection(cls, item, schedule):
        return cls(id=item.id, name=item.name, description=item.description, gitlab_url=item.gitlab_url,
                   enabled=item.enabled, created_at=item.created_at, updated_at=item.updated_at,
                   version=str(item.revision), allowed_author_emails=list(item.allowed_author_emails),
                   schedule_summary=ConfigurationScheduleSummary.from_record(schedule) if schedule else None)


class ConfigurationListResponse(BaseModel):
    items: list[ConfigurationListItem]


def _validate_token(value: str) -> str:
    if not value or not value.strip():
        raise ValueError("Provide a GitLab access token.")
    if len(value.encode("utf-8")) > 2048:
        raise ValueError("GitLab access tokens must not exceed 2048 UTF-8 bytes.")
    return value


class GitLabCredentialRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: str

    @field_validator("token")
    @classmethod
    def valid_token(cls, value: str) -> str:
        return _validate_token(value)


class GitLabValidationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: str | None = None

    @field_validator("token")
    @classmethod
    def valid_candidate(cls, value: str | None) -> str | None:
        return None if value is None else _validate_token(value)


class GitLabConnectionStatusResponse(BaseModel):
    configuration_id: UUID
    credential_configured: bool
    state: str
    latest_result: str | None = None
    last_validation_at: datetime | None = None
    last_successful_validation_at: datetime | None = None

    @classmethod
    def from_domain(cls, status):
        return cls(**{name: getattr(status, name) for name in cls.model_fields})


class GitLabValidationResponse(BaseModel):
    configuration_id: UUID
    credential_source: str
    state: str
    result: str
    message: str
    checked_at: datetime
    last_successful_validation_at: datetime | None = None

    @classmethod
    def from_domain(cls, result):
        return cls(**{name: getattr(result, name) for name in cls.model_fields})


class GitLabCandidateValidationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    gitlab_url: str = Field(min_length=1, max_length=2048)
    token: str

    @field_validator("token")
    @classmethod
    def valid_token(cls, value: str) -> str:
        return _validate_token(value)


class GitLabCandidateValidationResponse(BaseModel):
    state: str
    result: str
    message: str
    checked_at: datetime


class GitLabHierarchyNodeResponse(BaseModel):
    id: int
    type: str
    name: str
    full_path: str
    parent_group_id: int | None = None
    expandable: bool


class GitLabHierarchyResponse(BaseModel):
    nodes: list[GitLabHierarchyNodeResponse]


class ScopeSelectionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    selection_id: UUID | None = None
    gitlab_id: int = Field(gt=0)


class ReplaceMiningScopeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    groups: list[ScopeSelectionInput] = Field(default_factory=list)
    repositories: list[ScopeSelectionInput] = Field(default_factory=list)


class ScopeGroupResponse(BaseModel):
    selection_id: UUID
    gitlab_id: int
    name: str
    full_path: str
    parent_group_id: int | None = None
    availability: str


class ScopeRepositoryResponse(BaseModel):
    selection_id: UUID
    gitlab_id: int
    name: str
    full_path: str
    parent_group_id: int | None = None
    availability: str


class MiningScopeResponse(BaseModel):
    groups: list[ScopeGroupResponse]
    repositories: list[ScopeRepositoryResponse]
    stale: bool


def scope_response(scope, availability: dict[UUID, str] | None = None) -> MiningScopeResponse:
    statuses = availability or {}
    groups = [ScopeGroupResponse(
        selection_id=item.selection_id, gitlab_id=item.gitlab_group_id, name=item.name,
        full_path=item.full_path, parent_group_id=item.parent_group_id,
        availability=statuses.get(item.selection_id, "available"),
    ) for item in scope.groups]
    repositories = [ScopeRepositoryResponse(
        selection_id=item.selection_id, gitlab_id=item.gitlab_project_id, name=item.name,
        full_path=item.full_path, parent_group_id=item.parent_group_id,
        availability=statuses.get(item.selection_id, "available"),
    ) for item in scope.repositories]
    return MiningScopeResponse(
        groups=groups,
        repositories=repositories,
        stale=any(item.availability == "stale" for item in [*groups, *repositories]),
    )
