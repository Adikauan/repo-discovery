# Research: Mining Findings

## Decision: extend the existing configuration and execution snapshot

**Decision**: Store a normalized allowed-author email list on Monitoring Configuration; include a frozen copy in every newly captured execution snapshot. Keep that list out of public snapshot DTOs unless a separately approved product requirement is added.

**Rationale**: Manual and scheduled execution creation already share `CreateMiningExecution` and `ExecutionSnapshotV1.capture`, so one capture change preserves pipeline parity and historical immutability. An empty list has the explicit spec meaning: any valid commit author is unauthorized. Backward-compatible configuration reads treat missing persisted values as an empty list.

**Alternatives considered**: querying current configuration during mining (rejected because it rewrites history); duplicating the allowlist on RepositoryExecution (rejected as unnecessary ownership duplication); exposing it in public execution reads (not required and increases disclosure).

## Decision: normalized rule output, persisted by application orchestration

**Decision**: Extend the Feature 008 `MiningRule` result contract with normalized Finding candidates; domain rules remain pure and return values. `ProcessRepository` coordinates GitLab retrieval/rules and the repository unit of work persists the candidates.

**Rationale**: This keeps persistence and provider concerns outside business rules, preserves RepositorySummaryRule, and reuses the same manual/scheduled Feature 008 pipeline.

**Alternatives considered**: rule writes directly to SQLAlchemy (rejected by Clean Architecture); separate finding pipeline (rejected because it duplicates execution behavior); generic untyped JSON output (rejected because the initial result fields are stable and explicit).

## Decision: GitLab API for commit history, no clone/archive

**Decision**: Extend the existing GitLab repository client with normalized methods for current HEAD and commit metadata ranges. Use the Commits API's `ref_name` revision-range support (`<checkpoint>..<head>`) with complete pagination and a limit+1 guard. Use commit-reference information to verify the checkpoint is still on the selected branch. Avoid `since`/`until` timestamps for range correctness, and do not clone or fetch file contents for this rule.

**Rationale**: The commit list API provides author email/name, authored date, SHA, message, and parent SHAs. It accepts branch/tag/revision-range `ref_name`. Pagination defaults to 20 and permits up to 100 per page; commit responses omit total-count headers, so the client must follow the continuation/link information or validated page exhaustion. GitLab's commit refs API lists branch/tag refs that contain a commit, which can be used to distinguish a reachable checkpoint from a rewritten branch. Provider DTOs remain in the adapter.

**Alternatives considered**:

- **Shallow/full clone**: rejected; unnecessary for author metadata and adds local storage/process lifecycle.
- **Archive/tree/file APIs**: rejected; they do not provide the required incremental commit author range.
- **Timestamp-only `since`/`until`**: rejected; timestamps are not stable commit identity boundaries and can omit commits with skewed/rewritten timestamps.
- **Compare API**: possible for commit comparisons but not selected as the primary read path because paginated commit-list semantics plus the explicit configured cap better align with this feature's bounded range contract.

