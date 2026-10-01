from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.domain.monitoring_configuration import MonitoringConfiguration


def test_stale_conditional_update_cannot_overwrite_newer_postgres_version(pg_uow_factory):
    now = datetime.now(UTC)
    first = pg_uow_factory(); second = pg_uow_factory()
    original = MonitoringConfiguration.create(identifier=uuid4(), name="Original", gitlab_url="https://gitlab.example", now=now)
    first.configuration_repository.add(original); first.commit()
    first_loaded = first.configuration_repository.get_active(original.id)
    stale_loaded = second.configuration_repository.get_active(original.id)
    newer = first_loaded.update(name="Newer", description=None, gitlab_url=first_loaded.gitlab_url,
                                enabled=False, now=now + timedelta(seconds=1))
    assert first.configuration_repository.update(newer, 1); first.commit()
    stale = stale_loaded.update(name="Stale", description=None, gitlab_url=stale_loaded.gitlab_url,
                                enabled=False, now=now + timedelta(seconds=2))
    assert second.configuration_repository.update(stale, 1) is False
    second.rollback()
    assert first.configuration_repository.get_active(original.id).name == "Newer"
