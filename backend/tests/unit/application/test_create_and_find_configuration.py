from datetime import UTC, datetime

import pytest

from app.application.use_cases.create_monitoring_configuration import CreateMonitoringConfiguration
from app.application.use_cases.get_monitoring_configuration import GetMonitoringConfiguration
from app.application.use_cases.list_monitoring_configurations import ListMonitoringConfigurations
from app.domain.errors import IdempotencyConflict
from tests.fakes import MemoryUnitOfWork


NOW = datetime(2026, 9, 28, 12, 0, tzinfo=UTC)


def payload(name="Platform repository mining", description="Context", url="https://gitlab.example.com"):
    return {"name": name, "description": description, "gitlab_url": url}


def test_create_without_key_generates_disabled_configuration_and_can_be_retrieved():
    uow = MemoryUnitOfWork()
    result = CreateMonitoringConfiguration(uow, clock=lambda: NOW).execute(payload())

    from uuid import UUID
    identifier = UUID(result.response_snapshot["id"])
    assert identifier is not None
    assert result.response_snapshot["enabled"] is False
    assert GetMonitoringConfiguration(uow).execute(identifier).id == identifier


def test_optional_key_replays_same_result_and_rejects_different_values():
    uow = MemoryUnitOfWork()
    use_case = CreateMonitoringConfiguration(uow, clock=lambda: NOW)

    first = use_case.execute(payload(), idempotency_key="create-request-1")
    replay = use_case.execute(payload(name=" Platform repository mining "), idempotency_key="create-request-1")

    assert replay.response_snapshot["id"] == first.response_snapshot["id"]
    assert replay.replayed is True
    assert len(uow.configurations) == 1

    with pytest.raises(IdempotencyConflict):
        use_case.execute(payload(name="Different"), idempotency_key="create-request-1")


def test_different_keys_or_missing_key_are_distinct_create_intents():
    uow = MemoryUnitOfWork()
    use_case = CreateMonitoringConfiguration(uow, clock=lambda: NOW)
    first = use_case.execute(payload(), idempotency_key="intent-a")
    second = use_case.execute(payload(), idempotency_key="intent-b")
    third = use_case.execute(payload())

    assert len(uow.configurations) == 3
    assert len({first.response_snapshot["id"], second.response_snapshot["id"], third.response_snapshot["id"]}) == 3


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("platform", 1),
        ("PLATFORM", 1),
        ("  repository  ", 1),
        ("", 2),
        (" \t ", 2),
        ("%", 1),
        ("_", 1),
        ("*", 1),
        ("[x]\\", 1),
    ],
)
def test_search_is_trimmed_case_insensitive_literal_substring(query, expected):
    uow = MemoryUnitOfWork()
    use_case = CreateMonitoringConfiguration(uow, clock=lambda: NOW)
    use_case.execute(payload(name="Platform 100%_ *[x]\\ repository"))
    use_case.execute(payload(name="Unrelated service"))

    results = ListMonitoringConfigurations(uow).execute(query)

    assert len(results) == expected
