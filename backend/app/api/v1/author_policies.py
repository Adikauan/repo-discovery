import re
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Path, Response

from app.api.dependencies import get_uow, get_credential_cipher, get_gitlab_repository_client
from app.api.v1.author_policy_schemas import (BranchesResponse, PoliciesResponse,
    PolicyMutationRequest, PolicyMutationResponse, RepositoryPolicyMutationRequest)
from app.application.use_cases.author_policies import AuthorPolicies, ListRepositoryBranches, MigrateAuthorPolicyMode
from app.domain.errors import FieldValidationError, MissingPreconditionError

router = APIRouter(prefix="/monitoring-configurations/{configuration_id}/author-policies", tags=["author-policies"])
ETAG = re.compile(r'^"?(0|[1-9][0-9]*)"?$')


def _revision(value):
    if value is None:
        raise MissingPreconditionError("Provide the current configuration ETag in If-Match.")
    match = ETAG.fullmatch(value.strip())
    if not match:
        raise FieldValidationError("If-Match", "invalid", "Provide a valid configuration ETag.")
    return int(match.group(1))


@router.get("", response_model=PoliciesResponse)
def list_policies(configuration_id: UUID, uow=Depends(get_uow), provider=Depends(get_gitlab_repository_client),
                  cipher=Depends(get_credential_cipher)):
    return AuthorPolicies(uow, provider=provider, cipher=cipher).list(configuration_id)


@router.get("/repositories/{project_id}/branches", response_model=BranchesResponse)
def list_branches(configuration_id: UUID, project_id: Annotated[int, Path(gt=0)],
                   uow=Depends(get_uow), provider=Depends(get_gitlab_repository_client),
                   cipher=Depends(get_credential_cipher)):
    values = ListRepositoryBranches(uow, provider, cipher).execute(configuration_id, project_id)
    return {"items": [item.__dict__ for item in values]}


@router.put("/groups/{group_id}", response_model=PolicyMutationResponse)
def upsert_group(configuration_id: UUID, group_id: Annotated[int, Path(gt=0)], payload: PolicyMutationRequest,
                 response: Response, if_match: Annotated[str | None, Header(alias="If-Match")] = None,
                 uow=Depends(get_uow)):
    policy, revision = AuthorPolicies(uow).upsert(configuration_id, expected_revision=_revision(if_match),
        scope_type="group", scope_id=group_id, branch=None, authors=payload.allowed_author_emails)
    response.headers["ETag"] = f'"{revision}"'
    return PolicyMutationResponse(id=policy.id, scope_type=policy.scope_type,
        allowed_author_emails=list(policy.allowed_author_emails), configuration_revision=revision)


@router.put("/repositories/{project_id}/branches", response_model=PolicyMutationResponse)
def upsert_repository_branch(configuration_id: UUID, project_id: Annotated[int, Path(gt=0)],
                 payload: RepositoryPolicyMutationRequest, response: Response,
                 if_match: Annotated[str | None, Header(alias="If-Match")] = None,
                 uow=Depends(get_uow), provider=Depends(get_gitlab_repository_client),
                 cipher=Depends(get_credential_cipher)):
    revision = _revision(if_match)
    branches = ListRepositoryBranches(uow, provider, cipher).execute(configuration_id, project_id)
    if not any(item.name == payload.branch for item in branches):
        raise FieldValidationError("branch", "unavailable", "Choose a branch returned by GitLab for this repository.")
    policy, updated_revision = AuthorPolicies(uow, provider=provider, cipher=cipher).upsert(configuration_id, expected_revision=revision,
        scope_type="repository_branch", scope_id=project_id, branch=payload.branch,
        authors=payload.allowed_author_emails)
    response.headers["ETag"] = f'"{updated_revision}"'
    return PolicyMutationResponse(id=policy.id, scope_type=policy.scope_type,
        allowed_author_emails=list(policy.allowed_author_emails), configuration_revision=updated_revision)


@router.delete("/{policy_id}", status_code=204)
def delete_policy(configuration_id: UUID, policy_id: UUID,
                  if_match: Annotated[str | None, Header(alias="If-Match")] = None,
                  uow=Depends(get_uow)):
    AuthorPolicies(uow).delete(configuration_id, policy_id, _revision(if_match))
    return Response(status_code=204)


@router.post("/migration", response_model=PoliciesResponse)
def migrate_policy_mode(configuration_id: UUID, response: Response,
                        if_match: Annotated[str | None, Header(alias="If-Match")] = None,
                        uow=Depends(get_uow), provider=Depends(get_gitlab_repository_client),
                        cipher=Depends(get_credential_cipher)):
    configuration = MigrateAuthorPolicyMode(uow).execute(configuration_id, _revision(if_match))
    response.headers["ETag"] = f'"{configuration.revision}"'
    return AuthorPolicies(uow, provider=provider, cipher=cipher).list(configuration_id)
