from uuid import uuid4
import pytest
from pydantic import ValidationError
from app.domain.entities.execution_snapshot import ExecutionSnapshotV1, ExecutionSnapshotV2, ExecutionSnapshotV3, load_execution_snapshot


def payload():
    return dict(configuration_id=uuid4(), configuration_name='Original', configuration_enabled=False,
        gitlab_url='https://gitlab.example.com', configuration_revision=1, scope_version=0, trigger_type='manual')


def test_snapshot_roundtrip_empty_and_frozen():
    item = ExecutionSnapshotV1(**payload())
    assert item.groups == () and item.repositories == () and item.schema_version == 1
    assert ExecutionSnapshotV1.model_validate_json(item.model_dump_json()) == item
    with pytest.raises(ValidationError):
        item.configuration_name = 'changed'


@pytest.mark.parametrize('field', ['token', 'encrypted_token', 'credential_revision', 'authorization'])
def test_secret_fields_rejected(field):
    with pytest.raises(ValidationError):
        ExecutionSnapshotV1(**payload(), **{field: 'sensitive'})


def test_unknown_version_and_required_fields_rejected():
    with pytest.raises(ValidationError):
        ExecutionSnapshotV1(**payload(), schema_version=2)
    with pytest.raises(ValidationError):
        ExecutionSnapshotV1()


def test_snapshot_keeps_normalized_allowed_authors_and_legacy_defaults_empty():
    from datetime import UTC, datetime
    from app.domain.monitoring_configuration import MonitoringConfiguration
    from app.domain.entities.mining_scope import MiningScope
    now = datetime(2026, 9, 30, tzinfo=UTC)
    config = MonitoringConfiguration.create(identifier=uuid4(), name="Historical", gitlab_url="https://gitlab.example",
        now=now, allowed_author_emails=[" Bob@example.com ", "alice@example.com"])
    snapshot = ExecutionSnapshotV1.capture(config, MiningScope(config.id, 0, None))
    assert snapshot.allowed_author_emails == ("alice@example.com", "bob@example.com")
    legacy = ExecutionSnapshotV1(**payload())
    assert legacy.allowed_author_emails == ()
    scheduled = ExecutionSnapshotV1.capture(config, MiningScope(config.id, 0, None), trigger_type="scheduled",
        scheduled_occurrence=now, schedule_version=1)
    assert scheduled.allowed_author_emails == snapshot.allowed_author_emails


def test_v2_policy_snapshot_roundtrips_and_v1_remains_readable():
    from datetime import UTC, datetime
    from app.domain.monitoring_configuration import MonitoringConfiguration
    from app.domain.entities.mining_scope import MiningScope
    now = datetime(2026, 9, 30, tzinfo=UTC)
    config = MonitoringConfiguration.create(identifier=uuid4(), name="Scope-aware", gitlab_url="https://gitlab.example",
        now=now, author_policy_mode="scope_aware")
    captured = ExecutionSnapshotV2.capture(config, MiningScope(config.id, 0, None))
    assert captured.author_policy_mode == "scope_aware"
    assert load_execution_snapshot(captured.model_dump()) == captured
    legacy = ExecutionSnapshotV1(**payload())
    assert load_execution_snapshot(legacy.model_dump()) == legacy


def test_v3_snapshots_explicit_target_rules_without_secrets_and_legacy_versions_have_no_inferred_targets():
    from datetime import UTC, datetime
    from app.domain.entities.mining_scope import MiningScope
    from types import SimpleNamespace
    from app.domain.monitoring_configuration import MonitoringConfiguration
    now = datetime(2026, 10, 1, tzinfo=UTC)
    config = MonitoringConfiguration.create(identifier=uuid4(), name="Targeted", gitlab_url="https://gitlab.example", now=now)
    # Historical V3 deserialization keeps only the snapshot-shaped legacy fields;
    # no active TargetBranchRule domain entity exists in the Policy-sourced model.
    target = SimpleNamespace(scope_type="repository", instance_fingerprint="a" * 64,
        gitlab_scope_id=42, full_path="team/api", branch_name="quality")
    snapshot = ExecutionSnapshotV3.capture(config, MiningScope(config.id, 0, None), target_branch_rules=[target])
    assert snapshot.schema_version == 3 and snapshot.target_branch_rules[0].branch_name == "quality"
    assert load_execution_snapshot(snapshot.model_dump()) == snapshot
    assert "credential" not in snapshot.model_dump_json().casefold()
    assert not hasattr(ExecutionSnapshotV1(**payload()), "target_branch_rules")
    assert not hasattr(ExecutionSnapshotV2(**payload()), "target_branch_rules")


def test_v4_freezes_policy_targets_but_excludes_legacy_group_and_global_author_fallbacks():
    from datetime import UTC, datetime
    from app.domain.entities.execution_snapshot import ExecutionSnapshotV4, SnapshotMiningTarget
    from app.domain.entities.mining_scope import MiningScope
    from app.domain.monitoring_configuration import MonitoringConfiguration

    now = datetime(2026, 10, 1, tzinfo=UTC)
    config = MonitoringConfiguration.create(identifier=uuid4(), name="Policy targets",
        gitlab_url="https://gitlab.example", now=now, allowed_author_emails=["legacy@example.com"])
    target = SnapshotMiningTarget(gitlab_project_id=42, instance_fingerprint="a" * 64,
        name="API", full_path="team/api", branch="dev-larah", allowed_author_emails=("allowed@example.com",))
    snapshot = ExecutionSnapshotV4.capture(config, MiningScope(config.id, 0, None), mining_targets=[target])

    assert snapshot.schema_version == 4
    assert [(item.gitlab_project_id, item.branch) for item in snapshot.mining_targets] == [(42, "dev-larah")]
    assert snapshot.author_policies[0].allowed_author_emails == ("allowed@example.com",)
    assert snapshot.group_author_policies == ()
    assert snapshot.legacy_allowed_author_emails == ()
    assert snapshot.allowed_author_emails == ()
    assert load_execution_snapshot(snapshot.model_dump()) == snapshot
    assert "legacy@example.com" not in snapshot.model_dump_json()
    assert "credential" not in snapshot.model_dump_json().casefold()
