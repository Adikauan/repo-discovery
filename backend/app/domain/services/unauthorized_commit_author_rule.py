import re

from app.domain.services.email_identity import EmailNotValidError, validate_email
from app.domain.value_objects.finding_candidate import FindingCandidate


def _normalized(value: str) -> str:
    return validate_email(value.strip(), check_deliverability=False).normalized.casefold()


def _safe_text(value: str | None, limit: int = 500) -> str | None:
    if value is None:
        return None
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", value)[:limit].strip() or None


class UnauthorizedCommitAuthorRule:
    identifier = "unauthorized-commit-author"
    version = "1"

    def execute(self, commits, allowed_author_emails) -> tuple[FindingCandidate, ...]:
        allowed = {_normalized(item) for item in allowed_author_emails}
        result = []
        seen = set()
        for commit in commits:
            if commit.commit_hash in seen:
                continue
            seen.add(commit.commit_hash)
            raw_email = commit.author_email
            malformed_type = commit.author_email_malformed
            trimmed = raw_email.strip() if isinstance(raw_email, str) else ""
            state, email = ("malformed", None) if malformed_type else ("missing", None)
            if trimmed:
                try:
                    email = _normalized(trimmed)
                    state = "valid"
                except (EmailNotValidError, ValueError):
                    state = "malformed"
            if state == "valid" and email in allowed:
                continue
            suffix = f" ({email})" if email else ""
            name = _safe_text(commit.author_name, 200)
            result.append(FindingCandidate(
                rule_id=self.identifier, rule_version=self.version, severity="warning",
                title="Unauthorized commit author",
                summary=f"Commit author{suffix} is not in the allowed commit author list.",
                commit_hash=commit.commit_hash.lower(), author_email=email, author_email_state=state,
                author_name=name, authored_at=commit.authored_at,
                commit_message_summary=_safe_text(commit.message),
            ))
        return tuple(result)
