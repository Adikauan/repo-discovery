# Research: Monitoring Configuration Wizard Flow Consolidation

## Decision: Reuse the existing frontend and backend architecture

- **Decision**: Refactor the existing React/TypeScript, Material UI, React Router and FastAPI code paths; reuse current form hooks, API clients, save use cases, and Problem Details handling.
- **Rationale**: The feature changes field ownership and navigation, while existing Features 001-014 already own the business and provider behavior. A rewrite would increase regression risk.
- **Alternatives considered**: Rebuild the configuration area as a new wizard application; rejected because it duplicates tested behavior and exceeds the visual/navigation scope.

## Decision: Use shared fixed navigation with route-derived active step

- **Decision**: Use a shared wizard layout and bottom bar; derive active step from the current route. Make the progress indicator informational and leave previous/next navigation to the bottom bar.
- **Rationale**: Route-derived state avoids stepper drift, while one action surface prevents a competing navigation model. The bar must attach to the main content region and reserve scroll space.
- **Alternatives considered**: Keep each page's current header actions and clickable stepper; rejected because those are duplicate navigation paths. Put the bottom bar inside the form card; rejected because it would scroll out of view.

## Decision: Keep General data transient until GitLab Connection can create a complete configuration

- **Decision**: Hold only non-secret General values in an in-memory create wizard draft after General Next. Do not persist a draft. Create the Monitoring Configuration after GitLab Connection candidate validation.
- **Rationale**: The current create operation requires `gitlab_url`; General is forbidden from collecting it; no draft endpoint or new persistence is approved.
- **Alternatives considered**: Add incomplete/draft Monitoring Configurations to the database; rejected because that introduces persistence/domain lifecycle behavior outside the feature. Keep URL in General; rejected by field ownership.

## Decision: Add minimal server-side candidate validation without configuration persistence

- **Decision**: Add an operation that accepts candidate GitLab URL/token, calls the existing `GitLabConnectionClient.validate`, and returns normalized safe status without reading/writing configuration, credential, or execution persistence. After success, create the configuration, save the credential via existing secure storage, and call existing saved-credential validation to record its validated URL fingerprint.
- **Rationale**: Current candidate validation requires a configuration ID, but the approved create flow must validate before configuration creation. Saved validation state is required by current scope and mining flows, so candidate prevalidation alone is not sufficient after credential storage.
- **Alternatives considered**: Create an empty config to obtain an ID before candidate validation; rejected because the accepted decision requires validation before creation and creates abandoned incomplete records. Send provider traffic from the browser; rejected because credential handling and GitLab integration remain server-side.

## Decision: Reuse existing create idempotency and existing per-step persistence

- **Decision**: Keep one idempotency key for a create wizard attempt and reuse it for retries; after an ID is returned, retries resume credential save/validation using that ID. Next invokes existing save behavior for edit, Scope, Authors, and Scheduling; Back does not save and retains the current unsaved-change guard.
- **Rationale**: The existing create API accepts an `Idempotency-Key`; existing scopes/policies/schedules have their own revision or stale-write behavior. Reuse avoids duplicate creation and lost edits without new persistence.
- **Alternatives considered**: Add a generic multi-step transaction endpoint or draft table; rejected as unnecessary backend/domain expansion.

## Decision: Preserve current enabled and schedule behavior

- **Decision**: New configurations retain the existing disabled default. Enable/Disable is available only in General after creation. Scheduling remains an independent schedule setting and final `Save schedule` stays on the Scheduling step after success.
- **Rationale**: Existing create behavior defaults disabled; scheduler enabled state is independent from Monitoring Configuration enabled state. The feature relocates controls without changing lifecycle semantics.
- **Alternatives considered**: Add enabled selection to the create API or finish at a new summary page; rejected as new behavior not required by the specification.

## Decision: Use supplied visual references as layout guidance

- **Decision**: Map `03-new-configuration-general.png`, `04-gitlab-connection.png`, `05-scope-selection.png`, `06-author-policies.png`, and `07-scheduling.png` to their matching wizard steps. Use Feature 013/014 styling for the list because no Feature 015 list reference exists.
- **Rationale**: All five supplied images show the corresponding forms/proportions, while the specification governs fixed positioning, actions, and behavior.
- **Alternatives considered**: Treat the screenshots as pixel-perfect or behavioral contracts; rejected because they are visual guidance only and some bottom actions appear within content rather than viewport-fixed.
