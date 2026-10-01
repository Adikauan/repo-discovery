# Research: Monitoring Configuration Final UX Adjustments

## Existing behavior inspected

### Manual execution

- `ManualExecutionAction` in `src/features/executions/components/ManualExecutionAction.tsx` already calls `executionsApi.create` with the configuration ID and idempotency key, guards in-flight repeat activation, displays safe conflict/error states, and navigates to the created execution on success.
- It is currently rendered in the Monitoring Configuration details view as a text action; no new endpoint or pipeline is necessary.
- Decision: extend its presentation with a compact icon mode for list rows while preserving its current details-page rendering and behavior.

### Scope layout

- `GitLabScopePage` renders the existing GitLab repository tree and `ScopeSelectionSummary` in sibling Material UI Grid columns. The selected panel currently has no sticky positioning.
- The wizard bottom navigation is fixed to the viewport; the parent wizard layout reserves bottom padding.
- Decision: make the summary column sticky only at the desktop breakpoint, with a top offset and viewport-bounded scrollable height; use normal flow when the columns stack. Keep selection and persistence code unchanged.

### Final save/navigation

- Scheduling is the final Feature 015 wizard route. `ScheduleSection` owns dirty state, existing form validation, and the `useMonitoringSchedule` save operation; `SchedulingPage` owns route navigation.
- The configuration list fetches data when mounted and already presents a success notice from router state.
- Decision: notify the parent only after the existing schedule save resolves successfully, then navigate to `/monitoring-configurations` using router state for the existing success notice. On error, keep the current route and draft. Allow the intentional navigation only after persistence succeeds.

## Alternatives considered

- New manual-execution endpoint/pipeline: rejected because the existing action and execution API already satisfy the required behavior.
- JavaScript scroll listener: rejected because CSS sticky positioning is adequate and simpler.
- Navigate on submit before awaiting persistence: rejected because it can conceal failed saves and lose the user's draft.
- New list cache/invalidation subsystem: rejected because list mount triggers the existing list fetch after route navigation.

## Unresolved research questions

None. The requested changes can reuse current UI, API, routing, and persistence conventions.
