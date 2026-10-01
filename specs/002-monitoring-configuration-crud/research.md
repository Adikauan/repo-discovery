# Phase 0 Research: Monitoring Configuration CRUD

## Decision 1: Preserve Feature 001 and Add an Isolated Backend Package

**Decision**: Keep the frontend in its existing root-level `src/` tree and create a separate
`backend/` Python package with domain, application, infrastructure, and API boundaries.

**Rationale**: Feature 001 already supplies the Vite application shell and feature-oriented
structure. A separately packaged service introduces the requested backend without relocating or
redesigning the frontend. The layer separation keeps domain rules independent from HTTP and SQL.

**Alternatives considered**: A monorepo-wide workspace rewrite and putting Python modules beside
TypeScript source were rejected because they add migration/build complexity without a current need.

## Decision 2: Use Supported Python and PostgreSQL Baselines

**Decision**: Support Python 3.13 and 3.14, targeting Python 3.14.x for initial development. Target
PostgreSQL 16 or later and run the main integration suite against the baseline major.

**Rationale**: The official Python release list identifies 3.14 as the current feature series and
3.13 as a maintained series. PostgreSQL 16 through 18 are supported in the current release policy;
16 is a conservative production baseline with multiple supported majors available. Pin actual
dependency versions in the backend dependency lock when implementation begins.

**Alternatives considered**: A pre-release Python or PostgreSQL major was rejected for production
readiness; targeting only the newest PostgreSQL major would unnecessarily reduce deployment
compatibility.

