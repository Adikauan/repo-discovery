# Phase 1 Data Model: Application Shell

This feature has no persisted domain data. The models below are immutable presentation contracts
used to keep routing and shared components consistent. They MUST NOT become substitutes for future
Monitoring Configuration or Execution domain entities.

## NavigationItem

| Field | Meaning | Validation |
|-------|---------|------------|
| `id` | Stable presentation identifier | Unique among primary navigation items |
| `label` | Canonical user-facing term | One of Home, Monitoring Configurations, Executions, Settings |
| `path` | Primary destination | Must reference a registered internal route |
| `icon` | Decorative/semantic icon reference | Accessible name comes from label, not icon alone |
| `matchPaths` | Routes owned by this section | Must include the primary path and relevant nested paths |

Relationship: many route destinations may map to one primary navigation item.

## RouteDescriptor

| Field | Meaning | Validation |
|-------|---------|------------|
| `id` | Stable route identifier | Unique across the registry |
| `path` | Route pattern | Must match one of the eight specified destinations |
| `title` | Page title or title resolver | Must produce a unique, descriptive title |
| `primarySection` | Active navigation owner | Must reference a `NavigationItem` |
| `breadcrumbs` | Ordered parent/current descriptors | Parent destinations must be registered routes |
| `page` | Feature page reference | Must render inside `AppShell` |

## BreadcrumbItem

| Field | Meaning | Validation |
|-------|---------|------------|
| `label` | Visible hierarchy label | Concise and consistent with canonical terminology |
| `path` | Optional parent destination | Present for navigable parents; absent for current item |
| `current` | Current-page indicator | Exactly one current item per breadcrumb trail |

## PageStateDescriptor

| Field | Meaning | Validation |
|-------|---------|------------|
| `kind` | Presentation condition | `loading`, `empty`, `error`, `disabled`, `success`, or `placeholder` |
| `title` | Short state summary | Required except for minimal loading variants |
| `message` | User-oriented explanation | Must be truthful and must not imply deferred behavior works |
| `action` | Optional next/recovery action | Must be meaningful and keyboard accessible |
| `liveMode` | Announcement behavior | Applied only when a dynamic state requires announcement |

State transitions are owned by consuming features. Shared state components only render the current
descriptor and define no workflow.

## PresentationStatus

Allowed values: `active`, `disabled`, `paused`, `pending`, `running`, `completed`,
`partially-completed`, `failed`.

Each status maps to one canonical label, semantic tone, and optional icon. The mapping does not
define legal business transitions. Status is always communicated with text, not color alone.

## WizardStepDescriptor

| Field | Meaning | Validation |
|-------|---------|------------|
| `id` | Stable step identifier | Unique within a wizard |
| `label` | Visible step name | Required and meaningful out of context |
| `description` | Optional supporting text | Must not claim deferred behavior is available |
| `state` | Visual progress | `upcoming`, `current`, or `completed` |

The shell demo uses General information, GitLab connection, Repository selection, and Scheduling.
Only current/completed visual state changes; no submitted configuration is produced.

## Presentation Fixtures

Listing rows, profile details, selected hierarchy items, metrics, chart shapes, and table results may
exist only in `features/*/fixtures`. Every fixture module is labeled non-production and is imported
only by its owning feature. Fixtures have no persistence, service, or cross-feature identity.
