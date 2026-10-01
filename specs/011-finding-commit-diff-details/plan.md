# Implementation Plan: Finding Commit Diff Details

**Branch**: `011-finding-commit-diff-details` | **Date**: 2026-09-30 | **Spec**: [spec.md](spec.md)

## Summary

Extend the existing Feature 010 Finding read flow with an on-demand, read-only commit-diff operation. The backend derives the project ID, commit SHA, GitLab connection and instance identity only from the persisted Finding, its RepositoryExecution, and the parent execution snapshot. A normalized GitLab adapter result is bounded before returning it to a responsive accessible dialog in the existing Execution Dashboard. Full patches are not persisted and this feature needs no migration.

## Technical Context

**Language/Version**: Python 3.14; TypeScript
**Primary Dependencies**: Existing FastAPI, Pydantic, SQLAlchemy, HTTPX, React, Vite, Material UI, React Router and test/accessibility tooling; no new dependency planned.
**Storage**: Existing PostgreSQL records are read only; no new table or migration.
**Testing**: pytest unit/application/API/adapter suites; frontend component/API/accessibility tests; PostgreSQL tests only if existing transaction/query behavior is touched.
**Target Platform**: Existing backend API and browser dashboard.
**Project Type**: Full-stack web application following Clean Architecture.
**Performance Goals**: Do not fetch diffs on Findings-list load; per user action perform one bounded diff lookup. Return at most 100 changed-file entries, at most 256 KiB UTF-8 diff text per file, and at most 2 MiB cumulative UTF-8 diff text per response.
**Constraints**: Preserve Finding immutability and Feature 010 detection; use secure runtime credential resolution and snapshot instance fingerprint; never accept provider lookup identifiers from the browser; no patch persistence, migrations, polling, code-review workflow, or AI.
**Scale/Scope**: One commit-diff read endpoint and one detail interaction in the existing Findings section.

## Constitution Check

- **Clean Architecture / one rule owner**: pass. The API delegates to an application query; GitLab calls live behind the existing port/adapter. Finding detection remains unchanged.
- **Explicit contracts**: pass. Add a normalized read response and safe Problem Details cases; no raw GitLab DTOs cross the infrastructure boundary.
- **Secure by construction**: pass. Credentials are resolved transiently through established services, never returned/logged; clients cannot choose project, commit, URL, or token.
- **Immutable history**: pass. The Finding remains the historical record; diff is a live lookup against its persisted commit identity and snapshot instance. A later unavailable diff does not alter the Finding.
- **Migration-managed persistence**: pass. No persistence change is planned.
- **Risk-based verification**: pass. Cover endpoint ownership derivation, bounded payloads, provider failure normalization, no eager fetch, and accessible interaction.
- **Reusable accessible UX / simplicity**: pass. Reuse dashboard patterns and MUI dialog; no additional UI dependency.

No constitution exception is requested.

## Design Decisions

### Retrieval and authority

Use the existing Finding as the only public lookup key: `GET /api/v1/findings/{finding_id}/diff`. The query loads the Finding, owning RepositoryExecution, parent MiningExecution and immutable snapshot. It validates commit-based rule applicability, required commit hash/project identity, configured connection availability, and equality between active and snapshot GitLab instance identity before provider access. It resolves the current secure credential only after identity validation, using the existing credential service and established lifetime. No request query/body field can override project, SHA, URL, or credentials. Do not query current Monitoring Configuration values to replace historical repository or instance context.

The application asks the GitLab-owned port for the commit diff using stable project ID and the Finding's stored commit hash. The infrastructure adapter calls GitLab's `GET /projects/:id/repository/commits/:sha/diff` endpoint and maps path, diff, new/deleted/renamed and collapsed/too-large metadata to normalized values. It handles provider pagination/response-size behavior where supported. Changed-file list completeness is a separate three-state value: `complete` only when reliable provider/pagination evidence establishes completeness; `truncated` only when the provider or application has evidence that more entries exist than returned; and `unknown` when neither can be established. Never infer `complete` or `truncated` from missing provider attributes.

### Bounded response policy

Centralize limits in backend configuration/constants: maximum 100 changed-file records; maximum 256 KiB UTF-8 diff text per file; maximum 2 MiB cumulative UTF-8 diff text. Define `total_diff_bytes = sum(len(file.diff.encode("utf-8")))` over normalized textual `diff` fields actually included in the response. This budget excludes JSON syntax/serialization overhead, keys, commit metadata, paths, booleans, timestamps, and other metadata. Separately bound old/new changed-file paths and historical repository display paths to 4096 UTF-8 bytes each and repository name to 200 UTF-8 bytes, with explicit path-truncation flags. Persisted Finding metadata retains Feature 010 bounds (commit SHA ≤64 hex characters, author email ≤254 characters, author name ≤200 Unicode code points, message summary ≤500 Unicode code points). Preserve file entries in deterministic provider order and preserve bounded paths/type even when patch text is omitted or clipped. Enforce per-file limits first, then the cumulative diff-text budget. If the next patch exceeds the remaining cumulative budget, include only its UTF-8-safe prefix that fits, mark that file `diff_truncated`, then omit subsequent patch text and mark affected files `diff_truncated`; do not present clipped unified patches as complete. Count only bytes of returned `diff` strings. A too-large/collapsed provider file stays listed with no fabricated patch and its provider state. Do not add a second raw-payload size buffer beyond HTTP client's existing safe response limits; if the adapter needs one, define it centrally and fail safely rather than silently parse an unbounded body.

