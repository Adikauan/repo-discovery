from dataclasses import dataclass

from app.domain.value_objects.gitlab_hierarchy_node import GitLabHierarchyNode


@dataclass(frozen=True, slots=True)
class GitLabDiscoveryResult:
    outcome: str
    nodes: tuple[GitLabHierarchyNode, ...] = ()

    @property
    def succeeded(self) -> bool:
        return self.outcome == "success"
