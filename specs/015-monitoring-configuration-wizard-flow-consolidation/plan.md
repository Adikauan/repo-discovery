# Implementation Plan: Monitoring Configuration Wizard Flow Consolidation

**Branch**: `015-monitoring-configuration-wizard-flow-consolidation` | **Date**: 2026-09-30 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification and clarification decisions from `specs/015-monitoring-configuration-wizard-flow-consolidation/`.

## Summary

Unify new and edit configuration journeys into the five specified steps, reuse current forms and domain operations, move navigation into a shared fixed bottom bar, and remove duplicate configuration actions. New-mode General values stay only in a transient in-memory draft; a new server-side candidate GitLab validation operation is required because the current validator requires a configuration ID. After successful prevalidation, GitLab Connection Next creates the configuration, securely saves the credential through existing storage, confirms its saved validation state, and then advances. No draft record, migration, or new domain semantics are introduced.

## Technical Context

**Language/Version**: TypeScript/React frontend; Python backend (existing project runtimes)

**Primary Dependencies**: Existing Material UI and React Router frontend; existing FastAPI API, application use cases, and GitLab connection client

**Storage**: Existing PostgreSQL records and credential store; no new schema or persistence for this feature

**Testing**: Vitest + React Testing Library + axe for frontend; pytest/API tests for the new candidate-validation contract and GitLab adapter interaction

**Target Platform**: Existing desktop-first browser application and its API

**Project Type**: Web application with frontend and backend projects

**Performance Goals**: Preserve current step load and save expectations; candidate validation uses the existing GitLab connection client and must return its normalized result without waiting on configuration persistence

**Constraints**: No credential in logs, responses, browser storage, or persistent wizard context; no new persistence/migrations; preserve Feature 014 behavior and all existing domain semantics; Next saves/validates before advancing, except create-mode General which remains an in-memory draft

**Scale/Scope**: Five wizard steps, existing Monitoring Configuration data, no new mining or scheduler scale requirements

## Constitution Check

### Pre-design gates

- Clean Architecture: candidate GitLab validation is an application use case over the existing GitLab connection port; provider HTTP behavior remains in infrastructure.
- Domain-centered rules: UI coordinates existing validation/save use cases and does not reimplement domain validation.
- Explicit contracts: one minimal read-only validation request/response contract is added only because the existing candidate-validation route requires a persisted configuration ID.
- Secure by construction: candidate token crosses the browser-to-server boundary only for transient validation and secure credential submission; it is never logged, returned, or stored in the in-memory general draft.
- Immutable execution history: no execution or snapshot data is altered.
- One mining pipeline: no mining or scheduling path is changed.
- Observable lifecycle: no execution lifecycle changes.
- Migration-managed persistence: no migration is planned.
- Risk-based verification: route, save failure, duplicate-create, credential safety, and step ownership regressions receive automated coverage.
- Deliberate reusable UX: share one stepper/layout/bottom bar, reuse existing step-specific forms/hooks, preserve keyboard and focus behavior.
- Incremental simplicity: frontend changes are localized to configuration routes/components; one backend validation use case/contract is the only backend addition.
- Justified dependencies: no new packages.

**Gate result**: PASS. The validation contract is a narrowly scoped server-side operation with no persistence or domain change. It is required to satisfy the approved field ownership and create sequencing while the current validator requires a configuration ID.

## Design Decisions

### Existing UI and save behavior

Before implementation, routes were declared in `src/app/routes/routeConfig.tsx`: New General was `/monitoring-configurations/new`; edit General was `/:id/edit`; Scope and Authors used `/:id/scope` and `/:id/authors`; Scheduling controls appeared on the configuration overview. The `/:id` overview combined identity, credential controls, scope summary, execution actions, schedule controls, Enable, and Delete. The previous step indicator linked directly to routes/anchors. Feature 015 moves connection and schedule responsibilities into explicit routes and leaves `/:id` as a read-only overview.

The General form currently owns `gitlab_url` and submits it with name/description. Create requires a URL and has no draft operation. Credential candidate validation is currently `POST /monitoring-configurations/{id}/gitlab-connection/validate`; secure credential save is a separate `PUT`, and saved-credential validation records a URL fingerprint needed by scope/mining. Scope and Authors have dirty state and explicit saves; Schedule has a draft, explicit save, and discard blocker.

### Route and wizard model

