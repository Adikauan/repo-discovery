from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class SelectedGitLabGroup:
    selection_id: UUID
    instance_fingerprint: str
    gitlab_group_id: int
    name: str
    full_path: str
    parent_group_id: int | None
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class SelectedGitLabRepository:
    selection_id: UUID
    instance_fingerprint: str
    gitlab_project_id: int
    name: str
    full_path: str
    parent_group_id: int | None
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class MiningScope:
    configuration_id: UUID
    version: int
    updated_at: datetime | None
    groups: tuple[SelectedGitLabGroup, ...] = ()
    repositories: tuple[SelectedGitLabRepository, ...] = ()


@dataclass(frozen=True, slots=True)
class EffectiveRepositoryCandidate:
    instance_fingerprint: str
    project_id: int
    ancestor_group_ids: frozenset[int]


def effective_repositories(
    candidates: tuple[EffectiveRepositoryCandidate, ...] | list[EffectiveRepositoryCandidate],
    scope: MiningScope,
    active_instance_fingerprint: str,
) -> tuple[EffectiveRepositoryCandidate, ...]:
    """Deduplicate effective coverage without expanding group rules at save time."""
    selected_groups = {
        group.gitlab_group_id for group in scope.groups
        if group.instance_fingerprint == active_instance_fingerprint
    }
    selected_projects = {
        (repository.instance_fingerprint, repository.gitlab_project_id)
        for repository in scope.repositories
    }
    covered: dict[tuple[str, int], EffectiveRepositoryCandidate] = {}
    for candidate in candidates:
        if candidate.instance_fingerprint != active_instance_fingerprint:
            continue
        key = (candidate.instance_fingerprint, candidate.project_id)
        if key in selected_projects or selected_groups.intersection(candidate.ancestor_group_ids):
            covered.setdefault(key, candidate)
    return tuple(covered[key] for key in sorted(covered))
