from datetime import UTC, datetime
from uuid import uuid4

from app.application.ports.create_request_store import CreateRequestReceipt
from app.domain.monitoring_configuration import MonitoringConfiguration
from app.infrastructure.database.models import CreateRequestReceiptRecord, MonitoringConfigurationRecord


def test_postgres_persists_uuid_and_utc_aware_timestamps(pg_uow_factory):
    now = datetime.now(UTC)
    uow = pg_uow_factory()
    config = MonitoringConfiguration.create(identifier=uuid4(), name="Persist me", description=None,
        gitlab_url="https://gitlab.example", now=now)
    uow.configuration_repository.add(config)
    uow.commit()
    loaded = uow.configuration_repository.get_active(config.id)
    assert loaded.id == config.id and loaded.enabled is False
    assert loaded.created_at.tzinfo is not None and loaded.updated_at.tzinfo is not None


def test_postgres_search_escapes_like_wildcards(pg_uow_factory):
    uow = pg_uow_factory()
    now = datetime.now(UTC)
    for name in ("A 100%_ *[x]\\! repo", "Unrelated service"):
        uow.configuration_repository.add(MonitoringConfiguration.create(identifier=uuid4(), name=name,
            gitlab_url="https://gitlab.example", now=now))
    uow.commit()
    for needle in ("%", "_", "*", "[x]", "\\", "!"):
        assert len(uow.configuration_repository.list_active(needle)) == 1


def test_postgres_create_receipt_and_configuration_share_transaction(pg_uow_factory):
    uow = pg_uow_factory()
    config = MonitoringConfiguration.create(identifier=uuid4(), name="Atomic", gitlab_url="https://gitlab.example",
        now=datetime.now(UTC))
    uow.configuration_repository.add(config)
    uow.receipt_repository.add(CreateRequestReceipt("request-1", "f" * 64, {"id": str(config.id)}))
    uow.commit()
    assert uow.receipt_repository.get("request-1").response_snapshot["id"] == str(config.id)
    assert uow.session.get(MonitoringConfigurationRecord, config.id) is not None
    assert uow.session.get(CreateRequestReceiptRecord, "request-1") is not None
