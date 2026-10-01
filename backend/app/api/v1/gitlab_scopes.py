import re
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Path, Response

from app.api.dependencies import get_credential_cipher, get_gitlab_client, get_uow
from app.api.v1.schemas import (GitLabHierarchyNodeResponse, GitLabHierarchyResponse,
                                MiningScopeResponse, ReplaceMiningScopeRequest, scope_response)
from app.application.use_cases.get_gitlab_scope_tree import GetGitLabScopeTree
from app.application.use_cases.get_mining_scope import GetMiningScope
from app.application.use_cases.replace_mining_scope import ReplaceMiningScope
from app.domain.errors import FieldValidationError, MissingPreconditionError
from app.application.use_cases.get_gitlab_connection_status import normalized_url_fingerprint


router = APIRouter(prefix="/monitoring-configurations/{configuration_id}/gitlab-scope", tags=["gitlab-scope"])
_ETAG = re.compile(r'^"?(0|[1-9][0-9]*)"?$')


def _tree_response(nodes):
    return GitLabHierarchyResponse(nodes=[GitLabHierarchyNodeResponse(
        id=node.id, type=node.type, name=node.name, full_path=node.full_path,
        parent_group_id=node.parent_group_id, expandable=node.expandable,
    ) for node in nodes])


def _version(if_match: str | None) -> int:
    if if_match is None:
        raise MissingPreconditionError("Provide the current scope ETag in If-Match.")
    match = _ETAG.fullmatch(if_match.strip())
    if not match:
        raise FieldValidationError("If-Match", "invalid", "Provide a valid scope ETag.")
    return int(match.group(1))


@router.get("/root", response_model=GitLabHierarchyResponse)
def list_root(configuration_id: UUID, uow=Depends(get_uow), cipher=Depends(get_credential_cipher),
              client=Depends(get_gitlab_client)):
    return _tree_response(GetGitLabScopeTree(uow, cipher, client).execute(configuration_id))


@router.get("/groups/{group_id}/children", response_model=GitLabHierarchyResponse)
def list_children(configuration_id: UUID, group_id: Annotated[int, Path(gt=0)],
                  uow=Depends(get_uow), cipher=Depends(get_credential_cipher),
                  client=Depends(get_gitlab_client)):
    return _tree_response(GetGitLabScopeTree(uow, cipher, client).execute(configuration_id, group_id))


@router.get("", response_model=MiningScopeResponse)
def read_scope(configuration_id: UUID, response: Response, uow=Depends(get_uow),
               cipher=Depends(get_credential_cipher), client=Depends(get_gitlab_client)):
    scope, availability = GetMiningScope(uow, cipher, client).execute(configuration_id)
    response.headers["ETag"] = f'"{scope.version}"'
    return scope_response(scope, availability)


@router.put("", response_model=MiningScopeResponse)
def replace_scope(configuration_id: UUID, payload: ReplaceMiningScopeRequest, response: Response,
                  if_match: Annotated[str | None, Header(alias="If-Match")] = None,
                  uow=Depends(get_uow), cipher=Depends(get_credential_cipher),
                  client=Depends(get_gitlab_client)):
    expected_version = _version(if_match)
    groups = [item.model_dump() for item in payload.groups]
    repositories = [item.model_dump() for item in payload.repositories]
    saved = ReplaceMiningScope(uow, cipher, client).execute(
        configuration_id, groups, repositories, expected_version)
    scope, availability = GetMiningScope(uow, cipher, client).execute(configuration_id)
    response.headers["ETag"] = f'"{saved.version}"'
    return scope_response(scope, availability)
