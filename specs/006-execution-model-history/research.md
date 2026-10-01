# Feature 006 Research Decisions

## PostgreSQL active-execution concurrency

**Decision**: Use a short PostgreSQL repeatable-read transaction that captures configuration/scope from one consistent view and locks the owning configuration row with `SELECT ... FOR UPDATE NOWAIT`. Re-read active work after acquiring the lock. If it is not stale, return normalized HTTP 409; if stale (default threshold five minutes, configurable), transition it to failed through lifecycle logic and, for a distinct request, atomically persist the replacement snapshot and pending execution. Age is measured from `created_at` for pending or `started_at` for running, strictly greater than threshold. The application lifecycle then transitions the new record through running and, on success, completed before HTTP 201. Controlled failures use safe normalized metadata. The partial unique index for pending/running remains the durable invariant, and concurrent reconciliation/create attempts are serialized by the owner-row lock.

**Rationale**: The partial index is a durable invariant, not a convention each caller must remember. By itself, however, it does not ensure exactly one of two overlapping HTTP requests succeeds when the first request completes before the second insert resolves. The owning-row NOWAIT lock defines a deterministic request critical section without introducing a distributed lock service. PostgreSQL work is brief and performs no provider/repository calls. The active partial index remains a defense against writes that do not follow the use-case lock protocol.

**Alternatives considered**: Application check alone was rejected because concurrent requests race. A partial unique index alone was insufficient for the stronger overlapping-request outcome because its conflict can clear when the first row becomes terminal. Advisory locks or an application-level distributed lock were rejected as unnecessary. A test-only barrier after row-lock acquisition holds the first transaction while the second submits; this controls timing and does not simulate repository work.

**Operational caveat**: Feature 006 catches controlled orchestration failures and finalizes them as failed. A process crash after pending commits but before a final lifecycle transition can leave a visible active record until the next manual request arrives after the threshold and reconciles it; there is no background worker/recovery scheduler in scope. A database outage that prevents persisting a final failure cannot be converted into a durable failed record, and its API response remains generic and safe.

## Historical snapshot representation

**Decision**: Store an explicit `ExecutionSnapshotV1` as validated JSONB in the execution row. Serialize and validate through typed application/domain models. Capture configuration identity/name/enabled state, normalized GitLab URL, configuration revision, scope version if available, selected group/repository intent and safe metadata, trigger, and optional schedule context. Include the current internal instance fingerprint per scope selection to preserve instance identity, but never expose fingerprints in response DTOs.

**Rationale**: Execution snapshots are immutable, written once, and read as a coherent historical value. JSONB avoids duplicating mutable scope rows or creating snapshot tables for data that is not independently edited or queried. The schema version enables future evolution while typed validation prevents an arbitrary dictionary from becoming the historical contract. Projection DTOs prevent storage-only fields from leaking.

**Alternatives considered**: Foreign keys to current scope rows were rejected because selection edits or cascade deletion could rewrite/remove historical context. Fully normalized snapshot child tables were considered but add schema and migration complexity without a current query need. An untyped JSON/dict was rejected because it weakens validation and evolution guarantees.

## Scope and credential boundary

**Decision**: Read persisted scope intent from Feature 004 and copy its stable IDs, safe names/paths, parent IDs when available, origin identity, and scope version into the snapshot. Do not resolve groups or contact GitLab. Do not load credentials for snapshot creation.

**Rationale**: A selected group is a future dynamic scope rule; expanding it would change semantics and add provider work outside Feature 006. The credential is deliberately excluded from snapshot history and is not needed for a manual orchestration record.

**Alternatives considered**: Resolving current projects beneath selected groups was rejected because it performs discovery and turns a dynamic group rule into a static set. Capturing encrypted credentials or credential revision was rejected as both unnecessary and sensitive implementation coupling.

## Retention and configuration lifecycle

**Decision**: Keep a non-null FK from `mining_executions.monitoring_configuration_id` to the existing configuration with `ON DELETE RESTRICT` (or PostgreSQL's equivalent no-action behavior). Configuration retirement remains the established soft-retirement operation; it does not delete execution rows. Execution reads use the snapshot and remain available for retired configurations.

**Rationale**: Feature 002 retires configurations logically and keeps their identity. Restricting physical deletion protects the ownership link and history, while snapshots remain independent of mutable child rows which currently use cascade deletion.

**Alternatives considered**: `ON DELETE CASCADE` was rejected because it destroys history. A nullable FK was rejected because it weakens the invariant that each execution belongs to exactly one configuration. No new physical delete lifecycle is added.

## Idempotency for manual requests

**Decision**: Reuse the optional `Idempotency-Key` behavior already used by configuration creation. Fingerprint the operation and target configuration; persist the receipt with the initial execution creation. Store the execution identifier as the receipt result and reload the current execution on replay rather than treating a stale serialized status as authoritative. Same key/same operation returns the current execution if final; if active and non-stale it receives a safe conflict; if stale it is reconciled and the replay returns that same failed resource without creating a duplicate. A distinct key may create a replacement after reconciliation. A different fingerprint follows the existing idempotency conflict outcome.

**Rationale**: Constitution Principle VII explicitly requires idempotency where retries or repeated commands can occur. A manual request may complete quickly, so active-row uniqueness alone cannot prevent a client retry arriving after completion from creating a second history record. Idempotency remains optional for clients that do not supply a key; the owner-row lock and unique active index still prevent overlapping distinct requests.

**Alternatives considered**: No idempotency was rejected due to the existing project convention and uncertain-response duplicate risk. Making the key mandatory was rejected because existing APIs use an optional header and the execution endpoint has a separate database-backed active constraint.

## API pagination and frontend reuse

**Decision**: Follow existing API pagination vocabulary (`page`, `pageSize`) and use a bounded default/max page size for global and per-configuration execution lists. Apply filters in PostgreSQL and order by `created_at DESC, id DESC`. Replace the three existing execution placeholders and add the manual action to configuration details. Reuse current app shell, table, status, alert, loading, empty, and error patterns.

**Rationale**: Repository inspection found route placeholders and shared presentation primitives but no common table-pagination component. Backend bounded pagination avoids an unbounded global history payload; the UI can expose page controls locally in the feature without adding a new generic component absent demonstrated reuse.

**Alternatives considered**: Unbounded listing was rejected for uncontrolled history growth. Introducing a generalized pagination framework was rejected as unnecessary scope. Frontend-only filtering was rejected because the global history can grow and endpoint filters are part of the feature contract.

## Manual execution orchestration

**Decision**: The manual command commits pending/snapshot, transitions to running through the lifecycle service, performs no external/provider/repository work, and transitions to completed with zero counters. If the bounded orchestration path fails, transition to failed with a controlled code and safe summary; never echo internal errors.

**Rationale**: This is the clarified Feature 006 behavior and ensures active rows do not persist merely because mining is deferred. The lifecycle service remains reusable by Feature 008, which will add processing while running.

**Alternatives considered**: Leaving executions pending/running was rejected because it would create false stalled work. A fabricated mining result or `mining_unavailable` failure was rejected because the clarification says available Feature 006 orchestration succeeds and must not fake processing.
