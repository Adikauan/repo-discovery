# Feature 004 Research

## Decisions

### Use GitLab REST API v4 direct-node discovery

**Decision**: List top-level groups for the authenticated credential, direct subgroups for an expanded group, and projects directly owned by that group. Use normalized provider results at the application port.

**Rationale**: The group's projects endpoint defaults to including shared projects while its `include_subgroups` default is false. The adapter must explicitly send `with_shared=false` and `include_subgroups=false` to satisfy the accepted selection semantics. Direct subgroup traversal preserves the visible hierarchy and prevents recursive group project responses from overlapping.

**Alternatives considered**: Recursively list all descendants/projects when a group is selected; rejected because it eagerly fetches data that the user may never expand and risks duplicate project nodes. Include shared projects; rejected by clarification recorded in `spec.md`.

**Source**: [GitLab Groups API](https://docs.gitlab.com/api/groups/) documents top-level group listing, direct subgroup listing, group project listing, `include_subgroups`, and `with_shared` behavior.

### Resolve pagination in the backend for one node at a time

**Decision**: Request up to 100 entities per page, follow the REST API's next-page metadata until the list is complete, and return the complete result set for root or one expanded group's direct children. Any page failure fails that node load; no partial list is presented as complete.

**Rationale**: This keeps provider pagination details out of the frontend contract and avoids requiring the entire GitLab instance hierarchy before interaction. The user can expand other branches while a failed branch is retried.

**Alternatives considered**: Return a GitLab cursor/page token to the frontend; rejected initially because the plan's requested contract prefers complete per-node child lists. Expand every hierarchy branch recursively; rejected due unnecessary network and memory use.

**Source**: [GitLab REST API pagination](https://docs.gitlab.com/api/rest/) documents page/per_page behavior and the per_page maximum of 100.

### Require read API access, with user/credential permissions still authoritative

**Decision**: Document `read_api` as the recommended token scope for group/project REST discovery; `api` also works but grants broader write access and is unnecessary. Effective group and project visibility remains bounded by the token type and the GitLab user's/credential's permissions.

**Rationale**: Feature 003's `read_user` recommendation supports `/user` validation only; that success does not imply discovery access. GitLab documents `read_api` as read access to its API, including groups and projects. Project access tokens can only reach their project, while group access tokens are bounded to their group and descendants.

**Alternatives considered**: Require `api`; rejected because it grants complete read/write API access. Infer discovery permission from Feature 003 validation; rejected because `/user` tests a different endpoint and permission.

**Source**: [GitLab access token scopes](https://docs.gitlab.com/security/tokens/access_token_scopes/) documents `read_api`, `api`, and token-type reach.

### Extend the Feature 003 adapter and reuse its request controls

**Decision**: Extend the application-owned `GitLabConnectionClient` protocol and `HttpGitLabConnectionClient` implementation rather than creating another HTTP client. Reuse the existing config-scoped dependency wiring, finite connect/read/write/pool timeout settings, TLS verification, `PRIVATE-TOKEN` header, no redirects, and no retries.

**Rationale**: The existing adapter already owns URL base-path normalization, safe connection outcomes, MockTransport injection, and secret-safe HTTP behavior. Reusing it avoids duplicated connection policy while keeping GitLab API details in infrastructure.

**Relevant code**: `backend/app/domain/ports/gitlab_connection_client.py`, `backend/app/infrastructure/gitlab/http_gitlab_connection_client.py`, `backend/app/api/dependencies.py`, `backend/app/config.py`, and `backend/tests/unit/infrastructure/gitlab/test_http_gitlab_connection_client.py`.

### Persist intent in normalized rows with an independent optimistic version

**Decision**: Use one lazily created scope-state row for a monotonic scope ETag and separate normalized selected-group and selected-repository rows. Store the originating instance fingerprint per selection so old and current instances can coexist safely.

**Rationale**: A missing state/selection set is a valid empty scope; a state row still allows save-empty and concurrency fencing. Separate scope versioning prevents unrelated Monitoring Configuration edits from creating false scope conflicts. Per-row instance identity prevents same-number IDs from different GitLab installations from colliding. This extends existing rowcount-based conditional-update patterns.

**Alternatives considered**: Store all selection data as JSON or as an expanded project snapshot; rejected because relational uniqueness and group intent must remain explicit. Reuse the Monitoring Configuration revision; rejected because it would conflate unrelated edits with scope concurrency.

**Relevant code**: `backend/app/infrastructure/database/models.py`, `backend/app/infrastructure/database/sqlalchemy_repositories.py`, `backend/app/infrastructure/database/unit_of_work.py`, `backend/alembic/versions/0002_gitlab_credentials.py`, and `backend/tests/integration/test_configuration_concurrency.py`.

### Retain redundant explicit choices and deduplicate only effective coverage

**Decision**: Keep a user's explicitly selected repository even if a selected group currently covers it. Keep overlapping ancestor and subgroup rules too. When deriving an effective repository set later, deduplicate by `(instance identity, project ID)` and ignore rules whose instance fingerprint differs from the active configuration.

**Rationale**: Preserving the explicit choice means removing a group does not erase an independently selected repository. Duplicate effective targets are still prevented by set-based resolution.

**Alternatives considered**: Normalize away redundant repository rows during save; rejected because it loses explicit intent and would change selection after removing a group.

## Existing Project Findings

- Feature 002 routes use `/api/v1/monitoring-configurations/{id}`, Pydantic schemas, RFC 9457 `ProblemDetails`, and `ETag`/`If-Match`; missing update preconditions return 428 and stale edits return 412.
- Monitoring Configurations are soft-retired (`retired_at`); active queries exclude them. Physical deletion cascades via foreign keys. Feature 003 explicitly deletes credentials during soft retirement; scope rows are not credentials and remain under existing config retention behavior.
- Feature 003 has one application-owned GitLab client port and one HTTPX implementation. The implementation accepts a reusable timeout and transport, preserves self-managed URL base paths, uses `PRIVATE-TOKEN`, verifies TLS and disables redirects.
- Feature 001's tree components are visual scaffolding: `TreePanel`, `TreeNodeRow`, and `SelectedItemsPanel` need controlled props and feature-owned selection behavior. Existing route and page composition is in `src/app/routes/routeConfig.tsx` and `MonitoringConfigurationDetailsPage.tsx`.

## Research Gaps

None block the plan. GitLab rate limits and behavior can vary by deployment; the adapter treats provider outcomes as normalized safe failures and does not retry. If direct-child lists prove too large in practice, a later compatible contract may add frontend-visible incremental pagination.
