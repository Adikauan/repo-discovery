# Phase 1 Quickstart: Validate the Application Shell

## Prerequisites

- Node.js 26.x and npm available.
- Feature 001 implementation completed from the approved tasks.
- No backend, database, GitLab credentials, or external service is required.

## Setup and Run

```powershell
npm install
npm run dev
```

Open the local URL reported by Vite. The initial page must render the application shell without
network credentials or backend configuration.

## Automated Validation

```powershell
npm test -- --run
npm run build
```

Expected outcomes:

- Shell, route, navigation, placeholder, wizard, responsive-navigation, and accessibility tests pass.
- Production compilation and bundling complete without TypeScript errors.
- Tests make no GitLab or backend calls and do not depend on fixture persistence.
- Automated route coverage reaches all eight canonical destinations and validates page title,
  active primary section, and required breadcrumbs.
- Route transitions contain no intentional blocking timers and placeholders contain no artificial
  loading delays; formal performance benchmarking is outside Feature 001.

## Route Walkthrough

Open each route directly and through in-app navigation, substituting harmless display identifiers
for `:id`:

- `/`
- `/monitoring-configurations`
- `/monitoring-configurations/new`
- `/monitoring-configurations/demo`
- `/monitoring-configurations/demo/executions`
- `/executions`
- `/executions/demo`
- `/settings`

For every route verify the title, active primary section, shell consistency, and breadcrumb behavior
defined in [navigation.md](./contracts/navigation.md). Verify that all unfinished destinations are
truthful placeholders and that refreshing a nested route preserves its context.

## Visual Review

Compare the implementation with [visual-reference-map.md](./contracts/visual-reference-map.md) and
the four reference images at 375px (narrow), 768px (medium), and 1440px (wide). These are
representative acceptance widths and do not redefine Material UI breakpoints.

- Wide: persistent dark sidebar, full labels, light workspace, wide listing/table, two-panel tree,
  and multi-column dashboard composition.
- Medium: reduced gutters and adaptive grids without overlap.
- Narrow: accessible navigation drawer, single-column forms, stacked cards/panels, and localized
  table scrolling with no page-level horizontal overflow.
- Confirm that all sample content is visibly demonstrative and isolated from application behavior.

## Browser Compatibility

Perform a smoke review using the latest stable and previous major Chrome, latest stable and previous
major Microsoft Edge, latest stable Firefox, and latest stable Safari. Record the versions and
outcomes here during implementation validation. Any required browser-specific functionality must
have an appropriate fallback.

## State and Component Review

Render or navigate to demonstrations of Loading, Empty, Error, Disabled, Success, and Placeholder
states. Confirm each is distinct, understandable without color, and offers an appropriate action
only when that action truly works. Review component boundaries against
[ui-components.md](./contracts/ui-components.md).

## WCAG 2.2 Level AA Review

- Navigate every destination and interactive demo using only the keyboard.
- Verify logical focus order, visible focus, drawer focus containment/restoration, and no keyboard
  traps.
- At 200% zoom and narrow reflow, confirm controls and content remain usable.
- Confirm text, controls, focus indicators, statuses, and errors meet required contrast and do not
  rely on color alone.
- Confirm headings, landmarks, navigation labels, breadcrumbs, tables, forms, alerts, and status
  announcements expose meaningful semantics in a screen reader smoke test.
- Run the automated accessibility suite and resolve all critical violations; record any manual
  exceptions with evidence before acceptance.

## Scope Guard

Inspect browser network and storage tools during the walkthrough. There must be no GitLab/backend
requests, token handling, authentication state, persisted configurations/executions, real charts,
or stored fixture data. Any control suggesting deferred behavior must be absent, explicitly a
preview, or disabled with truthful explanatory text.

## Feature 001 Validation Record

Validated on 2026-09-28:

- `npm test -- --run --passWithNoTests`: PASS — 15 files, 44 tests.
- Automated axe review: PASS — four representative route compositions, no critical findings.
- `npm run build`: PASS — strict TypeScript and production bundle completed.
- Canonical routes: PASS — all eight routes are registered and covered by route tests.
- Representative widths: PASS — navigation and primary compositions covered at 375px, 768px, and
  1440px by responsive tests.
- Scope audit: PASS — no network calls, browser persistence, credentials, timers, backend, GitLab,
  authentication, mining, scheduling, CRUD, execution processing, or real analytics were found.
- Visual-reference review: PASS — dark navigation, light workspace, listing, wizard/tree, and
  dashboard composition follow the reference map; sample content remains isolated fixtures.
- Keyboard/focus review: PASS for automated navigation, active-state, drawer, and control semantics.
- Manual screen-reader smoke: not executable in the current non-screen-reader environment; the
  semantic and automated accessibility coverage remains passing.
- Browser smoke matrix: Chromium-compatible build/test validation passed. Direct Firefox, Safari,
  and previous-major browser sessions were unavailable in the current environment and remain a
  non-blocking external validation item; no browser-specific application APIs are used.
- Build note: the production build reports one non-blocking 631.44 kB chunk-size advisory. Feature
  001 intentionally keeps one simple route bundle; route-level code splitting may be introduced when
  later features add substantive payloads.

### Convergence validation update

- `npm test -- --run --passWithNoTests`: PASS - 16 files, 69 tests.
- `npm run build`: PASS - strict TypeScript and production bundling completed; the existing
  non-blocking single-chunk size advisory remains.
- Automated accessibility: PASS for all eight canonical destinations with no critical axe
  findings. Because jsdom does not calculate painted colors, deterministic WCAG contrast tests
  separately cover workspace/sidebar text, controls, semantic statuses, focus indicators, and
  borders against their themed backgrounds.
- Manual screen-reader smoke: not executable in the current non-screen-reader environment. The
  route-wide semantic and automated accessibility coverage passes, but this manual acceptance item
  must be completed in an environment with a screen reader before SC-005 can be closed.
- Browser inventory: Chrome 154.0.8037.57 and Edge 154.0.4258.37 are installed. The available
  browser automation provider exposed no sessions, and direct headless smoke could not attach to
  the local application. Firefox, Safari, and previous-major Chrome/Edge are not installed. The
  full FR-018 matrix remains an external validation item; the source audit found no browser-specific
  application APIs and `browserslist` encodes the required support baseline.
