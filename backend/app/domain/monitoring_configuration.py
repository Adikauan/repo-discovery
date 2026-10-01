from __future__ import annotations

import re
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from urllib.parse import urlsplit
from uuid import UUID
from app.domain.errors import FieldValidationError
from app.domain.services.email_identity import EmailNotValidError, validate_email


def _utc(value: datetime, field: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")
    return value.astimezone(UTC)


def normalize_name(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise FieldValidationError("name", "required", "Enter a configuration name.")
    return value.strip()


def normalize_description(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise FieldValidationError("description", "invalid", "Enter a valid description.")
    normalized = value.strip()
    return normalized or None


def normalize_gitlab_url(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise FieldValidationError("gitlab_url", "required", "Enter a GitLab instance URL.")
    normalized = value.strip()
    if re.search(r"\s", normalized):
        raise FieldValidationError("gitlab_url", "invalid_url", "Enter an absolute HTTP or HTTPS URL.")
    try:
        parsed = urlsplit(normalized)
        hostname = parsed.hostname
        _ = parsed.port
    except ValueError as error:
        raise FieldValidationError("gitlab_url", "invalid_url", "Enter an absolute HTTP or HTTPS URL.") from error
    if parsed.scheme.lower() not in {"http", "https"} or not hostname:
        raise FieldValidationError("gitlab_url", "invalid_url", "Enter an absolute HTTP or HTTPS URL.")
    if parsed.username is not None or parsed.password is not None:
        raise FieldValidationError(
            "gitlab_url", "credentials_not_allowed", "Do not include credentials in the GitLab instance URL."
        )
    return normalized


def normalize_allowed_author_emails(value: object) -> tuple[str, ...]:
    if value is None:
        value = ()
    if not isinstance(value, (list, tuple)) or len(value) > 500:
        raise FieldValidationError("allowed_author_emails", "invalid", "Enter up to 500 valid email addresses.")
    normalized: set[str] = set()
    for item in value:
        if not isinstance(item, str) or len(item) > 254:
            raise FieldValidationError("allowed_author_emails", "invalid", "Enter valid email addresses no longer than 254 characters.")
        item = item.strip()
        if not item or len(item) > 254:
            raise FieldValidationError("allowed_author_emails", "invalid", "Enter valid email addresses no longer than 254 characters.")
        try:
            valid = validate_email(item, check_deliverability=False).normalized
        except EmailNotValidError as error:
            raise FieldValidationError("allowed_author_emails", "invalid", "Enter a valid email address.") from error
        normalized.add(valid.casefold())
    return tuple(sorted(normalized))


@dataclass(frozen=True, slots=True)
class MonitoringConfiguration:
    id: UUID
    name: str
    description: str | None
    gitlab_url: str
    enabled: bool
    created_at: datetime
    updated_at: datetime
    revision: int = 1
    retired_at: datetime | None = None
    allowed_author_emails: tuple[str, ...] = ()
    author_policy_mode: str = "legacy"

    def __post_init__(self) -> None:
        if self.author_policy_mode not in {"legacy", "scope_aware"}:
            raise FieldValidationError("author_policy_mode", "invalid", "Choose a supported author policy mode.")

    @classmethod
    def create(
        cls,
        *,
        identifier: UUID,
        name: object,
        description: object = None,
        gitlab_url: object,
        now: datetime,
        allowed_author_emails: object = (),
        author_policy_mode: str = "legacy",
    ) -> MonitoringConfiguration:
        return cls(
            id=identifier,
            name=normalize_name(name),
            description=normalize_description(description),
            gitlab_url=normalize_gitlab_url(gitlab_url),
            enabled=False,
            created_at=_utc(now, "created_at"),
            updated_at=_utc(now, "updated_at"),
            allowed_author_emails=normalize_allowed_author_emails(allowed_author_emails),
            author_policy_mode=author_policy_mode,
        )

    def update(
        self,
        *,
        name: object,
        description: object,
        gitlab_url: object,
        enabled: object,
        now: datetime,
        allowed_author_emails: object | None = None,
    ) -> MonitoringConfiguration:
        if not isinstance(enabled, bool):
            raise FieldValidationError("enabled", "invalid", "Choose whether the configuration is enabled.")
        normalized = (
            normalize_name(name),
            normalize_description(description),
            normalize_gitlab_url(gitlab_url),
            enabled,
            normalize_allowed_author_emails(self.allowed_author_emails if allowed_author_emails is None else allowed_author_emails),
        )
        current = (self.name, self.description, self.gitlab_url, self.enabled, self.allowed_author_emails)
        if normalized == current:
            return self
        return replace(
            self,
            name=normalized[0],
            description=normalized[1],
            gitlab_url=normalized[2],
            enabled=normalized[3],
            allowed_author_emails=normalized[4],
            updated_at=_utc(now, "updated_at"),
            revision=self.revision + 1,
        )

    def set_enabled(self, enabled: bool, now: datetime) -> MonitoringConfiguration:
        if self.enabled == enabled:
            return self
        return replace(self, enabled=enabled, updated_at=_utc(now, "updated_at"), revision=self.revision + 1)

    def retire(self, now: datetime) -> MonitoringConfiguration:
        if self.retired_at is not None:
            return self
        return replace(self, retired_at=_utc(now, "retired_at"), updated_at=_utc(now, "updated_at"))

    def switch_to_scope_aware(self, now: datetime) -> MonitoringConfiguration:
        """One-way compatibility transition; legacy data remains retained."""
        if self.author_policy_mode == "scope_aware":
            return self
        return replace(self, author_policy_mode="scope_aware", updated_at=_utc(now, "updated_at"),
                       revision=self.revision + 1)

    def touch(self, now: datetime) -> MonitoringConfiguration:
        return replace(self, updated_at=_utc(now, "updated_at"), revision=self.revision + 1)
