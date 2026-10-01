from datetime import UTC, datetime
import logging
from uuid import uuid4
from types import SimpleNamespace

from app.application.use_cases.get_gitlab_connection_status import normalized_url_fingerprint
from app.domain.author_policy import AuthorPolicy
from app.domain.errors import AuthorPolicyApiError, NotFoundError, StaleConfigurationError
from app.application.use_cases.resolve_effective_scope import EffectiveScopeResolver
from app.domain.value_objects.mining_failure import MiningFailure

logger = logging.getLogger(__name__)


def _scope_items(scope, kind, identifier, fingerprint):
    values = scope.groups if kind == "group" else scope.repositories
    field = "gitlab_group_id" if kind == "group" else "gitlab_project_id"
    return [item for item in values if getattr(item, field) == identifier and item.instance_fingerprint == fingerprint]


def _effective_repositories(uow, configuration, scope, provider, cipher):
    if provider is None or cipher is None:
        # Compatibility for isolated unit callers; HTTP operations always inject both dependencies.
        return tuple(SimpleNamespace(id=item.gitlab_project_id, name=item.name, full_path=item.full_path)
            for item in scope.repositories)
    fingerprint = normalized_url_fingerprint(configuration.gitlab_url)
    credential = uow.credential_repository.get(configuration.id)
    if (credential is None or credential.last_validation_result != "success"
            or credential.validated_url_fingerprint != fingerprint):
        raise AuthorPolicyApiError("gitlab_credential_missing")
    # End the read transaction before external provider calls. Mutation paths still
    # use the configuration revision/CAS check after resolution.
    uow.commit()
    try:
        token = cipher.decrypt(credential.encrypted_token)
        if not token:
            raise ValueError("empty credential")
        context = SimpleNamespace(gitlab_url=configuration.gitlab_url,
            groups=scope.groups, repositories=scope.repositories)
        resolved = EffectiveScopeResolver(provider).execute(context, token)
        if resolved.failures:
            raise AuthorPolicyApiError("repository_forbidden")
        return resolved.repositories
    except AuthorPolicyApiError:
        raise
    except MiningFailure as error:
        code = error.code if error.code in AuthorPolicyApiError.DETAILS else "repository_invalid_response"
        raise AuthorPolicyApiError(code) from error
    except Exception as error:
        raise AuthorPolicyApiError("gitlab_credential_missing") from error


class AuthorPolicies:
    def __init__(self, uow, clock=None, provider=None, cipher=None):
        self.uow = uow
        self.clock = clock or (lambda: datetime.now(UTC))
        self.provider, self.cipher = provider, cipher

    def list(self, configuration_id, provider=None, cipher=None):
        configuration = self.uow.configuration_repository.get_active(configuration_id)
        if configuration is None:
            raise NotFoundError("Monitoring Configuration was not found.")
        scope = self.uow.mining_scope_repository.get(configuration_id)
        fingerprint = normalized_url_fingerprint(configuration.gitlab_url)
        effective = _effective_repositories(self.uow, configuration, scope,
            provider if provider is not None else self.provider,
            cipher if cipher is not None else self.cipher)
        active_projects = {item.id for item in effective}
        policies = self.uow.author_policy_repository.list_for_configuration(configuration_id)
        legacy = tuple(configuration.allowed_author_emails)
        return {"mode": configuration.author_policy_mode,
            "legacy_fallback": {"active": configuration.author_policy_mode == "legacy",
                                "allowed_author_emails": legacy},
            "repositories": [{"gitlab_project_id": item.id, "name": item.name, "full_path": item.full_path,
                "source": "direct" if any(row.gitlab_project_id == item.id for row in scope.repositories) else "group",
                "status": "configured" if any(p.scope_type == "repository_branch" and p.gitlab_project_id == item.id
                    and p.instance_fingerprint == fingerprint for p in policies) else "policy_required"}
                for item in effective],
            "policies": [{"id": str(p.id), "scope_type": p.scope_type,
                "active": p.scope_type == "repository_branch" and p.gitlab_project_id in active_projects
                    and p.instance_fingerprint == fingerprint,
                "gitlab_instance_fingerprint": p.instance_fingerprint,
                "gitlab_group_id": p.gitlab_group_id, "gitlab_project_id": p.gitlab_project_id,
                "scope_name": p.full_path.rsplit("/", 1)[-1], "scope_path": p.full_path,
                "branch": p.branch, "allowed_author_emails": list(p.allowed_author_emails)}
                for p in policies if p.scope_type == "repository_branch"],
            "configuration_revision": configuration.revision}

    def upsert(self, configuration_id, *, expected_revision, scope_type, scope_id, branch, authors):
        configuration = self.uow.configuration_repository.lock_active(configuration_id)
        if configuration is None:
            raise NotFoundError("Monitoring Configuration was not found.")
        if configuration.revision != expected_revision:
            raise StaleConfigurationError("This Monitoring Configuration has changed. Reload and reapply your edits.")
        fingerprint = normalized_url_fingerprint(configuration.gitlab_url)
        scope = self.uow.mining_scope_repository.get(configuration_id)
        if scope_type != "repository_branch":
            raise AuthorPolicyApiError("group_policy_discontinued")
        effective = _effective_repositories(self.uow, configuration, scope,
            self.provider, self.cipher)
        matches = [item for item in effective if item.id == scope_id]
        if not matches:
            raise AuthorPolicyApiError("scope_repository_not_selected")
        item = matches[0]
        policy = AuthorPolicy.create(identifier=uuid4(), configuration_id=configuration_id,
            instance_fingerprint=fingerprint, full_path=item.full_path, allowed_author_emails=authors,
            gitlab_group_id=None, gitlab_project_id=scope_id, branch=branch)
        updated = configuration.touch(self.clock())
        if not self.uow.configuration_repository.update(updated, expected_revision):
            self.uow.rollback()
            raise StaleConfigurationError("This Monitoring Configuration has changed. Reload and reapply your edits.")
        try:
            self.uow.author_policy_repository.upsert(policy)
            self.uow.commit()
        except Exception:
            self.uow.rollback()
            logger.error("Author policy persistence failed", extra={"configuration_id": str(configuration_id),
                "scope_type": scope_type, "scope_id": scope_id})
            raise
        return policy, updated.revision

    def delete(self, configuration_id, policy_id, expected_revision):
        configuration = self.uow.configuration_repository.lock_active(configuration_id)
        if configuration is None:
            raise NotFoundError("Monitoring Configuration was not found.")
        if configuration.revision != expected_revision:
            raise StaleConfigurationError("This Monitoring Configuration has changed. Reload and reapply your edits.")
        if not self.uow.author_policy_repository.delete(policy_id, configuration_id):
            raise AuthorPolicyApiError("author_policy_not_found")
        updated = configuration.touch(self.clock())
        if not self.uow.configuration_repository.update(updated, expected_revision):
            self.uow.rollback()
            raise StaleConfigurationError("This Monitoring Configuration has changed. Reload and reapply your edits.")
        self.uow.commit()
        return updated.revision


