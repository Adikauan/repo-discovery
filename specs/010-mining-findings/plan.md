# Implementation Plan: Mining Findings

**Branch**: `010-mining-findings` | **Date**: 2026-09-30 | **Spec**: [spec.md](spec.md)

## Summary

Extend Feature 008's repository mining pipeline with a deterministic Unauthorized Commit Author rule, durable immutable Finding records, and per-configuration/repository/branch checkpoints. Capture normalized allowed author emails in each new Feature 006 execution snapshot. A first successful run establishes a baseline without scanning earlier commits; subsequent runs inspect a bounded complete commit range, persist findings and advance the checkpoint atomically with the successful repository result. Expose findings through read-only APIs and the existing Feature 007 dashboard. Manual and Feature 009 scheduled executions continue through the same pipeline.

## Technical Context

**Language/Version**: Python 3.14 (backend), TypeScript (frontend)
**Primary Dependencies**: Existing FastAPI, SQLAlchemy, Alembic, Pydantic, React, Vite, Material UI, React Router; add `email-validator>=2.3,<3` for deterministic syntax validation of configured and provider author addresses
**Storage**: PostgreSQL
**Testing**: Existing pytest backend suites, frontend test/accessibility tooling, and PostgreSQL integration tests when `TEST_DATABASE_URL` is available
**Target Platform**: Existing web application and backend deployment
**Project Type**: Full-stack web application with Clean Architecture
**Performance Goals**: Process at most 1,000 commits per repository execution by default; configurable range 1–10,000; no unbounded history traversal or new unbounded concurrency
**Constraints**: Preserve Feature 006 lifecycle and active-execution guarantees; Feature 008 bounded repository concurrency and provider isolation; Feature 009 manual/scheduled pipeline parity; immutable snapshots; no credentials in snapshots/findings/logs; no Finding triage workflow
**Scale/Scope**: One deterministic commit-author rule and bounded historical commit ranges, immutable findings, three read paths, existing dashboard Findings section

## Constitution Check

- **Clean Architecture / domain-centered rules**: pass. Email normalization and rule evaluation remain domain logic; orchestration and persistence remain application responsibilities; HTTPX/GitLab DTOs and SQLAlchemy stay in infrastructure.
- **Explicit contracts**: pass. Extend current configuration and execution snapshot contracts compatibly and define read-only Finding API schemas.
- **External integration abstraction**: pass. Add normalized commit and history operations to the GitLab-owned port; provider DTOs remain in infrastructure.
- **Secure by construction**: pass. Snapshot contains only normalized policy emails, never credentials; malformed provider email is not retained; safe error taxonomy is returned.
- **Immutable history / one mining pipeline**: pass. Findings attach to RepositoryExecution and are append-only; manual and scheduled executions invoke Feature 008's existing pipeline.
- **Lifecycle / migrations / verification**: pass with migration-managed persistence, explicit atomicity boundaries, domain/application/API/UI tests, and PostgreSQL validation.
- **Reusable accessible UX / incremental simplicity**: pass. Reuse existing dashboard Findings section and shared loading/error/empty/status patterns; no charting or new frontend dependency.

No constitution exception is requested.

## Design Decisions

### Rule and pipeline

Extend `MiningRule` / `MiningRuleResult` so rules return normalized zero-or-more finding candidates as well as rule facts. Keep `RepositorySummaryRule` intact and add `UnauthorizedCommitAuthorRule`. `ProcessRepository` obtains normalized repository branch/HEAD and the eligible commit range through an application-owned GitLab port, builds normalized context, invokes the configured Feature 008 rules including the new rule, then delegates persistence to its unit of work. The rule itself does not perform I/O or access persistence.

The author rule compares trimmed Unicode case-folded emails. Valid allowed values are normalized and deduplicated when Monitoring Configuration is written and copied into the immutable execution snapshot. The author name is informational only and never participates in identity. Missing/malformed provider author emails yield a `warning` finding with `author_email = null` and an enum identity state; malformed raw input is discarded. An empty allowed set treats every valid author as unauthorized.

