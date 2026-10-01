from dataclasses import dataclass

from app.application.use_cases.get_gitlab_connection_status import normalized_url_fingerprint
from app.application.use_cases.resolve_effective_scope import EffectiveScopeResolver
from app.domain.errors import FieldValidationError


@dataclass(frozen=True, slots=True)
class ResolvedMiningTarget:
    gitlab_project_id: int
    instance_fingerprint: str
    name: str
    full_path: str
    branch: str
    allowed_author_emails: tuple[str, ...]


class ResolveMiningTargets:
    """Derive the complete mining target set from current Scope and repository Policies."""

    def __init__(self, provider):
        self.provider = provider

    def execute(self, configuration, scope, token, policies):
        from types import SimpleNamespace

        fingerprint = normalized_url_fingerprint(configuration.gitlab_url)
        context = SimpleNamespace(gitlab_url=configuration.gitlab_url, groups=scope.groups,
            repositories=scope.repositories)
        effective = EffectiveScopeResolver(self.provider).execute(context, token)
        if effective.failures:
            raise FieldValidationError("scope", "unavailable",
                "The current GitLab scope could not be fully resolved. Refresh the scope and try again.")
        by_repository = {}
        for policy in policies:
            if policy.instance_fingerprint != fingerprint or policy.scope_type != "repository_branch":
                continue
            by_repository.setdefault(policy.gitlab_project_id, []).append(policy)
        missing = [item.full_path for item in effective.repositories if not by_repository.get(item.id)]
        if missing:
            raise FieldValidationError("policies", "incomplete",
                "Configure at least one branch Policy for every repository in the effective Scope.")
        result = []
        for repository in effective.repositories:
            for policy in by_repository[repository.id]:
                result.append(ResolvedMiningTarget(repository.id, fingerprint, repository.name,
                    repository.full_path, policy.branch, tuple(policy.allowed_author_emails)))
        return tuple(sorted(result, key=lambda item: (item.full_path.casefold(), item.gitlab_project_id, item.branch)))
