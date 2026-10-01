from datetime import UTC, datetime
from uuid import uuid4

from app.domain.monitoring_configuration import MonitoringConfiguration
from app.infrastructure.database.models import MonitoringConfigurationRecord


def test_retirement_keeps_row_and_hides_from_active_reads(pg_uow_factory):
    uow = pg_uow_factory()
    item = MonitoringConfiguration.create(identifier=uuid4(), name="Keep history context",
        gitlab_url="https://gitlab.example", now=datetime.now(UTC))
    uow.configuration_repository.add(item); uow.commit()
    assert uow.credential_repository.replace(item.id, b"ciphertext", None, datetime.now(UTC)); uow.commit()
    assert uow.configuration_repository.retire(item.retire(datetime.now(UTC))); uow.credential_repository.remove(item.id); uow.commit()
    assert uow.configuration_repository.get_active(item.id) is None
    assert uow.configuration_repository.list_active() == []
    retained = uow.session.get(MonitoringConfigurationRecord, item.id)
    assert retained.name == "Keep history context" and retained.retired_at is not None
    assert uow.credential_repository.get(item.id) is None