### Commit range and checkpoint

Use the Feature 008 selected/default branch. Read the branch HEAD SHA from normalized repository metadata. A missing checkpoint means baseline: persist current HEAD only alongside successful repository completion, with no historical commit retrieval or findings. Otherwise retrieve commits strictly after the saved SHA through the captured HEAD, deduplicate by full SHA, and normalize them into deterministic oldest-to-newest evaluation order. The adapter must follow all pagination links/continuation metadata, validate each page, and fail rather than return a partial range.

The configured `MINING_MAX_COMMITS_PER_REPOSITORY_EXECUTION` defaults to 1,000 and accepts integer values from 1 through 10,000. Fetch at most the configured limit plus one commit to detect overflow. Overflow fails the RepositoryExecution with `commit_range_limit_exceeded`; do not persist candidates or move the checkpoint. No timestamp-based `since` filter is used for correctness because checkpointing is commit-identity based. Use GitLab's Commits API `ref_name` revision range with complete pagination, and the commit refs operation to establish that the old checkpoint remains reachable from the selected branch. If reachability cannot be established or history was rewritten, fail with normalized `repository_checkpoint_unreachable`; do not reset.

The checkpoint key is `(monitoring_configuration_id, gitlab_project_id, branch)`, protected by a PostgreSQL unique constraint. Since Feature 006 prevents overlapping executions per configuration and Feature 008 prevents duplicate RepositoryExecution per execution/project, checkpoint writes still use a short transaction and conditional/upsert protection to handle retries/concurrent persistence safely. Checkpoint advances to the HEAD captured at the beginning of that repository processing only after all work for that repository succeeds.

### Persistence and transaction boundaries

Add `Finding` and `RepositoryCheckpoint` using Alembic. `Finding` has a required FK to `RepositoryExecution`; MiningExecution is derived through that relation. Finding uniqueness is `(repository_execution_id, rule_id, rule_version, commit_hash)` for commit-based detections. Finding count is updated from the successfully persisted set/owned rows, not from uncommitted candidates. Rule facts stay typed; no generic arbitrary rule-output blob is introduced.

Do not hold database transactions over provider calls. Use short transactions for configuration/snapshot writes, reads, then after all GitLab and rule work a single repository result transaction that inserts findings, updates RepositoryExecution summary/status/count, advances checkpoint, and commits as one unit. On rollback, the repository is safely marked failed in a separate short transaction, leaving the previous checkpoint and zero committed findings for that range. Execution aggregation continues to use the Feature 008 orchestration after repository workers finish.

### GitLab retrieval

Use the existing GitLab REST adapter. The Commits API returns commit id, author identity, authored date, message, and parent IDs; `ref_name` supports revision ranges and the endpoint is paginated. Use provider pagination continuation rather than relying on total headers; GitLab documents that commit responses omit `x-total` and `x-total-pages`. Enforce the safety limit while reading pages. Use the commit refs operation or another adapter-supported graph check to validate reachability; never interpret a missing checkpoint as a fresh baseline. Only normalized models cross into application/domain layers. No clone, archive, diff, or file-content retrieval is needed for this rule.

Retry policy remains Feature 008's existing bounded provider policy, if one exists; this feature adds no retry subsystem. Auth, authorization, not-found, malformed response, and timeout errors are normalized and are not retried unless already explicitly approved by Feature 008.

### APIs and dashboard

Add read-only list endpoints for execution-scoped findings and repository-execution-scoped findings, plus Finding detail using existing API route, pagination/order, and Problem Details conventions. Verify ownership on nested routes. Stable ordering is `authoredAt DESC NULLS LAST, id ASC` as defined in the API contract. Basic repository/rule/severity filters are optional; no arbitrary search language or mutation routes.

