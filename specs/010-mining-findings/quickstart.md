# Feature 010 Validation Quickstart

This guide validates the approved Finding workflow after implementation. It does not define implementation code.

## Prerequisites

- PostgreSQL available and `TEST_DATABASE_URL` set for integration tests.
- Backend dependencies installed in the existing backend environment.
- Frontend dependencies installed from the root `package-lock.json`.
- GitLab provider mocked for standard tests; no live credentials are needed.

## Start or refresh the local application

1. From the repository root, run `docker compose up -d --build backend`. The backend container applies pending Alembic migrations before starting Uvicorn.
2. Start the frontend with `npm run dev` and open `http://localhost:5173` (the default API base is `http://localhost:8000/api/v1`). If Vite config loading fails with `spawn EPERM` in a restricted Windows environment, use `npm run dev -- --configLoader native`.
3. Confirm `http://localhost:8000/health` returns `{"status":"ok"}`. In `/openapi.json`, `CreateConfigurationRequest` must include `allowed_author_emails`, and the execution findings route must be present.
4. Create a Monitoring Configuration with a valid `allowed_author_emails` value and confirm it is returned normalized. Remove any temporary smoke-test configuration after verification.

If a valid configuration form submission returns the generic “Review the fields and try again” response, first verify the running API contract. An older backend rejects the Feature 010 `allowed_author_emails` field because its request schema uses `extra=forbid`; rebuild/restart the backend before changing valid form data.

## Validate configuration and historical policy

1. Create a Monitoring Configuration with `allowedAuthorEmails` containing padded and mixed-case values.
2. Confirm values are validated, trimmed, case-folded, deduplicated, and sorted.
3. Create a manual execution and confirm the immutable snapshot contains the normalized list internally.
4. Update the live configuration to a different list using its current ETag.
5. Process the historical execution fixture and confirm the old snapshot policy is used; public snapshot DTOs do not expose the policy unless separately approved.

## Validate baseline and incremental findings

1. Mock the Feature 008 selected/default branch with HEAD `commit-1` and no checkpoint; do not assume a branch name.
2. Run the existing manual execution pipeline. Expect a successful RepositoryExecution, baseline `commit-1`, and zero findings.
3. Add `commit-2` with a non-allowlisted valid author; run a second execution using the same Monitoring Configuration/project/branch checkpoint.
4. Expect exactly one persisted warning Finding, repository/execution finding counts of one, and checkpoint `commit-2`.
5. Attempt to persist the same `(repositoryExecutionId, ruleId, ruleVersion, commitHash)` identity twice and verify the database uniqueness constraint prevents a duplicate Finding.

## Validate failures and bounds

- Mock the checkpoint becoming unreachable from current branch HEAD. Expect normalized repository failure, no Finding, and unchanged checkpoint.
- Mock more than `MINING_MAX_COMMITS_PER_REPOSITORY_EXECUTION` commits. Expect `commit_range_limit_exceeded`, no Finding rows for the rejected range, and unchanged checkpoint.
- Inject provider, rule, and finding transaction failures. Expect no checkpoint advancement; other repositories in the execution continue.
- Return duplicate commit SHAs across pages and verify one evaluation/persist attempt per SHA.

## Validate API and dashboard

- Query execution-scoped and repository-scoped finding lists, then finding detail.
- Confirm nested repository ownership, safe DTO fields, deterministic ordering, normalized not-found errors, and no credential/internal error disclosure.
- Open `/executions/:id` and verify zero findings has a truthful empty state, while populated findings show rule, historical repository path, commit, author identity state/email, safe summary, severity, and timestamp.
- Verify loading, retry/error feedback, keyboard navigation, semantic headings/list/table labels, and narrow viewport behavior using existing frontend conventions.

## Commands

Run the repository's existing backend test command from `backend/` (normally `pytest`). Run frontend tests and build from the repository root (normally `npm test` and `npm run build`). Run Alembic migration validation and PostgreSQL integration tests where `TEST_DATABASE_URL` is available. Do not claim PostgreSQL constraint/rollback checks passed if that database is unavailable.

## Contract references

- [Finding APIs](contracts/findings-api.md)
- [Configuration and execution snapshot](contracts/configuration-snapshot.md)
- [Normalized GitLab commit port](contracts/gitlab-commit-port.md)
- [Data model](data-model.md)
