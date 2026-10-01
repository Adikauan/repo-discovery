# Research: Execution Dashboard

## Decision: Reuse the Feature 006 execution detail API as the sole dashboard data source

**Rationale**: The existing detail contract exposes all required dashboard data: execution identity and lifecycle, status and trigger, immutable safe configuration/scope snapshot, duration, persisted counters, nullable completion meaning, and bounded safe error fields. Its backend DTO is an explicit projection and the frontend execution type already represents these fields. `executionsApi.get(id)` is already available.

**Alternatives considered**: Add a dashboard-specific endpoint or read model; rejected because the existing detail DTO has all required information and a second model would duplicate persisted execution state. Extend the DTO; rejected because no required field is missing.

## Decision: Keep Feature 007 frontend-only

**Rationale**: The dashboard changes representation and navigation. Existing backend persistence, API route, detail use case, and safe projection already meet its read needs. There is no need for a migration, domain lifecycle change, API change, or backend test addition in this feature.

**Alternatives considered**: Add persistence or backend summary logic; rejected because no new execution facts are needed and this would increase scope without user value.

## Decision: Upgrade the existing `/executions/:id` page and reuse shared visual primitives

**Rationale**: Feature 001 established the route, shell, `PageHeader`, `ContentCard`, feedback patterns, `StatusBadge`, and `MetricCard`; Feature 006 implemented basic execution detail rendering at the route. Evolving that page preserves established navigation and visual conventions.

**Alternatives considered**: Add a second dashboard route or redesign the shell; rejected because the canonical route already exists and the feature explicitly reuses the shell.

## Decision: Render API duration and completion meaning without duplicating their logic or copy

**Rationale**: The API returns `durationSeconds` only when lifecycle instants permit a duration, and supplies the approved Feature 006 completion meaning for completed orchestration-only records. Reusing these values avoids divergent calculations and repeated hardcoded messaging. Running elapsed duration is omitted; no live timer is needed.

**Alternatives considered**: Add frontend duration calculations and a running timer; rejected because it duplicates existing API semantics and the live timer is outside the required behavior. Hardcode a separate completion message in components; rejected because the contract already owns that meaning.

## Decision: Use honest repository/findings states and metric cards; add no charting dependency

**Rationale**: Feature 007 has no repository-level processing or findings records and no meaningful chart dataset. Counters remain the persisted metrics; detail sections explicitly communicate unavailable records without replacing a real zero count.

**Alternatives considered**: Mock rows, generated findings, progress, or decorative charts; rejected because they would represent fabricated execution results and add unjustified dependencies.

## Decision: Preserve return context through internal route state with a global-history fallback

**Rationale**: Both global and configuration-specific history share `/executions/:id`. Route state allows the dashboard to return to the appropriate history without loading current configuration data. Direct entry and absent/invalid state use the global execution history route.

**Alternatives considered**: Depend only on browser back navigation; rejected because direct entry may have no useful prior history. Query current configuration to construct a return link; rejected because it adds a request and violates the snapshot/read-only boundary.

## Dependencies and research scope

No new external technology or dependency choice remains unresolved. The implementation uses the existing React, TypeScript, Material UI, React Router, Vitest, Testing Library, user-event, axe-core, FastAPI, Pydantic, and Feature 006 API contract. Project-specific design and contract evidence is documented in `plan.md` and `contracts/dashboard-ui.md`.