Replace Feature 008's Findings unavailable content in the existing dashboard component with API-backed persisted Finding cards/list/table. Keep persisted execution/repository finding counters as summary values; zero is an honest empty result. Display rule, repository path, optional file/line context, commit hash, valid author email or safe identity state, safe summary, `warning` severity, and authored/detected timestamps. Loading, normalized error/retry, empty, and populated states remain accessible and responsive. No separate finding detail route is required.

### Local runtime update

The frontend's create-configuration request includes `allowed_author_emails`, so the running backend must use the Feature 010 request schema. For the Compose development environment, rebuild/recreate it with `docker compose up -d --build backend`; the container command applies pending Alembic migrations before Uvicorn starts. Verify `/health`, then inspect `/openapi.json` for both `CreateConfigurationRequest.allowed_author_emails` and the execution findings route before testing the form. A stale backend may reject the otherwise valid field under its strict request schema and surface the generic validation message; this is a deployment-version mismatch, not a reason to omit the policy from the frontend request.

## Project Structure

### Documentation

```text
specs/010-mining-findings/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── findings-api.md
│   ├── gitlab-commit-port.md
│   └── configuration-snapshot.md
├── checklists/
│   ├── requirements.md
│   └── findings.md
└── tasks.md
```

### Source Code

```text
backend/app/domain/
├── entities/finding.py
├── entities/repository_checkpoint.py
├── monitoring_configuration.py
├── entities/execution_snapshot.py
├── services/mining_rule.py
├── services/unauthorized_commit_author_rule.py
└── value_objects/normalized_commit.py
backend/app/application/
├── ports/gitlab_repository_client.py
├── ports/finding_repository.py
├── ports/repository_checkpoint_repository.py
└── use_cases/process_repository.py
backend/app/infrastructure/
├── gitlab/http_gitlab_repository_client.py
├── database/models.py
└── database/sqlalchemy_repositories.py
backend/app/api/v1/
├── schemas.py
├── execution_schemas.py
├── main.py
├── executions.py
├── repository_executions.py
└── findings.py
backend/alembic/versions/
└── <new migration for findings and checkpoints>
backend/tests/
├── unit/domain/
├── unit/application/
├── api/
└── integration/
src/features/monitoring-configurations/
├── api/<existing configuration client files>
└── components/<allowed author email editor in existing form>
src/features/executions/
├── api/<existing execution client files>
└── components/ExecutionFindingsSection.tsx
src/test/features/executions/
└── <existing test layout>
```

The implementation must follow actual repository conventions if exact file names differ; these boundaries are ownership guidance, not a mandate to create unused abstractions. `ExecutionFindingsSection` extends the existing Feature 007/008 section in place.

**Structure Decision**: Extend the existing backend Clean Architecture packages and frontend feature folders. No new project, service, or state-management dependency is introduced.

## Implementation Phases

1. **Persistence/contract foundation**: allowed-email configuration and snapshot, Finding/checkpoint schema, normalized commit contracts, migration and compatibility defaults.
2. **Rule processing**: bounded range/reachability adapter, baseline/incremental checkpoint service, deterministic author rule, atomic repository finding/checkpoint persistence, counters and normalized failure handling.
3. **Read and presentation**: read-only APIs and safe DTOs, then existing dashboard Findings integration.
4. **Validation**: mocked provider tests, rule/application/API/frontend coverage, PostgreSQL uniqueness/rollback/concurrency/migration checks, and existing manual/scheduled parity tests.

## Complexity Tracking

No constitution violations. Two new persistence entities are justified because durable findings and a stable incremental baseline are explicit domain requirements. Typed nullable identity metadata is justified to explain missing/malformed provider emails without retaining malformed raw values. `email-validator` is the one new dependency: email syntax validation is a core configuration/rule requirement, hand-written regular expressions are error-prone, and the same validation must classify provider identities consistently. Disable DNS deliverability checks so execution is deterministic and offline; the package still supplies syntax validation only.
