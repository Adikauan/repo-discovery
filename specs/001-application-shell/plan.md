# Implementation Plan: Application Shell

**Branch**: `001-application-shell` | **Date**: 2026-09-28 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-application-shell/spec.md`

## Summary

Establish a frontend-only React application foundation for the repository mining platform. The
implementation uses TypeScript, Vite, Material UI, and React Router to provide a centralized theme,
central route registry, responsive application shell, reusable layout and state primitives, and
eight structural destinations. Feature pages compose shared primitives but contain no GitLab,
mining, scheduling, persistence, authentication, or analytics behavior. The four supplied images
guide visual composition in the precedence order defined by the request; the constitution and
specification remain authoritative.

## Technical Context

**Language/Version**: TypeScript 5.x in strict mode; Node.js 26.x development runtime

**Primary Dependencies**: React, React DOM, Vite, Material UI, Material UI icons, Emotion, and
React Router; package-lock versions are pinned during implementation

**Storage**: N/A; no backend, browser persistence, remote data, or durable application state

**Testing**: Vitest, Testing Library for React, jest-dom matchers, user-event, jsdom, and an
axe-compatible accessibility test integration

**Target Platform**: Latest stable and previous major Chrome; latest stable and previous major
Microsoft Edge; latest stable Firefox; latest stable Safari. Browser-specific functionality
requires an appropriate fallback when needed.

**Project Type**: Single frontend web application

**Performance Goals**: Route transitions introduce no intentional blocking delays; navigation
interactions update synchronously from the user's perspective; placeholder pages introduce no
artificial loading delay. Formal frontend performance benchmarking and numeric performance targets
are outside Feature 001. No unnecessary feature payloads or chart libraries are introduced.

**Constraints**: WCAG 2.2 Level AA; frontend only; centralized routing and theme; no business
state machines; no external calls; no credential fields or storage; localized table overflow only;
visual references are subordinate to the constitution and specification; responsive acceptance is
validated at 375px, 768px, and 1440px without redefining Material UI breakpoints

**Scale/Scope**: Eight routes, four primary navigation items, four feature areas, one responsive
shell, and a focused set of shared layout, state, status, form, wizard, tree, and dashboard
presentation primitives

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

### Pre-Research Gate

| Principle | Plan evidence | Result |
|-----------|---------------|--------|
| Clean Architecture and boundaries | `app`, `shared`, and `features` own distinct responsibilities; features do not own routing infrastructure or theme policy. | PASS |
| Domain independence and rule ownership | This feature has no domain behavior. Presentation fixtures and view state cannot become business models or validation rules. | PASS |
| Explicit contracts | Route, navigation, component, state, and visual-reference contracts are documented under `contracts/`. No backend contract is invented. | PASS |
| Abstract external integrations | No GitLab or other external integration is included. | PASS |
| Secure construction | No credentials, tokens, browser persistence, authentication, or sensitive logging are included. | PASS |
| Historical execution integrity | No execution data is created or mutated; execution references are display-only placeholders. | PASS |
| Controlled execution pipeline | Mining execution is explicitly out of scope. | PASS |
| Observability | Only static execution-status presentation is planned; operational execution telemetry is deferred with execution processing. | PASS |
| Migration-managed persistence | No database or schema is introduced. | PASS |
| Automated verification | Tests cover shell, routes, active navigation, placeholders, wizard structure, responsive navigation, and accessibility. | PASS |
| Deliberate reusable UX | Shared patterns cover all required states and compositions; WCAG 2.2 AA and responsive behavior are acceptance gates. | PASS |
| Incremental simplicity and dependencies | Components are extracted only for immediate reuse; each dependency has a documented purpose in `research.md`. | PASS |
| Specification workflow | Work is limited to Feature 001 and must pass analysis before implementation and convergence afterward. | PASS |

No constitutional violation requires a complexity exception.

### Post-Design Gate

Phase 1 artifacts preserve the same boundaries: `data-model.md` defines presentation-only types;
the contracts specify public UI behavior without domain rules; `quickstart.md` validates every
route and shared state without external services. No new persistence, API, authentication, or
business behavior was introduced. **Result: PASS.**

## Project Structure

### Documentation (this feature)

```text
specs/001-application-shell/
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
|-- references/
|   |-- 1.png
|   |-- 2.png
|   |-- 3.png
|   `-- 4.png
|-- contracts/
|   |-- navigation.md
|   |-- ui-components.md
|   `-- visual-reference-map.md
`-- tasks.md                 # Created later by $speckit-tasks
```

### Source Code (repository root)

