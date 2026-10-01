from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.domain.monitoring_configuration import MonitoringConfiguration

NOW = datetime(2026, 9, 28, tzinfo=UTC)


def config():
    return MonitoringConfiguration.create(identifier=uuid4(), name="Initial", gitlab_url="https://gitlab.example", now=NOW)


def test_update_preserves_identity_creation_time_and_noop_revision():
    original = config()
    unchanged = original.update(name=original.name, description=None, gitlab_url=original.gitlab_url,
                                enabled=False, now=NOW + timedelta(days=1))
    changed = original.update(name="Updated", description="Note", gitlab_url=original.gitlab_url,
                              enabled=False, now=NOW + timedelta(days=1))
    assert unchanged is original and unchanged.revision == 1
    assert changed.id == original.id and changed.created_at == original.created_at
    assert changed.updated_at == NOW + timedelta(days=1) and changed.revision == 2


def test_enable_disable_changes_only_lifecycle_values():
    original = config()
    enabled = original.set_enabled(True, NOW + timedelta(minutes=1))
    assert enabled.enabled and enabled.revision == 2
    assert enabled.set_enabled(True, NOW + timedelta(minutes=2)) is enabled
    assert enabled.set_enabled(False, NOW + timedelta(minutes=3)).enabled is False
