from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class PolicyWire(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID
    scope_type: str
    active: bool
    gitlab_instance_fingerprint: str
    gitlab_group_id: int | None
    gitlab_project_id: int | None
    scope_name: str
    scope_path: str
    branch: str | None
    allowed_author_emails: list[str]


class LegacyPolicyWire(BaseModel):
    model_config = ConfigDict(extra="forbid")
    active: bool
    allowed_author_emails: list[str]


class EffectiveRepositoryWire(BaseModel):
    model_config = ConfigDict(extra="forbid")
    gitlab_project_id: int
    name: str
    full_path: str
    source: str
    status: str


class PoliciesResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: str
    legacy_fallback: LegacyPolicyWire
    policies: list[PolicyWire]
    repositories: list[EffectiveRepositoryWire] = []
    configuration_revision: int


class PolicyMutationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    allowed_author_emails: list[str] = Field(max_length=500)


class RepositoryPolicyMutationRequest(PolicyMutationRequest):
    branch: str = Field(min_length=1, max_length=255)


class PolicyMutationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID
    scope_type: str
    active: bool = True
    allowed_author_emails: list[str]
    configuration_revision: int


class BranchWire(BaseModel):
    name: str
    commit_sha: str
    default: bool


class BranchesResponse(BaseModel):
    items: list[BranchWire]
