from dataclasses import dataclass


class AuthorPolicyResolutionError(ValueError):
    code = "author_policy_ambiguous"


@dataclass(frozen=True, slots=True)
class AuthorPolicyResolution:
    allowed_author_emails: tuple[str, ...] | None
    source: str


def resolve_author_policy(snapshot, project_id: int, repository_path: str, branch: str) -> AuthorPolicyResolution:
    """Resolve one snapshot-bound policy; None allowlist means detection disabled."""
    policies = tuple(getattr(snapshot, "author_policies", ()))
    fingerprints = {scope.instance_fingerprint.casefold() for scope in (*snapshot.groups, *snapshot.repositories)}
    selected_groups = {group.gitlab_group_id for group in snapshot.groups}
    policies = tuple(p for p in policies if p.instance_fingerprint.casefold() in fingerprints
                     and (p.scope_type != "group" or p.gitlab_group_id in selected_groups))
    repository = [p for p in policies if p.scope_type == "repository_branch"
                  and p.gitlab_project_id == project_id and p.branch == branch]
    if len(repository) > 1:
        raise AuthorPolicyResolutionError("Ambiguous repository branch policy.")
    if repository:
        return AuthorPolicyResolution(repository[0].allowed_author_emails, "repository_branch")

    matches = []
    coverage = [item for item in getattr(snapshot, "repository_group_coverage", ())
                if item.gitlab_project_id == project_id]
    covered_ids = {item.selected_group_id: item.distance_to_repository for item in coverage}
    for policy in policies:
        if policy.scope_type != "group" or not policy.gitlab_group_id:
            continue
        if coverage:
            if policy.gitlab_group_id in covered_ids:
                matches.append((covered_ids[policy.gitlab_group_id], policy))
            continue
        path = repository_path.strip("/").casefold()
        prefix = policy.full_path.strip("/").casefold()
        if path == prefix or path.startswith(prefix + "/"):
            distance = len(path.split("/")) - len(prefix.split("/"))
            matches.append((distance, policy))
    if matches:
        best_depth = min(depth for depth, _ in matches)
        best = [policy for depth, policy in matches if depth == best_depth]
        if len(best) != 1:
            raise AuthorPolicyResolutionError("Ambiguous Group author policy.")
        return AuthorPolicyResolution(best[0].allowed_author_emails, "group")

    if getattr(snapshot, "author_policy_mode", "legacy") == "legacy":
        legacy = tuple(getattr(snapshot, "legacy_allowed_author_emails",
                               getattr(snapshot, "allowed_author_emails", ())))
        return AuthorPolicyResolution(legacy, "legacy")
    return AuthorPolicyResolution(None, "disabled")