Use one `MonitoringConfigurationWizardLayout` with one non-clickable, accessible five-step progress indicator and one `WizardBottomBar`. The bar is fixed to the main application content area (offset around the persistent sidebar at desktop widths), with responsive full-width placement when the shell collapses. Reserve page bottom space at least equal to the bar height plus spacing. Previous/Next are the only step-navigation controls; the stepper is informational and not a second navigation mechanism.

| Step | Create route | Edit route | Active index |
|---|---|---|---:|
| General | `/monitoring-configurations/new` | `/monitoring-configurations/{id}/edit` | 0 |
| GitLab Connection | `/monitoring-configurations/new/gitlab-connection` | `/monitoring-configurations/{id}/gitlab-connection` | 1 |
| Scope | after create: `/monitoring-configurations/{id}/scope` | same | 2 |
| Authors | `/monitoring-configurations/{id}/authors` | same | 3 |
| Scheduling | `/monitoring-configurations/{id}/schedule` | same | 4 |

The new-mode General draft and non-secret candidate URL are held by an in-memory wizard provider shared by the two create routes; a direct connection-step URL without its General draft returns to General. Neither is written to browser storage. The candidate token remains only in the credential input component and is cleared on explicit discard/submission. A stable create idempotency key is reused on retry. Once create returns an ID, retain it on the connection step so credential-save retries do not repeat creation. Existing `/:id` remains a read-only configuration overview for compatibility; its configuration-edit shortcuts and controls are removed. The list's Edit action opens step 1; its Open/name action may continue to the read-only overview. Execution history/manual execution access remains available from the overview.

Invalid configuration IDs keep existing not-found behavior. Legacy routes for Scope, Authors, and Scheduling remain deep-linkable and render the shared wizard shell with the corresponding active step. General/Connection steps are deep-linkable for existing IDs. Create-mode Connection is reachable only with in-memory General draft state.

### Field and action ownership

| Area | Editable responsibility and actions | Removed from this area |
|---|---|---|
| General | Name, Description; for existing configurations, current Enable/Disable mutation | GitLab URL/token, scope, author policies, schedule, Delete |
| GitLab Connection | GitLab URL; credential state, candidate validation, replace/remove under existing secure behavior | Name/Description/Enable, scope, author policies, scheduling |
| Scope | Existing dynamic group/repository discovery, selection, summary, stale/unavailable state | General, connection credentials, authors, scheduling |
| Authors | Feature 014 scope-aware policies | General, connection, scope editing, scheduling |
| Scheduling | Existing recurrence/time/timezone/enabled/preview/save/remove behavior | General, GitLab connection, scope, authors, Enable/Disable configuration, Delete |
| Configurations list | New, Open/Edit, Delete; existing search | Enable/Disable, configuration section shortcuts |
| Configuration overview | Read-only identity/status plus existing execution history/manual execution | All settings/forms, section shortcuts, Enable/Disable, Delete |

New configurations retain the existing disabled default. Enable/Disable is available after creation in General only; new-mode General does not imply a new enabled-create contract.

### Save and navigation contract

| Step/context | Save trigger | Next/final behavior | Back behavior |
|---|---|---|---|
| General, new | No API save. Validate name/description and retain General values in the in-memory draft. | Move to new-mode GitLab Connection. | Cancel/back to list is outside the wizard; warn before discarding a dirty draft. |
| GitLab Connection, new | User validates the candidate URL/token using the new non-persisting server operation. | After successful prevalidation, create using existing create contract; save credential through existing secure endpoint; validate the saved credential to persist its validated URL fingerprint; advance to Scope only when these succeed. Keep returned ID and retry failed post-create credential steps without duplicate creation. | Return to General preserving General draft. Clear transient token only after explicit discard; warn if an unsubmitted token would be cleared. |
| General, edit | Existing full configuration update with current ETag; carry the persisted URL unchanged as a non-editable API field because existing PUT is full-resource. | Save via existing update and advance only after success; refresh current revision. | Use existing route/dirty guard; never silently discard form edits. |
| GitLab Connection, edit | URL update uses existing configuration update/ETag. Candidate credential uses existing scoped validation; saved replacement uses secure credential save and saved validation. | Save changed URL/credential and required validation before advancing; unchanged/missing credential follows existing allowed behavior and safe status. Refresh revision after mutation. | Existing connection form feedback/guard; unsaved candidate token is cleared only after user confirms leaving. |
| Scope | Existing `useGitLabScope.save()` with its scope ETag. | Next saves dirty scope, then advances; failure stays on Scope with draft/error. | Existing `useBlocker` confirmation remains. |
| Authors | Existing `saveAll()` and configuration revision/CAS semantics. | Next saves dirty policies, then advances; failure stays on Authors. | Existing dirty-policy blocker remains. |
| Scheduling | Existing schedule save and revision/stale-write handling. | Bottom-right `Save schedule` invokes the existing save, shows current success feedback, and remains on the final step; no next step is added. | Existing schedule dirty blocker remains. |