**Sources**: [Python active releases](https://www.python.org/getit/), [PostgreSQL versioning
policy](https://www.postgresql.org/support/versioning/).

## Decision 3: Keep Domain Rules Independent and Server-Authoritative

**Decision**: Put configuration creation, normalization, URL validation, update/no-op semantics,
disabled-by-default behavior, and retirement in the framework-independent domain/application
boundary. Use Pydantic for HTTP shape validation and serialization; map domain errors to one API
error contract. Frontend native constraints are advisory and backend outcomes remain authoritative.

**Rationale**: This follows Clean Architecture and the constitution's single-rule ownership. FastAPI
response models produce documented, validated, filtered output, so SQLAlchemy rows do not become
public contracts. FastAPI dependencies can scope a database session to each request.

**Alternatives considered**: Keeping rules only in Pydantic or the route handler would make
non-HTTP application calls bypass them. Returning ORM rows directly couples public contracts to
storage and may expose fields unintentionally.

**Sources**: [FastAPI response models](https://fastapi.tiangolo.com/tutorial/response-model/),
[FastAPI dependencies with yield](https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/),
[Pydantic validators](https://docs.pydantic.dev/latest/concepts/validators/), [Pydantic URL types](https://docs.pydantic.dev/latest/api/networks/).

## Decision 4: Use Synchronous SQLAlchemy 2 Sessions and Application Transactions

**Decision**: Use SQLAlchemy 2 `Session` and statement APIs with one request-scoped session. Keep
commit/rollback in the application operation that coordinates domain changes and idempotency
receipts. Do not share a session between concurrent requests.

**Rationale**: This feature is bounded CRUD, so synchronous access keeps transaction behavior easy
to follow and test. The session represents mutable transaction state and explicitly controls
commit/rollback.

**Alternatives considered**: Async SQLAlchemy would add an async driver and transaction path without
a stated concurrent I/O target. Committing inside route handlers would make transaction behavior
transport-specific.

**Source**: [SQLAlchemy Session Basics](https://docs.sqlalchemy.org/en/20/orm/session_basics.html).

## Decision 5: Use Explicit Optimistic Concurrency for Updates

**Decision**: Assign each configuration an internal integer revision and expose it as an opaque
version/ETag. Require `If-Match` for updates; return `412 Precondition Failed` for a stale version
and `428 Precondition Required` when the precondition is missing. Map SQLAlchemy stale-row errors
into this contract.

**Rationale**: This implements the clarified reject-stale-edit rule without holding a database
transaction open while a user edits a form. SQLAlchemy's version counter compares the in-memory
revision to the row during flush. HTTP conditional requests are specifically designed to prevent
lost updates.

**Alternatives considered**: Last-write-wins contradicts the specification. Comparing timestamps
risks precision collisions. PostgreSQL `xmin` is database-specific and less explicit than a normal
version column.

**Sources**: [RFC 9110 If-Match](https://www.rfc-editor.org/rfc/rfc9110.html#section-13.1.1),
[SQLAlchemy version counters](https://docs.sqlalchemy.org/en/20/orm/versioning.html).

## Decision 6: Persist Create Idempotency Receipts Transactionally

**Decision**: The backend generates every Monitoring Configuration identifier; clients do not
provide a resource ID during creation. An optional `Idempotency-Key` can be supplied for retry
replay, but ordinary create requests do not require any client-provided identifier. When that
header is supplied, one database transaction stores its unique request key, normalized-request
fingerprint, generated configuration identifier, and original response snapshot with the new
configuration. Replay the original response for a same-key/same-payload retry; return conflict for
a same-key/different-payload reuse. A new key permits a distinct configuration with identical
values; requests without a key are separate create intents.

**Rationale**: For clients that opt into the key, the receipt uniqueness constraint arbitrates
simultaneous retry requests and remains available after process restart or a lost network response.
The receipt is implementation support for the explicitly accepted API behavior; requiring a client
key for every ordinary creation would confuse retry identity with the server-owned resource ID.

**Alternatives considered**: Value-based deduplication prevents legitimate identical configurations
and contradicts the specification. In-memory keys cannot guarantee atomic durable behavior. The
IETF `Idempotency-Key` header document is an Internet-Draft rather than a finalized RFC; its name is
used as a project contract convention, not claimed as an external conformance obligation.

**Sources**: [SQLAlchemy unique constraints](https://docs.sqlalchemy.org/en/20/core/constraints.html),
[Idempotency-Key draft status](https://datatracker.ietf.org/doc/html/draft-ietf-httpapi-idempotency-key-header-07),
[PostgreSQL uniqueness and conflict handling](https://www.postgresql.org/docs/current/sql-insert.html).

## Decision 7: Use Logical Retirement and Keep Future History Independent

**Decision**: Add nullable retirement metadata and retain all configuration values after deletion.
Normal list/get/update operations exclude retired records. No cascade deletion is configured. A
future history model must own the immutable execution-time snapshot it needs rather than depend on
the active configuration view.

**Rationale**: This provides user-facing removal while preserving the stable configuration
reference and current values for future execution-history relationships, as required by the spec
and constitution.

**Alternatives considered**: Physical deletion risks losing context or breaking future history
references. A restore workflow is not required in this feature.

## Decision 8: Store UUIDs and UTC-Aware Instants

**Decision**: Generate opaque UUID identifiers in the application, persist using SQLAlchemy's
portable UUID mapping, and persist creation, update, and retirement instants as timezone-aware
timestamps. API responses serialize ISO 8601 timestamps in UTC; display localization belongs to the
frontend.

**Rationale**: UUID is supported natively by PostgreSQL and SQLAlchemy provides a generic UUID type.
PostgreSQL stores timezone-aware timestamps internally in UTC. UTC instants avoid ambiguity across
developer, browser, and deployment time zones.

**Sources**: [SQLAlchemy UUID type](https://docs.sqlalchemy.org/en/20/core/type_basics.html),
[PostgreSQL UUID type](https://www.postgresql.org/docs/current/datatype-uuid.html),
[PostgreSQL date/time types](https://www.postgresql.org/docs/current/datatype-datetime.html).

## Decision 9: Keep Search Simple and Migration-Driven

**Decision**: Expose one optional `search` query parameter. Trim leading/trailing whitespace,
perform case-insensitive substring matching, treat empty/whitespace-only input as no filter, and
match wildcard-like characters literally. Use a parameterized query and escape SQL wildcard and
escape characters when using `LIKE`/`ILIKE`. Do not add pagination or specialized indexes
initially. Use version-controlled Alembic revisions and review autogenerated candidates manually.

**Rationale**: The spec requires simple name search and requests avoiding unjustified pagination.
Substring search does not benefit from an ordinary B-tree index; specialized extensions are
premature at the stated scope. Alembic documents that autogenerate is a candidate generator and
must be reviewed.

**Alternatives considered**: A separate search service, trigram extension, or full-text index adds
operational and migration cost without a scale requirement. Runtime table creation bypasses the
constitution's migration rule.

**Sources**: [PostgreSQL index types](https://www.postgresql.org/docs/current/indexes-types.html),
[Alembic autogenerate and limitations](https://alembic.sqlalchemy.org/en/latest/autogenerate.html).

## Dependency Justification

| Dependency | Immediate purpose | Why built-in capabilities are insufficient |
|---|---|---|
| FastAPI | HTTP routing, dependency injection, OpenAPI generation, response validation. | Python standard library does not provide the requested API service framework or API schema generation. |
| Pydantic 2 | Explicit API input/output schemas and validation serialization. | Hand-written request parsing/serialization would duplicate contracts and error handling. |
| SQLAlchemy 2 | PostgreSQL persistence and transaction management through a portable ORM/Core boundary. | Direct SQL in routes/use cases would couple persistence to business flow. |
| Alembic | Version-controlled schema migration lifecycle. | ORM metadata alone does not record or apply reviewed schema history. |
| Psycopg 3 | PostgreSQL DB-API driver. | Python has no built-in PostgreSQL driver. |
| pytest / HTTPX | Backend domain, application, integration, and API test execution. | Existing JavaScript test tools cannot execute Python backend behavior. |
| Existing Vitest / Testing Library | Frontend behavior tests and Feature 001 regression checks. | No new frontend test framework is needed. |

Backend package versions and lock data will be finalized during implementation after checking
compatibility with the selected Python baseline.
