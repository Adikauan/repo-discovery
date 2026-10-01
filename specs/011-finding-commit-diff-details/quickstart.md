# Quickstart: Finding Commit Diff Details

This is the validation guide for the planned Feature 011 implementation. Use mocked GitLab interactions in normal automated tests.

## Prerequisites

- Existing Feature 010 Finding with Unauthorized Commit Author rule identity, stored commit SHA and owning RepositoryExecution.
- Parent MiningExecution has a historical GitLab instance snapshot; a matching secure connection is configured for success-path provider requests.
- Backend and frontend test dependencies from the repository are installed.

## Scenarios

1. Open an execution dashboard with a persisted unauthorized-author Finding. Confirm loading the Findings tab makes no diff request.
2. Activate **View diff**. Confirm one request to `GET /api/v1/findings/{finding_id}/diff`, no caller-selected provider identifiers, and metadata matches the Finding's stored commit.
3. Return a changed-file response with add/modify/delete/rename types. Select files and verify line-oriented `+`, `-`, and context rendering.
4. Return binary/no-text, `collapsed`, `too_large`, provider-truncated, and application-clipped responses. Validate textual diff budgets below, exactly at, and above the cap; confirm paths and commit metadata do not consume that budget, UTF-8 is counted by bytes, and clipping follows provider order.
5. Exercise `filesCompleteness` as `complete`, `truncated`, and `unknown`. Confirm missing provider evidence remains `unknown`, with no warning for `complete`, a factual omitted-files warning for `truncated`, and a calm uncertainty note for `unknown`.
6. Return credential missing, instance mismatch, not found, forbidden, timeout, malformed, and unavailable errors. Confirm normalized feedback, Finding remains visible, and retry is available.
7. Use keyboard to open, navigate file entries, expand/select a diff, close with Escape, and confirm focus returns to the triggering button. Repeat at a narrow viewport.

## Validation commands

Run the repository's existing backend test command targeting `backend/tests/unit/infrastructure/test_gitlab_commit_diff.py`, `backend/tests/unit/application/test_get_finding_commit_diff.py`, and `backend/tests/api/test_finding_commit_diff.py`; run frontend tests targeting `src/test/features/executions/finding-commit-diff.test.tsx`; then run the full relevant frontend suite/build. No migration is expected.

See [API contract](contracts/finding-commit-diff-api.md), [data model](data-model.md), and [research](research.md).