Primary sources: [GitLab Commits API](https://docs.gitlab.com/api/commits/) and [GitLab REST API pagination](https://docs.gitlab.com/api/rest/).

## Decision: baseline on first successful repository processing

**Decision**: If the configuration/project/branch checkpoint is absent, capture the branch HEAD and write it only in the successful repository result transaction. Do not enumerate commits before that baseline and do not produce historical findings on the first run.

**Rationale**: This is the deterministic product behavior stated by FR-009 and avoids surprise alerts from preexisting repository history.

**Alternatives considered**: scan full history at first run (rejected as unbounded and contrary to baseline requirement); persist baseline before repository completion (rejected because failures must not advance checkpoint).

## Decision: one checkpoint identity per configuration, stable project and branch

**Decision**: Uniqueness key is `(monitoring_configuration_id, gitlab_project_id, branch)`. Persist only last successful SHA and `updated_at`. Use a database uniqueness constraint and transactional update/upsert. A different Monitoring Configuration gets an independent baseline even for the same project.

**Rationale**: This is the smallest durable state that supports incremental reads while preventing one configuration's allowlist/policy cadence from affecting another.

**Alternatives considered**: keying on path/name (rejected as mutable); one checkpoint shared across configurations (rejected because policies and execution cadence differ); checkpoint per execution (rejected because incremental state must persist across executions).

## Decision: atomic finding, repository result, counter, and checkpoint commit

**Decision**: Complete GitLab I/O and pure rule evaluation before opening the final short write transaction. In that transaction, insert findings, set RepositoryExecution findings count and successful terminal state, and advance checkpoint. On failure, roll back the result transaction and mark RepositoryExecution failed in a separate short transaction. Execution counters continue to be aggregated from persisted repository rows by Feature 008.

**Rationale**: No long database transaction spans provider I/O, and a checkpoint cannot pass findings that failed to persist.

**Alternatives considered**: checkpoint before findings (rejected because detections could be lost); findings in separately committed batches (rejected because it could leave partial findings while retaining an old checkpoint); transaction around remote calls (rejected due to long-held locks).

## Decision: bounded overflow fails without truncation

**Decision**: `MINING_MAX_COMMITS_PER_REPOSITORY_EXECUTION` defaults to 1,000 and accepts 1–10,000. Fetch at most limit+1 unique commits. If overflow occurs, fail with `commit_range_limit_exceeded`, persist no findings from the rejected range, and leave checkpoint unchanged. Never silently truncate and advance.

**Rationale**: The number of commits processed is objectively bounded while the explicit failure avoids permanently skipping the unprocessed tail.

**Alternatives considered**: process first N and move baseline to HEAD (rejected because it loses findings); queue remainder (rejected as unapproved scheduler/backlog behavior); unlimited retrieval (rejected as unbounded).

## Decision: finding shape and idempotency

**Decision**: Persist an explicit immutable Finding associated only to RepositoryExecution. For Unauthorized Commit Author use rule id `unauthorized-commit-author`, version `1`, severity `warning`, commit SHA, normalized valid email or null plus `missing`/`malformed` state, authored timestamp when valid, optional sanitized author name, bounded safe summary, and bounded message summary. Use unique key `(repository_execution_id, rule_id, rule_version, commit_hash)`.

**Rationale**: These fields explain the deterministic detection without storing raw provider response payloads. RepositoryExecution supplies MiningExecution ownership. The unique key makes repeated persistence attempts for the same rule/commit/repository execution idempotent.

**Alternatives considered**: a mutable issue/triage state (rejected; historical detection only); duplicate MiningExecution FK on every finding (rejected absent measured query need); raw commit/provider JSON blob (rejected as sensitive, unbounded, and unstable).

## Decision: safe malformed identity and summary handling

**Decision**: Trim/case-fold configured allowlist emails and provider author email for comparison. Validate configured values at the configuration boundary; deduplicate normalized addresses. For missing or malformed provider email, store no raw malformed input, store null email and an explicit safe identity state, and create one finding per affected commit. Never infer identity from the author name. Strip control characters and bound message summary to 500 Unicode code points.

**Rationale**: This gives deterministic comparison and useful explanation without retaining malformed identity text or large provider payloads.

**Alternatives considered**: reject the whole repository on one bad author field (rejected because the approved clarification specifies a finding); store malformed raw email (rejected for safe historical data); match names (rejected because names are non-unique and explicitly excluded).

## Configuration bound assumption

**Decision**: Limit the allowed-author list to 500 entries, each at most 254 characters, and validate as an email before normalization; persistence snapshots contain the sorted normalized set. This is a conservative resource bound for request and snapshot size, not a user-management feature.

**Rationale**: The specification requires a list but gives no cardinality bound. A finite limit protects API, revision receipt, and JSONB snapshot sizes while remaining far above typical configuration lists.

**Review note**: Confirm this product-level maximum before implementation. It is an explicit planning assumption and can be adjusted during analysis without changing the mining model.

## Decision: severity and empty policy

**Decision**: All Unauthorized Commit Author findings use `warning`; empty allowed list means every valid author email is unauthorized. Missing/malformed author emails produce a `warning` finding per commit but never expose invalid raw values.

**Rationale**: This directly records the clarification outcomes in a stable contract.

## Decision: one narrowly scoped email validation dependency

**Decision**: Add `email-validator` to the backend dependency set for configured email syntax validation and provider author identity classification; call validation without DNS deliverability lookup. Reuse all other existing Python, FastAPI, SQLAlchemy, Alembic, Pydantic, PostgreSQL, React/TypeScript/Vite/Material UI, test, API error, and accessibility capabilities. Add no charting or state-management dependency.

**Rationale**: The same email syntax decision is required at configuration save and commit evaluation. Hand-written regular expressions or ad hoc parsing risk different accepted values across those paths; deliverability checks would add network behavior and nondeterminism that are not required. The package is justified for this precise boundary and runs syntax-only. Use the maintained 2.x line (`email-validator>=2.3,<3`) and pin through the backend dependency workflow. Its published documentation confirms syntax validation can run with DNS deliverability checks disabled ([PyPI project documentation](https://pypi.org/project/email-validator/)).
