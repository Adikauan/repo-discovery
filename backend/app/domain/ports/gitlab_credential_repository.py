from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CredentialSnapshot:
    configuration_id: UUID
    encrypted_token: bytes
    revision: int
    last_validation_result: str | None
    last_validated_at: datetime | None
    last_successful_validation_at: datetime | None
    validated_url_fingerprint: str | None


class GitLabCredentialRepository(Protocol):
    def get(self, configuration_id: UUID) -> CredentialSnapshot | None: ...
    def replace(self, configuration_id: UUID, encrypted_token: bytes,
                expected_revision: int | None, now: datetime) -> bool: ...
    def remove(self, configuration_id: UUID) -> None: ...
    def update_validation(self, configuration_id: UUID, expected_revision: int, url_fingerprint: str,
                          result: str, checked_at: datetime) -> bool: ...