Stepper labels are not clickable. Exit to the configurations list and browser navigation use the relevant existing dirty guard; shared wizard shell must coordinate a step's guard before route change. Do not create a second save operation, change endpoint meaning, or turn Back into implicit save.

### Candidate validation contract and backend impact

Add `POST /api/v1/gitlab-connections/validate-candidate` for create mode only. Request contains GitLab base URL and a candidate token; response contains normalized safe validation state/result/message/time only and no token, raw provider payload, or configuration ID. It calls the existing `GitLabConnectionClient.validate` through a use case and does not read/write Monitoring Configuration, credential, schedule, scope, or execution persistence. Existing Problem Details mapping is reused. The token must be redacted from logs and exception text.

The frontend calls existing configuration create only after candidate validation succeeds. It creates with General values and GitLab URL, then uses existing secure credential save and saved validation operations. Existing public create/update/schedule/authors contracts keep their shape; the new validation route is additive. No other backend contract or persistence changes are planned.

### Feature 014 and Feature 005/009 compatibility

Authors uses existing policy endpoints, branch discovery, dirty policy state, and optimistic revision behavior with no policy semantics changes. Scheduling continues to use the existing model, preview, save/remove APIs, recurrence, timezone/DST, and conflict behavior. The new shared shell owns only navigation and presentation.

### Reference mapping

All five supplied images were inspected:

| Reference | Screen mapping and use |
|---|---|
| `references/03-new-configuration-general.png` | General step, title/stepper hierarchy, name/description grouping, first-step Cancel/Next composition |
| `references/04-gitlab-connection.png` | GitLab URL and credential form, connection state, previous/next composition |
| `references/05-scope-selection.png` | Scope tree and selected-scope summary proportions |
| `references/06-author-policies.png` | Authors scope rows, branch/author grouping, Group branch-not-applicable treatment |
| `references/07-scheduling.png` | Scheduling form grouping, recurrence/time/timezone, preview, final save placement |

The references do not include a Monitoring Configurations list image or a separate fixed-bar example. The list is validated against its existing Feature 013/014 visual system. Some references show navigation at the bottom of a card/content block; the higher-priority Feature 015 requirement is a viewport-fixed bar attached to main content, with reserved scroll space. Decorative sample data or values in images do not become requirements. The images were inspected during implementation; visual comparison against a running browser remains pending because the configured computer-use/browser surface is unavailable and Vite cannot load its config in this environment (`spawn EPERM`).

## Implementation Structure

### Planned touch points

Frontend:

- `src/app/routes/routeConfig.tsx` and `src/app/routes/navigation.tsx`: route destinations and stable wizard step mapping.
- `src/features/monitoring-configurations/components/MonitoringConfigurationWizardLayout.tsx`, `ConfigurationWizardProgress.tsx`, and new `WizardBottomBar.tsx`: shared shell, non-clickable stepper, fixed main-area bar, spacing, responsive/focus behavior.
- New wizard draft context under `src/features/monitoring-configurations/`: in-memory General state and stable create idempotency key; no token in shared draft or storage.
- `MonitoringConfigurationForm.tsx`, `NewMonitoringConfigurationPage.tsx`, `EditMonitoringConfigurationPage.tsx`: General-only fields, enabled placement, create/edit state.
- New `GitLabConnectionPage.tsx`, existing `GitLabConnectionPanel.tsx`, `GitLabCredentialForm.tsx`, `gitlabConnectionApi.ts`, connection hooks/types: URL ownership, transient candidate validation, secure save/retry.
- `GitLabScopePage.tsx`, `AuthorPoliciesPage.tsx`, `ScheduleSection.tsx`/new `SchedulingPage.tsx`: shared navigation callbacks around existing save/hook operations; preserve their business forms.
- `MonitoringConfigurationsPage.tsx`, `MonitoringConfigurationDetailsPage.tsx`: move Edit entry to General, remove list Enable, remove detail actions/forms; keep list Delete and read-only overview execution capabilities.
- `src/test/features/monitoring-configurations/` and `src/test/app/routes.test.tsx`: contract, ownership, routes, save, failure/retry, and existing Feature 014/005 regression coverage.

Backend:

