# Quickstart: Execution Dashboard Validation

This guide describes validation scenarios for Feature 007. It does not prescribe implementation code. The feature adds no backend endpoint or migration.

## Prerequisites

- Use the repository's existing frontend and API setup from the README and `compose.yaml`.
- Have an execution retrievable from Feature 006, or use the existing test fixtures for deterministic UI states. Fixture values are test-only and must not enter production behavior.
- Configure the frontend API base URL using the existing application configuration.

## Automated frontend validation

From the repository root:

```powershell
npm run test:run -- src/test/features/executions
npm run test:run -- src/test/app/routes.test.tsx src/test/app/nestedRoutes.test.tsx src/test/features/responsiveLayouts.test.tsx
npm run build
```

Expected outcomes:

- Execution tests verify all five statuses, persisted values (including zero), historical snapshot scope, completion meaning, safe errors, loading/not-found/retry, honest unavailable sections, navigation context, tabs, keyboard behavior, and accessible names/states.
- Route and responsive tests confirm existing route reuse, global/configuration history navigation, and usability at representative viewport widths.
- The frontend build completes without type errors.

If the test runner's CLI differs in the checked-out version, run the matching project script with the same test files; do not add a new test runner.

## Manual end-to-end review

1. Open a real completed Feature 006 execution at `/executions/{id}`. Confirm the header prioritizes execution ID, historical configuration name, status, and trigger. Confirm Overview timestamps, API duration, historical GitLab URL and captured scope, and all four counters match the API response.
2. Confirm completion meaning is rendered from the response and states that orchestration completed without repository mining.
3. Open pending, running, partially completed, and failed detail fixtures in frontend tests; verify absent timestamps remain absent, status text is explicit, and only safe error fields appear.
4. Visit Repositories and Findings. Confirm their unavailable-detail explanations do not replace or misstate the persisted count cards and no fake data is present.
5. Open an execution from global history, then from configuration-specific history. Confirm each dashboard's return path matches its entry context. Open the route directly and confirm the global history fallback.
6. In frontend tests, pair an execution fixture with historical snapshot values and a current-configuration fixture with deliberately different name, GitLab URL, and group/repository scope. Confirm only snapshot values are presented and the dashboard needs no current-configuration request.
7. Select Repositories or Findings, trigger manual refresh, and confirm accessible loading, another detail request, updated response values, and the same selected tab. On refresh failure, confirm normalized error feedback. Confirm no current-configuration or GitLab request occurs and no polling is introduced.
8. Review a nonexistent ID and a normalized API failure. Confirm the not-found/error presentation, history/retry actions, and no raw backend details.
9. At 375px, 768px, and 1440px, inspect wrapping, metric stacking, tab operation, scope lists, and page-level overflow. Use keyboard-only navigation and existing axe-core tests.

## Contract and persistence scope

The Feature 006 execution detail API is unchanged. Do not run a migration or add backend tests for this feature unless implementation uncovers a genuinely missing safe persisted field; if so, update this plan/contract and add focused API security-contract tests before implementation continues.