```text
src/
|-- app/
|   |-- layout/
|   |   |-- AppShell.tsx
|   |   |-- Sidebar.tsx
|   |   `-- MobileNavigation.tsx
|   |-- routes/
|   |   |-- routeConfig.tsx
|   |   |-- navigation.ts
|   |   `-- router.tsx
|   |-- theme/
|   |   |-- theme.ts
|   |   `-- tokens.ts
|   `-- App.tsx
|-- shared/
|   |-- components/
|   |   |-- dashboard/
|   |   |-- feedback/
|   |   |-- form/
|   |   |-- layout/
|   |   |-- listing/
|   |   |-- navigation/
|   |   |-- status/
|   |   |-- tree/
|   |   `-- wizard/
|   |-- hooks/
|   |   `-- useResponsiveNavigation.ts
|   |-- types/
|   |   `-- presentation.ts
|   `-- utils/
|       `-- displayText.ts
|-- features/
|   |-- home/
|   |   `-- pages/HomePage.tsx
|   |-- monitoring-configurations/
|   |   |-- components/
|   |   |-- fixtures/
|   |   `-- pages/
|   |       |-- MonitoringConfigurationsPage.tsx
|   |       |-- NewMonitoringConfigurationPage.tsx
|   |       |-- MonitoringConfigurationDetailsPage.tsx
|   |       `-- ConfigurationExecutionsPage.tsx
|   |-- executions/
|   |   |-- components/
|   |   |-- fixtures/
|   |   `-- pages/
|   |       |-- ExecutionsPage.tsx
|   |       `-- ExecutionDetailsPage.tsx
|   `-- settings/
|       `-- pages/SettingsPage.tsx
|-- test/
|   |-- accessibility/
|   |-- app/
|   |-- features/
|   |-- shared/
|   `-- setup.ts
|-- main.tsx
`-- vite-env.d.ts

index.html
package.json
tsconfig.json
vite.config.ts
```

**Structure Decision**: Use one Vite frontend at the repository root because Feature 001 contains
no backend and no second deployable unit. `app` owns composition, route registration, and global
theme. `shared` contains only primitives reused by at least two pages or explicitly required as a
future-stable visual contract. `features` owns page composition and isolated presentation fixtures.
Pages never declare routes, theme tokens, or shared business behavior.

## Routing Architecture

- Build a single route-object registry in `src/app/routes/routeConfig.tsx` and instantiate it in
  `router.tsx`; feature pages export presentation components only.
- Place all destinations beneath `AppShell` as a shared layout route. Use stable path constants and
  route metadata for titles, primary section ownership, and breadcrumb generation.
- Register `/`, `/monitoring-configurations`, `/monitoring-configurations/new`,
  `/monitoring-configurations/:id`, `/monitoring-configurations/:id/executions`, `/executions`,
  `/executions/:id`, and `/settings` exactly as specified.
- Treat this ordered set of eight paths as canonical across route metadata, automated tests,
  acceptance inspection, and documentation.
- Compute active primary navigation from route metadata/path matching so nested configuration and
  execution routes highlight their owning section consistently.
- Treat path parameters as untrusted display inputs: sanitize/format before rendering and show a
  neutral unavailable-reference placeholder for absent or invalid values. Do not fetch or validate
  them against business data.
- Keep the route hierarchy capable of nested feature children, but do not add unused guards,
  loaders, API layers, or authorization wrappers.

## Theme Architecture

- `tokens.ts` defines semantic color roles, typography scale, spacing choices, radii, border color,
  sidebar dimensions, and restrained elevations. Components consume semantic theme values rather
  than repeated literals.
- `theme.ts` constructs one Material UI theme and contains only global component overrides with
  broad value: focus visibility, button casing/radius, input shape, cards, table cells, alerts,
  tabs, and navigation surfaces.
- The palette follows the references: light cool-gray workspace, white surfaces, dark navy sidebar,
  saturated blue primary actions, neutral grays, and accessible semantic status colors.
- Status text/icons accompany color. Focus indicators and text/background pairs must satisfy WCAG
  2.2 AA. Theme checks include both default and interactive states.
- Responsive values use theme breakpoints; component-local layout choices remain beside the
  component when they are not system-wide tokens.

## Shared Component Boundaries

- Layout: `AppShell`, `Sidebar`, `MobileNavigation`, `PageContainer`, `PageHeader`, breadcrumbs,
  `ContentCard`, and `SectionHeader` own composition and semantics, not feature rules.
- Feedback: `LoadingState`, `EmptyState`, and `ErrorState` accept concise text and optional actions.
  Alerts/helper/validation messages rely on Material UI semantics with thin project conventions.
- Status: `StatusBadge` maps a presentation status to label, semantic tone, and optional icon. It
  supports active, disabled, paused, pending, running, completed, partially completed, and failed,
  without defining valid business transitions.
- Listing: reusable search/action/header/table composition handles spacing and overflow; column
  definitions and row actions remain feature-owned.
- Forms: reusable field group and form-action layout establish labels, required markers, helper
  text, validation placement, and responsive button ordering. No configuration validation is added.
- Wizard: a controlled `WizardShell` receives steps, current index, completion presentation, page
  content, and callbacks. The feature page owns only local visual-demo step state; there is no
  submission, persistence, GitLab connection, selection, or scheduling.
- Tree: lightweight `TreePanel`, `TreeNodeRow`, and `SelectedItemsPanel` may render static fixtures
  to validate indentation, expansion visuals, checkboxes, and responsive panel stacking. They do
  not implement recursive GitLab selection rules.
