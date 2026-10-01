# Quickstart: Feature 016

## Prerequisites

- Use the existing development setup documented by the repository.
- Have at least one Monitoring Configuration available for list-action validation.
- For scope layout validation, use a configuration with enough GitLab groups/repositories to make the tree taller than the viewport.

## Automated validation

From the frontend project root:

```powershell
npm run test:run -- <affected Feature 016 test files>
npm run test:run
npm run build
```

No backend or migration validation is required because Feature 016 changes no backend contract or persistence.

### Executed results

- Targeted Feature 016, schedule lifecycle, and regression tests: 10 tests passed across 4 files.
- Full frontend suite: 215 tests passed across 53 files.
- Production build: passed (`tsc -b` and Vite build). Vite reported the existing large-chunk advisory.
- Vitest ran with the temporary workspace config, single thread, and `--isolate=false` because the default configuration could not start child processes in this environment. The temporary config is not a project change.
- Accessibility checks were included in the full frontend suite; all passed.

## Manual scenarios

1. From Monitoring Configurations, activate the manual-execution icon for a row. Verify it opens the resulting execution for that row and the action prevents repeat submission while pending. Trigger a server conflict/failure where available and confirm safe feedback.
2. Open Scope for a configuration with a large GitLab hierarchy. Scroll the tree at a desktop width and verify Selected Scope remains visible below the page/stepper area and above the fixed bottom bar. Resize to a narrow width and verify Selected Scope returns to normal flow without clipping selected paths.
3. In create and edit wizard flows, complete the final schedule save. Confirm successful persistence returns to `/monitoring-configurations` and the list shows fresh data. Force a save failure and confirm the current Scheduling step, error, and draft remain.

Manual visual validation remains pending because no browser or app surface was available in the validation session. Do not mark it complete until these scenarios are inspected in a running application.
