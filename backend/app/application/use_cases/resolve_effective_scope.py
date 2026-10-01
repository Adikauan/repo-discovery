from dataclasses import dataclass

from app.application.use_cases.get_gitlab_connection_status import normalized_url_fingerprint
from app.domain.value_objects.mining_failure import MiningFailure


@dataclass(frozen=True, slots=True)
class ScopeResolution:
    repositories: tuple
    failures: int = 0
    # Selected Group IDs paired with the number of hierarchy edges from that
    # selected Group to the repository. Smaller distance means closer scope.
    group_distances: dict[int, tuple[tuple[int, int], ...]] | None = None


class EffectiveScopeResolver:
    def __init__(self, provider):
        self.provider = provider

    def execute(self, snapshot, token):
        fingerprint = normalized_url_fingerprint(snapshot.gitlab_url)
        if any(item.instance_fingerprint != fingerprint for item in (*snapshot.groups, *snapshot.repositories)):
            raise MiningFailure("gitlab_instance_mismatch")
        resolved = {}
        group_distances = {}
        failures = 0
        for selected in snapshot.repositories:
            try:
                project = self.provider.get_project_scope(snapshot.gitlab_url, token, selected.gitlab_project_id)
                resolved[project.id] = project
            except MiningFailure as error:
                if error.code in {"repository_not_found", "repository_forbidden"}:
                    failures += 1
                else:
                    raise
        for selected in snapshot.groups:
            try:
                self.provider.get_group(snapshot.gitlab_url, token, selected.gitlab_group_id)
            except MiningFailure as error:
                if error.code in {"repository_not_found", "repository_forbidden"}:
                    failures += 1
                    continue
                raise
            queue = [(selected.gitlab_group_id, 0)]
            visited = set()
            while queue:
                group_id, distance = queue.pop(0)
                if group_id in visited:
                    continue
                visited.add(group_id)
                try:
                    groups, projects = self.provider.group_children(snapshot.gitlab_url, token, group_id)
                except MiningFailure as error:
                    if error.code in {"repository_not_found", "repository_forbidden"}:
                        failures += 1
                        continue
                    raise
                queue.extend((item.id, distance + 1) for item in groups)
                for project in projects:
                    resolved[project.id] = project
                    group_distances.setdefault(project.id, []).append((selected.gitlab_group_id, distance))
        ordered = tuple(sorted(resolved.values(), key=lambda item: (item.full_path.casefold(), item.id)))
        return ScopeResolution(ordered, failures, {
            project_id: tuple(sorted(set(coverage))) for project_id, coverage in group_distances.items()
        })
