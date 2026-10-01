from datetime import UTC, datetime, timedelta

import pytest

from app.application.use_cases.create_monitoring_configuration import CreateMonitoringConfiguration
from app.application.use_cases.update_monitoring_configuration import UpdateMonitoringConfiguration
from app.domain.errors import StaleConfigurationError
from tests.fakes import MemoryUnitOfWork


def test_update_and_stale_conflict_preserve_saved_values():
    now = datetime(2026, 9, 28, tzinfo=UTC)
    uow = MemoryUnitOfWork()
    created = CreateMonitoringConfiguration(uow, clock=lambda: now).execute({"name": "Name", "gitlab_url": "https://gitlab.example"})
    identifier = next(iter(uow.configurations))
    update = UpdateMonitoringConfiguration(uow, clock=lambda: now + timedelta(minutes=1))
    changed = update.execute(identifier, {"name": "Changed", "description": None, "gitlab_url": "https://gitlab.example", "enabled": True}, 1)
    assert changed.id == identifier and changed.created_at == now and changed.revision == 2 and changed.enabled
    with pytest.raises(StaleConfigurationError):
        update.execute(identifier, {"name": "Stale", "description": None, "gitlab_url": "https://gitlab.example", "enabled": True}, 1)
    assert uow.configuration_repository.get_active(identifier).name == "Changed"
    assert created.response_snapshot["id"] == str(identifier)
