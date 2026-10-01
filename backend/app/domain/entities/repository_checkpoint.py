from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class RepositoryCheckpoint:
    id: UUID
    monitoring_configuration_id: UUID
    gitlab_project_id: int
    branch: str
    last_successful_commit_hash: str
    updated_at: datetime

    def __post_init__(self):
        if self.gitlab_project_id <= 0 or not self.branch.strip():
            raise ValueError("Repository checkpoint identity is invalid.")
        value = self.last_successful_commit_hash
        if len(value) not in {40, 64} or any(c not in "0123456789abcdefABCDEF" for c in value):
            raise ValueError("Repository checkpoint commit hash is invalid.")