Binary files are not inferred from extension or fetched separately. A changed-file entry with absent/empty patch and no provider too-large/collapsed indicator gets normalized `text_diff_available=false` (binary/unavailable wording remains cautious because empty diff can also mean no textual patch). It does not fail other files. Preserve provider `collapsed` and `too_large` exactly as distinct states. Per-file patch state (`diff_truncated`, `collapsed`, `too_large`, `binary` when reliably supplied) is independent of `files_completeness`.

### Safe errors

Map domain errors to existing Problem Details conventions: `finding_not_found` (404), `finding_diff_not_applicable` (409), `gitlab_credential_missing` (safe unavailable response), `gitlab_instance_mismatch` (409), `commit_not_found` (404), `commit_diff_forbidden` (403), `commit_diff_timeout` (504), `commit_diff_unavailable` (502/503 per existing mapping), and `commit_diff_invalid_response` (502). Do not return raw provider text, HTTP bodies, exception text, DB details, authorization data, or stack traces. Failures leave Finding query/read behavior unchanged.

### Dashboard interaction

Add “View diff” to each applicable Unauthorized Commit Author row in the existing `ExecutionFindingsSection`. Keep existing Finding metadata visible. On activation, open an MUI dialog and fetch only that Finding's diff. Prevent duplicate in-flight request for that dialog; no list-prefetch, polling, or persistent cache. Retrying refetches the same finding. Keep the dialog open on normalized errors. Display commit fields at top, changed files as a keyboard-operable expansion list, and each selected file's unified patch in monospace line rows with textual `+`/`-` markers and accessible labels; context lines stay neutral. Long lines scroll horizontally, content scrolls within responsive dialog. MUI dialog focus behavior must be tested for enter/return and Escape/close. A file with no textual patch displays an explicit unavailable reason; app/provider truncation is visible.

### API and persistence

No schema or migration. Add response schemas and application query contracts only. Public response includes Finding ID, historical repository path, stored commit hash and persisted commit metadata where available, plus normalized `filesCompleteness` (`complete`, `truncated`, `unknown`) and `files` (`oldPath`, `newPath`, nullable `changeType`, `diff`, `textDiffAvailable`, `binary` when known, `collapsed`, `tooLarge`, `diffTruncated`, `oldPathTruncated`, `newPathTruncated`). Repository display name is at most 200 UTF-8 bytes; repository and changed-file paths are at most 4096 UTF-8 bytes and include truncation indicators. Existing Finding bounds cap commit hash, author email/name, and message summary. `filesCompleteness` is `complete` only with positive evidence of completeness, `truncated` only with evidence of omitted changed files, and otherwise `unknown`. `total_diff_bytes` counts only UTF-8 bytes of returned textual `diff` fields, not the serialized API body or metadata. No private snapshot fields, provider DTO, execution credential metadata or current configuration payload is returned.

## Project Structure

### Documentation

```text
specs/011-finding-commit-diff-details/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── finding-commit-diff-api.md
├── checklists/
│   ├── requirements.md
│   └── finding-commit-diff.md
└── tasks.md
```

### Source Code

```text
backend/app/application/
├── ports/gitlab_repository_client.py              # extend normalized diff operation
└── use_cases/get_finding_commit_diff.py
backend/app/domain/value_objects/
└── commit_diff.py                                  # normalized result, bounds/state semantics
backend/app/infrastructure/gitlab/
└── http_gitlab_repository_client.py                # provider mapping, pagination/limits
backend/app/api/v1/
├── finding_schemas.py                              # safe response DTO
└── findings.py                                     # GET diff route
backend/tests/
├── unit/application/test_get_finding_commit_diff.py
├── unit/infrastructure/test_gitlab_commit_diff.py
└── api/test_finding_commit_diff.py
src/features/executions/
├── api/findingsApi.ts                              # on-demand API client
├── types/findingDiff.ts
└── components/ExecutionFindingsSection.tsx        # action/dialog and per-file presentation
src/test/features/executions/
└── finding-commit-diff.test.tsx
```

Use the existing actual package and test conventions; do not create files for layers already adequately served by existing types/interfaces.

**Structure Decision**: Extend existing Finding API, GitLab repository port/adapter, and execution Findings UI. No new application project, persistence model, or dependency.

## Implementation Phases

1. **Normalized contracts and provider boundary**: normalized diff model, provider adapter mapping, bounds/truncation semantics, mocked adapter tests.
2. **Safe read API**: Finding-owned lookup, snapshot instance/credential checks, normalized errors and API/security tests.
3. **Dashboard interaction**: on-demand API client, accessible dialog, changed-file selection and line-oriented diffs; loading/error/retry and no eager-fetch tests.
4. **Cross-cutting validation**: diff-text budget boundaries, changed-file completeness states, provider flags, route wiring, focus behavior, narrow viewport and regression tests. No database migration is expected.

## Complexity Tracking

No constitution violations or new dependencies. The bounded normalized diff response and one read query extend existing architecture without introducing persistence or a parallel mining process.
