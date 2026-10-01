from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class Finding:
    id: UUID
    repository_execution_id: UUID
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

    def __post_init__(self):
        if not 1 <= len(self.rule_id) <= 100 or not 1 <= len(self.rule_version) <= 32:
            raise ValueError("Finding rule identity is invalid.")
        if self.severity != "warning" or self.author_email_state not in {"valid", "missing", "malformed"}:
            raise ValueError("Finding classification is invalid.")
        if (self.author_email_state == "valid") != (self.author_email is not None):
            raise ValueError("Finding author identity is inconsistent.")
        if not 1 <= len(self.title) <= 160 or not 1 <= len(self.summary) <= 500:
            raise ValueError("Finding text is outside the supported bounds.")
        if len(self.commit_hash) not in {40, 64} or any(c not in "0123456789abcdefABCDEF" for c in self.commit_hash):
            raise ValueError("Finding commit hash is invalid.")
        if self.author_name is not None and len(self.author_name) > 200:
            raise ValueError("Finding author name is too long.")
        if self.commit_message_summary is not None and (len(self.commit_message_summary) > 500 or any(ord(c) < 32 and c not in "\t\n\r" for c in self.commit_message_summary)):
            raise ValueError("Finding commit message summary is invalid.")

