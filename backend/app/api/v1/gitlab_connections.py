from uuid import UUID

from fastapi import APIRouter, Body, Depends, Response

from app.api.dependencies import get_credential_cipher, get_gitlab_client, get_uow
from app.api.v1.schemas import (GitLabConnectionStatusResponse, GitLabCredentialRequest,
                                GitLabValidationRequest, GitLabValidationResponse,
                                GitLabCandidateValidationRequest, GitLabCandidateValidationResponse)
from app.application.use_cases.get_gitlab_connection_status import GetGitLabConnectionStatus
from app.application.use_cases.remove_gitlab_credential import RemoveGitLabCredential
from app.application.use_cases.save_gitlab_credential import SaveGitLabCredential
from app.application.use_cases.validate_gitlab_connection import ValidateGitLabConnection
from app.application.use_cases.validate_gitlab_candidate import ValidateGitLabCandidate
from app.domain.errors import FieldValidationError, GitLabDiscoveryError

router = APIRouter(
    prefix="/monitoring-configurations/{configuration_id}/gitlab-connection",
    tags=["gitlab-connections"],
)

candidate_router = APIRouter(prefix="/gitlab-connections", tags=["gitlab-connections"])


@candidate_router.post("/validate-candidate", response_model=GitLabCandidateValidationResponse)
def validate_candidate(payload: GitLabCandidateValidationRequest,
                       client=Depends(get_gitlab_client)):
    try:
        result = ValidateGitLabCandidate(client).execute(payload.gitlab_url, payload.token)
    except FieldValidationError:
        raise
    except TimeoutError as error:
        raise GitLabDiscoveryError("timeout") from error
    except Exception:
        # Provider exceptions can include request headers; never pass their text to logs or clients.
        raise GitLabDiscoveryError("provider_unavailable") from None
    return GitLabCandidateValidationResponse(**{
        "state": result.state,
        "result": result.result,
        "message": result.message,
        "checked_at": result.checked_at,
    })


@router.get("", response_model=GitLabConnectionStatusResponse)
def get_status(configuration_id: UUID, uow=Depends(get_uow)):
    return GitLabConnectionStatusResponse.from_domain(
        GetGitLabConnectionStatus(uow).execute(configuration_id))


@router.put("/credential", response_model=GitLabConnectionStatusResponse)
def save_credential(configuration_id: UUID, payload: GitLabCredentialRequest,
                    uow=Depends(get_uow), cipher=Depends(get_credential_cipher)):
    return GitLabConnectionStatusResponse.from_domain(
        SaveGitLabCredential(uow, cipher).execute(configuration_id, payload.token))


@router.delete("/credential", status_code=204)
def remove_credential(configuration_id: UUID, uow=Depends(get_uow)):
    RemoveGitLabCredential(uow).execute(configuration_id)
    return Response(status_code=204)


@router.post("/validate", response_model=GitLabValidationResponse)
def validate_connection(configuration_id: UUID,
                        payload: GitLabValidationRequest = Body(default_factory=GitLabValidationRequest),
                        uow=Depends(get_uow), cipher=Depends(get_credential_cipher),
                        client=Depends(get_gitlab_client)):
    result = ValidateGitLabConnection(uow, cipher, client).execute(configuration_id, payload.token)
    return GitLabValidationResponse.from_domain(result)
