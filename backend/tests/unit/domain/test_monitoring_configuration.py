from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.domain.errors import FieldValidationError
from app.domain.monitoring_configuration import MonitoringConfiguration


NOW = datetime(2026, 9, 28, 12, 0, tzinfo=UTC)


def test_create_normalizes_name_description_and_url_and_starts_disabled():
    config = MonitoringConfiguration.create(
        identifier=uuid4(),
        name="  Platform mining  ",
        description="  Useful context  ",
        gitlab_url="  https://gitlab.example.com/group  ",
        now=NOW,
    )

    assert config.name == "Platform mining"
    assert config.description == "Useful context"
    assert config.gitlab_url == "https://gitlab.example.com/group"
    assert config.enabled is False
    assert config.created_at == config.updated_at == NOW
    assert config.revision == 1


@pytest.mark.parametrize("value", [None, "", "   ", "\t\n"])
def test_create_rejects_empty_trimmed_name(value):
    with pytest.raises(FieldValidationError) as error:
        MonitoringConfiguration.create(
            identifier=uuid4(), name=value, description=None,
            gitlab_url="https://gitlab.example.com", now=NOW,
        )
    assert error.value.field == "name"


@pytest.mark.parametrize("value", [None, "", "   ", "gitlab.example.com", "ftp://gitlab.example.com", "https:///missing-host"])
def test_create_rejects_missing_or_invalid_gitlab_url(value):
    with pytest.raises(FieldValidationError) as error:
        MonitoringConfiguration.create(
            identifier=uuid4(), name="valid", description=None, gitlab_url=value, now=NOW,
        )
    assert error.value.field == "gitlab_url"


@pytest.mark.parametrize("description", [None, "", "   ", "\n\t"])
def test_create_normalizes_blank_description_to_absent(description):
    config = MonitoringConfiguration.create(
        identifier=uuid4(), name="valid", description=description,
        gitlab_url="http://gitlab.example.com", now=NOW,
    )
    assert config.description is None


def test_create_rejects_invalid_port_and_whitespace_inside_url():
    for url in ("https://gitlab.example.com:99999", "https://gitlab.example.com/a b"):
        with pytest.raises(FieldValidationError) as error:
            MonitoringConfiguration.create(
                identifier=uuid4(), name="valid", description=None, gitlab_url=url, now=NOW,
            )
        assert error.value.field == "gitlab_url"


@pytest.mark.parametrize("url", [
    "https://user@gitlab.example.com",
    "https://user:secret-token@gitlab.example.com",
])
def test_create_rejects_gitlab_url_user_info(url):
    with pytest.raises(FieldValidationError) as error:
        MonitoringConfiguration.create(
            identifier=uuid4(), name="valid", description=None, gitlab_url=url, now=NOW,
        )
    assert error.value.field == "gitlab_url"
    assert error.value.code == "credentials_not_allowed"


def test_allowed_authors_are_trimmed_casefolded_deduplicated_and_sorted():
    config = MonitoringConfiguration.create(identifier=uuid4(), name="valid", gitlab_url="https://gitlab.example",
        now=NOW, allowed_author_emails=[" Alice@Example.com ", "bob@example.com", "alice@example.com"])
    assert config.allowed_author_emails == ("alice@example.com", "bob@example.com")


@pytest.mark.parametrize("emails", [["nope"], ["x" * 255 + "@example.com"], ["a@example.com"] * 501])
def test_allowed_authors_reject_invalid_or_oversized_policy(emails):
    with pytest.raises(FieldValidationError):
        MonitoringConfiguration.create(identifier=uuid4(), name="valid", gitlab_url="https://gitlab.example",
            now=NOW, allowed_author_emails=emails)
