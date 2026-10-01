# Feature 004 Quickstart and Validation

Feature 004 requires Feature 003's configured GitLab URL and encrypted credential. For private group/project discovery, use a token with `read_api` scope and only the GitLab visibility needed for the intended scope. Feature 003's connection validation calls `/user`; a successful result does not verify discovery permissions. GitLab documents `read_api` as read access to the API; `api` also works but is broader. Never place a token in commands, logs, screenshots, or test fixtures.

## Start the application

Use the repository's existing local PostgreSQL/Compose workflow from the root `.env`. Ensure `GITLAB_CREDENTIAL_ENCRYPTION_KEYS` contains a persistent Fernet key in the local ignored secret configuration; do not use an ephemeral key if you need credentials from a previous run. Start/rebuild the backend so Alembic applies `0003_gitlab_scope`, then run the existing Vite frontend.

## Manual scenario

1. Open an active Monitoring Configuration with a GitLab URL and configured credential, then navigate to its GitLab Scope page.
2. Confirm only top-level groups load initially. Expand one group and nested subgroups; confirm direct repositories appear as repository nodes and no shared projects appear.
3. Select one group without expanding all descendants, one repository under another group, and one repository also covered by a selected group. Confirm the summary shows explicit rules and identifies any overlap.
4. Filter and collapse the tree; confirm the selected rules remain in the summary. Save and confirm a successful save advances the scope ETag.
5. Reopen the page and confirm the same explicit group and repository rules appear. Save an empty selection and verify the configuration enabled state remains unchanged.
6. Remove the GitLab credential or replace it with one lacking access. Confirm saved rules remain and inaccessible items are marked unavailable/unresolved; remove one explicitly and save.
7. Change the GitLab URL to a different instance. Confirm old selections are marked stale and are never looked up against the new instance, even if numeric IDs match. Select a new-instance entity and save while retaining a stale rule, then explicitly remove the stale rule and save.
8. Open two editor sessions. Save in one, then try to save the older draft in the other; verify the stale save receives a conflict and does not overwrite the first result.

## Automated validation

From `backend/`, run database-independent tests:

```powershell
.venv\Scripts\python.exe -m pytest tests\unit\application\test_gitlab_scope.py tests\unit\infrastructure\gitlab\test_gitlab_scope_client.py tests\api\test_gitlab_scope.py
```

Against an isolated PostgreSQL database, run migrations, scope persistence/CAS, and retirement integration tests:

```powershell
$env:TEST_DATABASE_URL = "postgresql+psycopg://<test-user>:<test-password>@127.0.0.1:<port>/<isolated-test-db>"
.venv\Scripts\python.exe -m pytest tests\integration\test_gitlab_scope_persistence.py tests\integration\test_migrations.py
```

All GitLab calls in normal tests use HTTPX `MockTransport`; no live GitLab token or service is required. Verify failed later pages do not return partial success, no provider response/token leaks, and stale origin IDs are never requested against the active URL.

From the repository root, run the Feature 004 frontend suites and build:

```powershell
npm test -- --run src/test/features/monitoring-configurations/gitlab-scope-tree.test.tsx src/test/features/monitoring-configurations/gitlab-scope-selection.test.tsx src/test/features/monitoring-configurations/gitlab-scope-reconciliation.test.tsx src/test/features/monitoring-configurations/gitlab-scope-accessibility.test.tsx
npm run build
```

Expected result: users can browse and save explicit scope intent; all pages of the current root/expanded node are represented; reloaded rules match the saved explicit selection set; stale/unavailable rules remain until removed; repeated/overlapping coverage does not produce duplicate effective repository targets; no credential or provider payload is exposed; and no mining operation is started.