- Dashboard: `DashboardHeader`, `MetricCard`, `DashboardSection`, `ChartContainer`, and
  `DashboardGrid` arrange static placeholders. Charts are CSS/skeleton placeholders; no charting
  dependency or analytics calculation is introduced.

## Feature Boundaries

- `home` owns the landing placeholder.
- `monitoring-configurations` owns the list shell, new-configuration wizard composition,
  configuration details placeholder, related-executions placeholder, and any isolated visual
  fixtures used by those pages.
- `executions` owns the global list placeholder and execution dashboard shell plus isolated metric
  fixtures.
- `settings` owns the settings placeholder.
- Shared code cannot import from `features`. Features may import `shared` and route-link helpers,
  but not another feature's internal components or fixtures.
- No API client, repository, service layer, global feature store, domain entity, or backend folder is
  created in this feature.

## Responsive Strategy

- Desktop: persistent fixed-width sidebar, full labels, bounded readable content width, wide tables,
  two-column tree panels, and multi-column dashboard grids.
- Tablet: navigation switches to a temporary drawer when content would become constrained; spacing
  and grid columns reduce using shared breakpoints.
- Mobile: a labeled menu control exposes navigation in a focus-managed drawer; selecting a route
  closes it; forms and action groups become one column; tree panels and dashboard cards stack;
  tables scroll inside their own labeled region.
- Viewport changes close or reconcile temporary navigation state so the drawer cannot remain as an
  invisible focus trap. Layout testing covers 375px (narrow), 768px (medium), and 1440px (wide) as
  representative acceptance widths.
- Breakpoint values are centralized in the theme and finalized against actual content during
  implementation rather than copied mechanically from acceptance widths or desktop mockup
  dimensions; the three validation widths do not redefine Material UI breakpoints.

## Testing Strategy

- Use behavior-oriented component/integration tests with a memory router and user-event.
- Verify the shell renders once around every route; primary links navigate; direct entry works;
  active navigation is visible and exposed semantically; titles and breadcrumbs match route context.
- Verify successful routing to all eight canonical destinations and deterministic page orientation
  through title, active primary section, and breadcrumbs where required.
- Verify route changes contain no intentional timers or blocking delays and placeholder pages add no
  artificial loading delay; formal performance benchmarking is not part of this feature.
- Verify every placeholder destination renders and clearly identifies deferred functionality.
- Verify wizard current/completed states and next/back presentation without testing business
  validation or submission.
- Mock responsive media queries to verify persistent desktop navigation, accessible mobile menu,
  focus behavior, drawer closure after selection, and no loss of destinations at representative
  widths of 375px, 768px, and 1440px.
- Perform compatibility smoke validation against the documented Chrome, Edge, Firefox, and Safari
  support baseline; browser-specific functionality requires a suitable fallback where necessary.
- Run automated accessibility checks on the shell, shared states, listing shell, wizard shell, and
  dashboard shell; add manual keyboard, focus, contrast, zoom, and screen-reader smoke checks to the
  quickstart because automation alone cannot prove WCAG conformance.
- Avoid snapshot-heavy and internal-state tests. Assert user-visible roles, names, navigation
  outcomes, active state, and recovery actions.

## Visual Reference Use

- `1.png`: shell proportions, dark sidebar treatment, active navigation, light page container,
  page header, search/action row, table density, status chips, and compact row actions.
- `2.png`: back/title treatment, horizontal stepper, form rhythm, field/help/error placement,
  checkbox grouping, divider, and cancel/back/next action alignment.
- `3.png`: completed/current step visuals, bordered two-panel hierarchy composition, indented tree
  rows, selection summary, panel-local search, and responsive stacking inspiration only.
- `4.png`: breadcrumb/header/status arrangement, tab strip, metric cards, two-column sections,
  chart-placeholder containers, compact tables, and responsive dashboard grid hierarchy.
- Reference-only names, profile data, statuses, rows, GitLab paths, metrics, charts, and actions are
  not requirements. Fixture modules label any retained examples as non-production presentation data.

## Deferred Functionality

Backend services, databases, API contracts, GitLab connectivity, token handling, repository
discovery, recursive selection behavior, schedule creation, monitoring-configuration CRUD,
execution orchestration/history, findings, real charts/statistics, report download, authentication,
authorization, localization, and durable preferences remain out of scope. Their visual affordances
must be absent, disabled with truthful explanation, or explicitly labeled as previews.

## Technical Trade-offs

- Prefer Material UI composition and semantic theme overrides over a custom design-system layer;
  this reduces bespoke styling while preserving a stable project vocabulary.
- Keep presentation types local and shallow rather than introducing domain models before business
  behavior exists.
- Use local component state only for navigation drawer and wizard visual demonstration. A global
  state library is unjustified.
- Use static/CSS chart placeholders instead of a charting library because analytics are deferred.
- Keep route metadata centralized even though eight routes are small; it immediately prevents
  duplicated labels, active-state rules, titles, and breadcrumb semantics.
- Do not force pixel-perfect mobile reproduction of desktop references; accessible reflow and
  readable interaction take precedence.

## Complexity Tracking

No constitutional violations or justified exceptions.