- `backend/app/application/use_cases/`: add candidate validation use case over the existing client port.
- `backend/app/api/v1/gitlab_connections.py` (or existing connection router module) and schemas/router registration: expose the additive candidate-validation operation.
- `backend/app/domain/ports/gitlab_connection_client.py` and `backend/app/infrastructure/gitlab/http_gitlab_connection_client.py`: reuse the existing validation abstraction; change only if its current normalized result needs a minimal adapter method.
- `backend/tests/unit/application/`, `backend/tests/api/`, and `backend/tests/infrastructure/`: no-persistence, normalized errors, provider calls, and secret non-disclosure.

No data-model migration or execution snapshot change.

### Project Structure

```text
specs/015-monitoring-configuration-wizard-flow-consolidation/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── wizard-navigation.md
│   └── gitlab-candidate-validation.md
└── tasks.md

src/app/routes/
src/features/monitoring-configurations/{api,components,context,hooks,pages,types}/
src/test/features/monitoring-configurations/
backend/app/{api/v1,application/use_cases,domain/ports,infrastructure/gitlab}/
backend/tests/{unit/application,api,infrastructure}/
```

**Structure Decision**: Incremental changes to the existing React/TypeScript frontend and FastAPI backend. Existing page forms and use cases are reused; shared wizard presentation is isolated in focused frontend components. The only backend addition is validation of an unpersisted candidate connection.

## Delivery Phases

1. Confirm route/form/contract baseline; specify new candidate validation contract and automated test coverage.
2. Implement server-side candidate validation with normalized safe results and no persistence/logging of secrets.
3. Add transient create-mode wizard draft and shared layout/stepper/bottom bar, including route mapping and dirty-state coordination.
4. Move General and GitLab Connection ownership; implement create validation → create → secure save → saved validation sequence and retry identity handling.
5. Integrate Scope and Authors existing saves with Next and previous navigation; preserve Feature 004/014 semantics.
6. Move Schedule to the final step and integrate existing save/remove/conflict behavior.
7. Remove competing detail shortcuts and list Enable; centralize Enable in General and Delete in the list; preserve read-only overview execution actions.
8. Validate route/ownership/save/security/accessibility/responsive regressions and compare all supplied references manually where tooling permits.

**Dependencies**: Candidate validation contract/use case precedes create-mode connection UI. Shared navigation/state precedes all page integrations. Route mapping and draft creation precede create-mode end-to-end tests. Field ownership refactor precedes ownership regression tests. Existing Feature 014/005 forms remain dependent on shared layout but their business logic is not changed. Final visual validation follows all screen migrations.

## Test Strategy

- Backend: unit-test candidate URL/token validation, provider success/failure, no persistence calls, and safe response/log behavior; API-test request shape and Problem Details; mock the existing GitLab client. No PostgreSQL integration or migration test is needed because no schema changes are planned.
- Frontend: use existing Vitest/RTL patterns for each step's field ownership, route/stepper state, navigation, save-before-advance, invalid/save failure, create draft, preflight/create/credential retry without duplication, list/detail action placement, and return/back/dirty guards.
- Accessibility: axe checks and keyboard/focus tests for the fixed bar, active step semantics, step controls, focus visibility, responsive content obstruction.
- Regression: retain Feature 014 author policy, Feature 004 scope, Feature 005/009 schedule, credential security, CRUD and delete confirmation tests; update only visual/route assumptions changed by Feature 015.
- Build: `npm run test:run` and `npm run build`; backend targeted pytest tests for candidate validation/API. Manual reference review remains an explicit task and is not marked complete unless actually performed.

## Risks and Mitigations

- **Create retry after partial completion**: hold the returned configuration ID and reuse the existing idempotency key; never issue a second create after an ID is known.
- **Token validation happens before an ID exists**: use a server-side, non-persisting candidate operation based on the existing GitLab client, then confirm validation again through the existing persisted credential validation flow after save.
- **Credential secret leakage**: token remains transient in the credential form until secure submission; avoid context/local-storage, response bodies, logs, and raw provider exceptions.
- **Existing forms have different dirty/save models**: adapt the shared bar to callbacks; do not rewrite domain forms or make Back save implicitly.
- **Fixed bar overlaps persistent sidebar**: place/size it in the main content viewport and reserve page bottom padding; test desktop and narrow shell behavior.
- **Reference images are not authoritative for fixed placement**: follow FR-009/010 even if images depict an in-content bottom action row.

## Complexity Tracking

No constitution violations. The one new server route/use case is justified by the existing candidate validator requiring a configuration ID while the approved flow prohibits creating a configuration until after candidate validation.
