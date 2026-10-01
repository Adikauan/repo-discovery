from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

ConnectionState = Literal["not_configured", "configured_not_validated", "validated", "failed"]


@dataclass(frozen=True, slots=True)
class GitLabConnectionStatus:
    configuration_id: UUID
    credential_configured: bool
    state: ConnectionState
    latest_result: str | None = None
    last_validation_at: datetime | None = None
    last_successful_validation_at: datetime | None = None
