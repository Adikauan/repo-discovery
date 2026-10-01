# Phase 0 Research: Application Shell

## Decision 1: Single Vite React Frontend

**Decision**: Create one root-level Vite application using React and strict TypeScript.

**Rationale**: The feature is explicitly frontend-only. One deployable unit is the simplest
structure and keeps build, test, and application composition together without inventing a backend
workspace.

**Alternatives considered**: A frontend subdirectory was rejected because no sibling backend or
monorepo unit exists. A multi-package workspace was rejected as premature abstraction.

## Decision 2: Central Route Registry with Layout Route

**Decision**: Declare route objects and metadata centrally, with all feature destinations nested
under an `AppShell` layout route.

**Rationale**: A route registry provides one source for paths, titles, primary section ownership,
and breadcrumb metadata. It supports future nested routes while keeping route declarations out of
feature presentation components.

**Alternatives considered**: Page-local route declarations duplicate navigation knowledge.
Hand-written pathname conditionals are brittle for parameterized and nested routes.

## Decision 3: Material UI Theme as the Token Boundary

**Decision**: Define semantic design tokens and broadly useful component overrides in one Material
UI theme; use theme-aware component styles for composition-specific rules.

**Rationale**: The required stack already supplies palette, typography, spacing, breakpoints, shape,
and component customization. Semantic roles prevent repeated literal colors and measurements.

**Alternatives considered**: A parallel custom token framework would duplicate Material UI.
Scattered inline values would undermine consistency and future redesign.

## Decision 4: Shared Only When Reuse Is Immediate

**Decision**: Put shell, page layout, states, status display, and explicitly required cross-feature
patterns in `shared`; keep page composition, columns, fixture shapes, and wording inside features.

**Rationale**: This applies the constitution's maintainability-over-abstraction rule. The requested
patterns already have multiple concrete consumers; feature details do not.

**Alternatives considered**: A universal component library was rejected as speculative. Keeping all
components feature-local would duplicate the visual foundation.

## Decision 5: Controlled Presentation-Only Wizard

**Decision**: Model the wizard as a controlled structural component with step descriptors, current
step, completed presentation, content, and visual navigation callbacks.

**Rationale**: It proves the four-step flow and reusable composition without owning validation,
submission, repository selection, GitLab access, or schedule persistence.

**Alternatives considered**: A form engine or state-machine dependency is unjustified. A static
image-like wizard would not validate keyboard interaction or future composition.

## Decision 6: Lightweight Tree and Dashboard Primitives

**Decision**: Implement only shallow presentational containers and optional isolated fixtures for
tree and dashboard layouts; use placeholder surfaces rather than real charts.

**Rationale**: The references are needed to validate future-ready spatial patterns, but their data
and behaviors belong to later features.

**Alternatives considered**: Recursive selection logic, a tree library, and a chart library were
rejected because they add complexity for excluded functionality.

## Decision 7: Responsive Drawer Below the Persistent-Sidebar Range

**Decision**: Use a persistent sidebar when space permits and a temporary, focus-managed navigation
drawer with a labeled menu button on constrained viewports.

**Rationale**: This retains access to all destinations, protects content width, and supports
keyboard and assistive-technology use.

**Alternatives considered**: Shrinking the full sidebar indefinitely harms content readability.
An icon-only rail obscures labels and is not the clearest mobile interaction.

## Decision 8: Behavior and Accessibility Testing

**Decision**: Use Vitest, Testing Library, user-event, DOM matchers, jsdom, and automated axe checks,
supplemented by manual WCAG verification in the quickstart.

**Rationale**: These tools test rendered semantics and user actions without binding tests to
component internals. Automated checks catch common violations; manual checks cover focus order,
reflow, contrast, zoom, and screen-reader behavior that automation cannot fully assess.

**Alternatives considered**: Snapshot-only tests give weak behavioral assurance. Full browser
end-to-end infrastructure is deferred until cross-page business workflows justify its cost.

## Dependency Justification

| Dependency | Immediate purpose | Why built-in capabilities are insufficient |
|------------|-------------------|--------------------------------------------|
| React / React DOM | Component composition and rendering | Required frontend stack and reusable view model |
| Vite | Development/build/test integration | Required stack; browser modules alone do not provide the project toolchain |
| TypeScript | Static contracts and strict presentation types | Required stack; JavaScript alone cannot enforce component contracts |
| Material UI / icons / Emotion | Accessible UI primitives, theme, icons, responsive styling | Required design system; rebuilding these controls increases accessibility risk |
| React Router | Central nested routing, params, links, active navigation | Required stack; manual history handling duplicates mature routing behavior |
| Vitest / jsdom | Fast component test runtime and DOM environment | Vite does not provide behavioral tests by itself |
| Testing Library / jest-dom / user-event | User-centered DOM queries and interactions | Low-level DOM calls encourage implementation-detail tests |
| Axe integration | Repeatable automated accessibility checks | Manual review alone is not repeatable enough for regression coverage |

All decisions are resolved; no `NEEDS CLARIFICATION` items remain.
