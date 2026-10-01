from datetime import datetime
from uuid import UUID
from typing import Literal
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class WireModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")


class FindingResponse(WireModel):
    id: UUID
    repository_execution_id: UUID
    execution_id: UUID
    repository_name: str
    repository_full_path: str
    branch: str | None = None
    rule_id: str
    rule_version: str
    severity: str
    title: str
    summary: str
    commit_hash: str
    author_email: str | None
    author_email_state: str
    author_name: str | None
    authored_at: datetime | None
    commit_message_summary: str | None
    file_path: str | None
    line_start: int | None
    line_end: int | None
    created_at: datetime

    @classmethod
    def from_entity(cls, item, repository_path, repository_name="", execution_id=None, branch=None):
        return cls(**{name: getattr(item, name) for name in cls.model_fields if hasattr(item, name)},
                   repository_full_path=repository_path, repository_name=repository_name, execution_id=execution_id,
                   branch=branch)


class FindingPage(WireModel):
    items: list[FindingResponse]
    page: int
    page_size: int
    total_items: int
    total_pages: int


class ChangedFileDiffResponse(WireModel):
    old_path: str | None
    new_path: str | None
    change_type: Literal["added", "modified", "deleted", "renamed"] | None
    diff: str | None
    text_diff_available: bool
    binary: bool | None
    collapsed: bool | None
    too_large: bool | None
    diff_truncated: bool
    old_path_truncated: bool
    new_path_truncated: bool


class FindingCommitDiffResponse(WireModel):
    finding_id: UUID
    repository_name: str
    repository_name_truncated: bool
    repository_full_path: str
    repository_full_path_truncated: bool
    commit_hash: str
    author_name: str | None
    author_email: str | None
    authored_at: datetime | None
    commit_message_summary: str | None
    files: list[ChangedFileDiffResponse]
    files_completeness: Literal["complete", "truncated", "unknown"]

    @classmethod
    def from_entity(cls, item):
        return cls(**{key: getattr(item, key) for key in cls.model_fields if key != "files" and hasattr(item, key)},
                   files=[ChangedFileDiffResponse(**{key: getattr(row, key) for key in ChangedFileDiffResponse.model_fields})
                          for row in item.files])
