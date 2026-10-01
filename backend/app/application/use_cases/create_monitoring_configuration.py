from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Callable
from uuid import uuid4

from app.application.ports.create_request_store import CreateRequestReceipt
from app.application.ports.monitoring_configuration_repository import UnitOfWork
from app.domain.errors import DuplicateIdempotencyKey, FieldValidationError, IdempotencyConflict
from app.domain.monitoring_configuration import (
    MonitoringConfiguration,
    normalize_allowed_author_emails,
    normalize_description,
    normalize_gitlab_url,
    normalize_name,
)


@dataclass(frozen=True, slots=True)
class CreateConfigurationResult:
    response_snapshot: dict[str, Any]
    replayed: bool = False


def _response_snapshot(configuration: MonitoringConfiguration) -> dict[str, Any]:
    return {
        "id": str(configuration.id),
        "name": configuration.name,
        "description": configuration.description,
        "gitlab_url": configuration.gitlab_url,
        "enabled": configuration.enabled,
        "created_at": configuration.created_at.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        "updated_at": configuration.updated_at.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        "version": str(configuration.revision),
        "allowed_author_emails": list(configuration.allowed_author_emails),
    }


def _fingerprint(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class CreateMonitoringConfiguration:
    def __init__(self, uow: UnitOfWork, clock: Callable[[], datetime] | None = None):
        self.uow = uow
        self.clock = clock or (lambda: datetime.now(UTC))

    def execute(
        self, payload: dict[str, Any], idempotency_key: str | None = None
    ) -> CreateConfigurationResult:
        try:
            name = normalize_name(payload.get("name"))
            description = normalize_description(payload.get("description"))
            gitlab_url = normalize_gitlab_url(payload.get("gitlab_url"))
            allowed_author_emails = normalize_allowed_author_emails(payload.get("allowed_author_emails", []))
            normalized_payload = {"name": name, "description": description, "gitlab_url": gitlab_url,
                                  "allowed_author_emails": allowed_author_emails}
            fingerprint = _fingerprint(normalized_payload)

            if idempotency_key:
                existing = self.uow.receipt_repository.get(idempotency_key)
                if existing:
                    if existing.request_fingerprint != fingerprint:
                        raise IdempotencyConflict("This idempotency key was already used with different values.")
                    return CreateConfigurationResult(existing.response_snapshot.copy(), replayed=True)

            configuration = MonitoringConfiguration.create(
                identifier=uuid4(),
                name=name,
                description=description,
                gitlab_url=gitlab_url,
                now=self.clock(),
                allowed_author_emails=allowed_author_emails,
            )
            snapshot = _response_snapshot(configuration)
            self.uow.configuration_repository.add(configuration)
            if idempotency_key:
                self.uow.receipt_repository.add(
                    CreateRequestReceipt(idempotency_key, fingerprint, snapshot)
                )
            self.uow.commit()
            return CreateConfigurationResult(snapshot)
        except DuplicateIdempotencyKey:
            self.uow.rollback()
            if not idempotency_key:
                raise
            existing = self.uow.receipt_repository.get(idempotency_key)
            if existing is None:
                raise
            if existing.request_fingerprint != fingerprint:
                raise IdempotencyConflict("This idempotency key was already used with different values.")
            return CreateConfigurationResult(existing.response_snapshot.copy(), replayed=True)
        except Exception:
            self.uow.rollback()
            raise
