from app.application.use_cases.resolve_effective_scope import EffectiveScopeResolver
from app.application.use_cases.get_gitlab_connection_status import normalized_url_fingerprint
from app.domain.entities.execution_snapshot import ExecutionSnapshotV1, SnapshotGroup, SnapshotRepository
from tests.unit.test_create_manual_execution import setup


def test_scope_resolves_snapshot_only_and_deduplicates_direct_and_group_results():
    _, config = setup()
    fingerprint = normalized_url_fingerprint(config.gitlab_url)
    snapshot = ExecutionSnapshotV1(configuration_id=config.id, configuration_name="historic", configuration_enabled=False,
        gitlab_url=config.gitlab_url, groups=(SnapshotGroup(gitlab_group_id=1, name="g", full_path="g", instance_fingerprint=fingerprint),),
        repositories=(SnapshotRepository(gitlab_project_id=9, name="p", full_path="g/p", instance_fingerprint=fingerprint),), trigger_type="manual")
    class Provider:
        def get_project_scope(self, *_): return type("P", (), {"id": 9, "name": "p", "full_path": "g/p"})()
        def get_group(self, *_): return object()
        def group_children(self, url, token, group_id):
            if group_id == 1:
                subgroup = type("G", (), {"id": 2, "name": "child", "full_path": "g/child"})()
                project = type("P", (), {"id": 9, "name": "p", "full_path": "g/p"})()
                return (subgroup,), (project,)
            project = type("P", (), {"id": 10, "name": "nested", "full_path": "g/child/nested"})()
            return (), (project,)
    result = EffectiveScopeResolver(Provider()).execute(snapshot, "secret")
    assert [item.id for item in result.repositories] == [10, 9]
    assert [item.full_path for item in result.repositories] == ["g/child/nested", "g/p"]
    assert result.failures == 0
    assert result.group_distances == {9: ((1, 0),), 10: ((1, 1),)}
