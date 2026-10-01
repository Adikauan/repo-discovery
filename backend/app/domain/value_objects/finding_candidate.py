from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class FindingCandidate:
    rule_id: str
    rule_version: str
    severity: str
    title: str
    summary: str
    commit_hash: str
    author_email: str | None
    author_email_state: str
    author_name: str | None = None
    authored_at: datetime | None = None
    commit_message_summary: str | None = None
    file_path: str | None = None
    line_start: int | None = None
    line_end: int | None = None

