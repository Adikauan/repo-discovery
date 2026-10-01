from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from app.domain.errors import FieldValidationError
from app.domain.monitoring_configuration import normalize_allowed_author_emails


AuthorPolicyScope = Literal["group", "repository_branch"]


def _positive_id(value: int | None, field: str) -> int | None:
    if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value <= 0):
        raise FieldValidationError(field, "invalid", "Choose a valid GitLab scope item.")
    return value


@dataclass(frozen=True, slots=True)
class AuthorPolicyAuthor:
    normalized_email: str

    @classmethod
    def create(cls, policy_id: UUID, email: object) -> AuthorPolicyAuthor:
        del policy_id  # Ownership is represented by the persistence relationship.
        normalized = normalize_allowed_author_emails([email])
        return cls(normalized_email=normalized[0])


@dataclass(frozen=True, slots=True)
class AuthorPolicy:
    id: UUID
    monitoring_configuration_id: UUID
    scope_type: AuthorPolicyScope
    instance_fingerprint: str
    full_path: str
    gitlab_group_id: int | None
    gitlab_project_id: int | None
    branch: str | None
    allowed_author_emails: tuple[str, ...]

    @classmethod
    def create(
        cls,
        *,
        identifier: UUID,
        configuration_id: UUID,
        instance_fingerprint: str,
        full_path: str,
        allowed_author_emails: object,
        gitlab_group_id: int | None = None,
        gitlab_project_id: int | None = None,
        branch: str | None = None,
    ) -> AuthorPolicy:
        group_id = _positive_id(gitlab_group_id, "gitlab_group_id")
        project_id = _positive_id(gitlab_project_id, "gitlab_project_id")
        if not isinstance(instance_fingerprint, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", instance_fingerprint):
            raise FieldValidationError("instance_fingerprint", "invalid", "Choose a valid GitLab instance.")
        if not isinstance(full_path, str) or not full_path.strip():
            raise FieldValidationError("full_path", "required", "A scope path is required.")

        if group_id is not None and project_id is None and branch is None:
            scope_type: AuthorPolicyScope = "group"
        elif group_id is None and project_id is not None and isinstance(branch, str) and branch.strip():
            scope_type = "repository_branch"
        else:
            raise FieldValidationError("scope_type", "invalid", "Choose a valid Group or repository branch policy.")

        return cls(
            id=identifier,
            monitoring_configuration_id=configuration_id,
            scope_type=scope_type,
            instance_fingerprint=instance_fingerprint.casefold(),
            full_path=full_path.strip(),
            gitlab_group_id=group_id,
            gitlab_project_id=project_id,
            branch=branch if scope_type == "repository_branch" else None,
            allowed_author_emails=normalize_allowed_author_emails(allowed_author_emails),
        )

    @classmethod
    def group(
        cls,
        *,
        identifier: UUID,
        configuration_id: UUID,
        instance_fingerprint: str,
        gitlab_group_id: int,
        full_path: str,
        allowed_author_emails: object,
    ) -> AuthorPolicy:
        return cls.create(
            identifier=identifier,
            configuration_id=configuration_id,
            instance_fingerprint=instance_fingerprint,
            gitlab_group_id=gitlab_group_id,
            full_path=full_path,
            allowed_author_emails=allowed_author_emails,
        )

    @classmethod
    def repository_branch(
        cls,
        *,
        identifier: UUID,
        configuration_id: UUID,
        instance_fingerprint: str,
        gitlab_project_id: int,
        branch: str,
        full_path: str,
        allowed_author_emails: object,
    ) -> AuthorPolicy:
        return cls.create(
            identifier=identifier,
            configuration_id=configuration_id,
            instance_fingerprint=instance_fingerprint,
            gitlab_project_id=gitlab_project_id,
            branch=branch,
            full_path=full_path,
            allowed_author_emails=allowed_author_emails,
        )
