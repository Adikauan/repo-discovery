# Implementation Plan: Monitoring Configuration Final UX Adjustments

**Branch**: `016-monitoring-configuration-final-ux-adjustments` | **Date**: 2026-09-30 | **Spec**: [spec.md](spec.md)

**Input**: Feature 016 specification: list-level manual execution, sticky Selected Scope presentation, and return to the list after successful final save.

## Summary

Make three incremental frontend changes while reusing existing behavior: render the existing manual-execution action compactly in each configuration row; constrain a sticky Selected Scope panel to the desktop Scope grid; and navigate to `/monitoring-configurations` only after the existing final Scheduling save succeeds. No backend or persistence changes are planned.

## Technical Context

**Language/Version**: TypeScript, React (existing application)
**Primary Dependencies**: React Router, Material UI, existing execution/configuration API clients
**Storage**: Existing PostgreSQL-backed application data; no schema change
**Testing**: Vitest, React Testing Library, axe checks, existing frontend test suite
**Target Platform**: Desktop-oriented web application with narrower viewport support
**Project Type**: Full-stack web application; Feature 016 scope is frontend-only
**Performance Goals**: No additional API calls beyond the existing manual execution and schedule save operations
**Constraints**: Preserve manual execution eligibility, concurrency/idempotency, scope semantics, five-step wizard, and safe save/error handling; do not add persistence or endpoints
**Scale/Scope**: Three existing UI surfaces; no new domain entities or cross-feature redesign

## Constitution Check

- **I–IV, VI–X**: No domain, API, GitLab, execution-pipeline, persistence, migration, or history redesign. The row action calls the existing execution component/client and preserves server-owned lifecycle/concurrency behavior.
- **V Secure by Construction**: No credentials or secret handling is introduced or changed.
- **XI Deliberate, Reusable UX**: Reuse `ManualExecutionAction`, Material UI controls, existing safe feedback, and the existing wizard layout. Sticky behavior is responsive and does not create a new scroll trap.
- **XII Incremental Simplicity**: Limit edits to the configuration list action, Scope layout/summary, and final Scheduling save callback, with focused tests.

**Gate result**: PASS. No new endpoint, domain behavior, schema, persistence, dependency, or business rule is required.

## Architecture and Implementation Decisions

### Manual execution action

- Reuse `src/features/executions/components/ManualExecutionAction.tsx`, which already calls the existing `executionsApi.create(configurationId, idempotencyKey)`, prevents an in-flight duplicate, applies safe conflict/error feedback, and navigates to the created execution.
- Add a compact presentation mode using the existing Material UI icon system (`PlayArrow`/existing execution convention), `IconButton`, `Tooltip`, an accessible name tied to the row, focus styling, and pending disabled/`aria-busy` state. Preserve the current text-button presentation used on the details page.
- Render one instance in each row's Actions cell. Do not change server-side rules about disabled configurations or active-execution conflicts.

### Sticky Selected Scope

- In `GitLabScopePage`, retain the existing group/repository tree and selection summary as sibling columns on desktop.
- Set the desktop Grid row alignment and summary column alignment so the summary has intrinsic height and can stick relative to the long tree row; apply `position: sticky` with a modest top offset and a maximum height below the viewport, allowing the summary itself to scroll when it contains many selected entries.
- Disable sticky positioning and the summary's nested height/overflow constraints below the desktop breakpoint, where the columns stack. Preserve bottom padding from `MonitoringConfigurationWizardLayout` for the fixed wizard bar.
- Do not add scroll listeners, mutate selection data, or change scope persistence.

### Final save and redirect

- Keep `SchedulingPage` as the final wizard step and `ScheduleSection` as owner of schedule loading, draft, validation, stale-write handling, and `useMonitoringSchedule.save`.
- Add an optional success callback from `ScheduleSection` to `SchedulingPage`. Invoke it only after the existing save returns a persisted schedule. The page then routes to `/monitoring-configurations` with the existing list notice convention.
- Allow this intentional post-save navigation through the ScheduleSection dirty-route blocker after persistence succeeds. Validation/save failures keep the same step and draft; no redirect is performed. The list route's existing mount/load effect fetches the latest configuration list; no new cache abstraction is needed.
- Create and edit both use the same final Scheduling route and therefore the same redirect behavior. Intermediate saves remain unchanged.

## Project Structure

```text
src/features/executions/components/ManualExecutionAction.tsx
src/features/monitoring-configurations/
  pages/MonitoringConfigurationsPage.tsx
  pages/GitLabScopePage.tsx
  pages/SchedulingPage.tsx
  components/ScopeSelectionSummary.tsx
  components/ScheduleSection.tsx
src/test/features/monitoring-configurations/
  manual-execution list/action tests
  scope sticky layout tests
  final save redirect tests
```

**Structure Decision**: Incremental edits to the existing React application; no new frontend package, backend module, endpoint, or database object.

## Delivery Phases

1. Reuse the existing execution action in each list row with accessible compact presentation and duplicate-submit protection.
2. Make the Selected Scope column sticky on desktop while preserving stacked narrow layouts and bottom-bar clearance.
3. Connect successful final schedule persistence to a list redirect in create and edit flows; preserve failure and dirty-draft behavior.
4. Add focused component/interaction/accessibility regression tests, run the frontend suite, and build.
5. Perform manual visual validation when an application/browser surface is available; converge against Feature 016 requirements and existing Features 001–015 behavior.

## Test Strategy

- **Manual execution**: Assert each row has its own accessible icon action; activating a row calls the existing execution API with that row's ID; pending state prevents duplicate calls; existing success navigation, conflict feedback, and safe errors remain.
- **Scope**: Assert the Selected Scope container exists in the same layout as the GitLab tree, receives desktop sticky/max-height styling, becomes normal-flow when stacked, and does not remove the fixed bottom navigation. Use manual scrolling at desktop and narrow widths for visual confirmation.
- **Final save**: Exercise successful create/edit final schedule saves and verify route `/monitoring-configurations` plus list refresh/notice; reject schedule writes and verify no route change, alert shown, and draft retained. Retain existing validation and unsaved-navigation tests.
- **Regression/accessibility**: Run affected manual execution, scope, scheduling, wizard, and axe suites, then all frontend tests and production build. No backend tests are required because backend code/contracts do not change.

## Risks and Mitigations

- **Action accidentally uses the wrong row ID**: derive component identity directly from the row model and assert request URL in table-level tests.
- **Sticky box overlaps shell or bottom bar**: sticky only at desktop breakpoint, cap its available height, use a top offset, preserve wizard bottom padding, and validate the stacked layout.
- **Dirty blocker prevents redirect after save**: explicitly bypass the blocker only after the save response succeeds; test failed and successful save paths.
- **Disabled rows might be mistakenly disabled for manual runs**: retain eligibility behavior in the existing shared action; do not couple it to the status badge.

## Complexity Tracking

No constitution violations or complexity exceptions.
