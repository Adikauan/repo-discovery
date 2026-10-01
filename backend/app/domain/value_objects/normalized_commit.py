from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class NormalizedCommit:
    commit_hash: str
    author_email: str | None
    author_name: str | None = None
    authored_at: datetime | None = None
    message: str | None = None
    parent_hashes: tuple[str, ...] = ()
    author_email_malformed: bool = False

    def __post_init__(self):
        if len(self.commit_hash) not in {40, 64} or any(c not in "0123456789abcdefABCDEF" for c in self.commit_hash):
            raise ValueError("Commit hash is invalid.")
        if any(len(value) not in {40, 64} or any(c not in "0123456789abcdefABCDEF" for c in value)
               for value in self.parent_hashes):
            raise ValueError("Commit parent identity is invalid.")