class MigrateAuthorPolicyMode:
    def __init__(self, uow, clock=None):
        self.uow = uow
        self.clock = clock or (lambda: datetime.now(UTC))

    def execute(self, configuration_id, expected_revision):
        configuration = self.uow.configuration_repository.lock_active(configuration_id)
        if configuration is None:
            raise NotFoundError("Monitoring Configuration was not found.")
        if configuration.revision != expected_revision:
            raise StaleConfigurationError("This Monitoring Configuration has changed. Reload and reapply your edits.")
        updated = configuration.switch_to_scope_aware(self.clock())
        if updated != configuration and not self.uow.configuration_repository.update(updated, expected_revision):
            self.uow.rollback()
            raise StaleConfigurationError("This Monitoring Configuration has changed. Reload and reapply your edits.")
        self.uow.commit()
        return updated


class ListRepositoryBranches:
    def __init__(self, uow, provider, cipher):
        self.uow, self.provider, self.cipher = uow, provider, cipher

    def execute(self, configuration_id, project_id):
        configuration = self.uow.configuration_repository.get_active(configuration_id)
        if configuration is None:
            raise NotFoundError("Monitoring Configuration was not found.")
        fingerprint = normalized_url_fingerprint(configuration.gitlab_url)
        scope = self.uow.mining_scope_repository.get(configuration_id)
        selected = _effective_repositories(self.uow, configuration, scope, self.provider, self.cipher)
        if not any(item.id == project_id for item in selected):
            raise AuthorPolicyApiError("scope_repository_not_selected")
        credential = self.uow.credential_repository.get(configuration_id)
        if (credential is None or credential.last_validation_result != "success"
                or credential.validated_url_fingerprint != fingerprint or self.cipher is None):
            raise AuthorPolicyApiError("gitlab_credential_missing")
        self.uow.rollback()
        try:
            token = self.cipher.decrypt(credential.encrypted_token)
        except Exception as error:
            raise AuthorPolicyApiError("gitlab_credential_missing") from error
        if not token:
            raise AuthorPolicyApiError("gitlab_credential_missing")
        try:
            return self.provider.list_branches(configuration.gitlab_url, token, project_id)
        except Exception as error:
            code = getattr(error, "code", None)
            if code not in AuthorPolicyApiError.DETAILS:
                if code == "repository_timeout": code = "repository_timeout"
                elif code == "repository_forbidden": code = "repository_forbidden"
                elif code == "repository_not_found": code = "repository_not_found"
                else: code = "repository_invalid_response"
            logger.warning("GitLab branch discovery failed", extra={"configuration_id": str(configuration_id),
                "gitlab_project_id": project_id, "error_code": code})
            raise AuthorPolicyApiError(code) from error
