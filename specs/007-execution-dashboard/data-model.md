# Data Model: Execution Dashboard

Feature 007 introduces no persisted or domain entity. The dashboard is a presentation of the existing Feature 006 `ExecutionDetail` response. It must not create a second execution model or mutate execution history.

## Input: Mining Execution detail

The existing `GET /api/v1/executions/{executionId}` response, represented by `ExecutionDetail` in `src/features/executions/types/execution.ts`, is the authoritative input.

| Field | Source | Presentation rule |
|---|---|---|
| `id` | Persisted execution | Show as execution identifier; allow wrapping. |
| `monitoringConfigurationId` | Execution relationship | Use only for configuration-history navigation fallback/context if needed; do not fetch current configuration. |
| `status` | Persisted lifecycle | Support `pending`, `running`, `completed`, `partially_completed`, `failed`; show text and shared icon/status badge. |
| `triggerType` | Persisted execution | Show Manual or Scheduled. |
| `createdAt`, `startedAt`, `completedAt` | Persisted lifecycle instants | Format for display; absent optional values remain visibly absent. |
| `durationSeconds` | Feature 006 detail projection | Use only when non-null; do not persist or recompute. Current Feature 006 running records do not receive an elapsed timer. |
| `snapshot.configurationName` | Immutable safe snapshot | Label as historical configuration context. |
| `snapshot.gitlabUrl` | Immutable safe snapshot | Display as captured URL, wrap safely. |
| `snapshot.scope.groups[]` | Immutable safe selected group intent | Keep group selections separate from repositories; display safe name/full path. Empty means no groups selected. |
| `snapshot.scope.repositories[]` | Immutable safe selected repository intent | Display safe name/full path. Empty means no repositories selected. |
| `counters.repositoryCount` | Persisted MiningExecution counter | Show numeric value including zero. |
| `counters.successfulRepositoryCount` | Persisted MiningExecution counter | Show numeric value including zero. |
| `counters.failedRepositoryCount` | Persisted MiningExecution counter | Show numeric value including zero. |
| `counters.findingCount` | Persisted MiningExecution counter | Show numeric value including zero. |
| `completionMeaning` | Safe Feature 006 API projection | Render only when non-null/non-empty; API is source of text. |
| `error.code`, `error.summary` | Safe normalized execution metadata | Render only when error object exists; expose no raw/internal error details. |

## Relationships and lifecycle

The Mining Execution belongs to one Monitoring Configuration and contains an immutable Execution Snapshot. Feature 007 reads these through the execution detail contract. Existing status values and transitions remain owned by Feature 006; the dashboard does not change or infer them.

## View-only states

These are presentation states, not persisted entities:

- **Loading**: request is pending; announce progress accessibly.
- **Loaded**: one `ExecutionDetail` is available and all visible facts are sourced from it.
- **Not found**: normalized 404; offer global execution history navigation.
- **Retrieval error**: normalized safe failure; offer retry.
- **Repository detail unavailable**: repository processing records do not exist in Feature 007; do not confuse with `repositoryCount: 0`.
- **Finding detail unavailable**: finding records do not exist in Feature 007; do not confuse with `findingCount: 0`.

No fixtures or fabricated values may be used by production dashboard behavior.

## Data excluded from presentation

Do not expose raw snapshot JSON/schema version, GitLab instance fingerprint, credential revision/value, authorization headers, provider response bodies, stack traces, raw exceptions, database errors, or internal concurrency/idempotency metadata. These are absent from the public detail projection or explicitly prohibited by the Feature 006 contract.
