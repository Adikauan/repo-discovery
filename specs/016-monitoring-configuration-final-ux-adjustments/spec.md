# Feature Specification: Monitoring Configuration Final UX Adjustments

**Feature Branch**: `016-monitoring-configuration-final-ux-adjustments`

**Created**: 2026-09-30

**Status**: Draft

**Input**: User description: "Add manual execution from each Monitoring Configuration list row, keep Selected Scope visible while browsing the GitLab scope tree, and return to the configuration list after a successful final save."

## User Scenarios & Testing

### User Story 1 - Run a configuration from the list (Priority: P1)

As a user reviewing Monitoring Configurations, I want to start a manual execution directly from its row so I do not have to open another screen to run it.

**Why this priority**: Manual execution is an existing core action and the list is the main entry point for configuration management.

**Independent Test**: Render multiple configuration rows, activate one row's manual execution action, and verify only that configuration's existing manual execution operation is requested with existing success and error feedback.

**Acceptance Scenarios**:

1. **Given** a configuration appears in the list, **When** the user activates its manual execution action, **Then** the existing manual execution operation is requested for that configuration only.
2. **Given** a manual execution request is in progress, **When** the row is rendered, **Then** repeat activation is prevented until the request settles.
3. **Given** the request succeeds or fails, **When** its response is received, **Then** existing success or safe error feedback is shown and existing execution lifecycle/concurrency rules remain authoritative.
4. **Given** the configuration is disabled, **When** manual execution is available under existing approved behavior, **Then** Feature 016 does not change that eligibility.

### User Story 2 - Keep Selected Scope visible during tree navigation (Priority: P1)

As a user selecting GitLab groups and repositories, I want the Selected Scope summary to remain visible while I browse a long hierarchy so I can review my current selection without repeatedly scrolling back.

**Why this priority**: Long hierarchies make it difficult to keep track of the chosen monitoring scope.

**Independent Test**: Open the Scope step with a sufficiently long tree, scroll the content, and verify the selected-scope summary remains visible within its layout without covering the stepper or fixed navigation.

**Acceptance Scenarios**:

1. **Given** a desktop Scope page with a long GitLab hierarchy, **When** the user scrolls the tree/page, **Then** Selected Scope remains visible within the Scope content area.
2. **Given** selected items exist, **When** Selected Scope remains visible, **Then** its existing selection details and controls remain usable.
3. **Given** a narrow layout stacks the tree and Selected Scope, **When** the user scrolls or reviews the page, **Then** Selected Scope remains accessible without overlap or unreadable path compression.
4. **Given** any viewport, **When** the user uses the Scope step, **Then** the existing scope discovery, selection, persistence, dynamic group, lazy-loading, search, and unavailable-item behavior is unchanged.

### User Story 3 - Return to the list after final save (Priority: P1)

As a user completing a Monitoring Configuration, I want to return to the configuration list after the final save succeeds so I can see the updated configuration and continue managing configurations.

**Why this priority**: A predictable completion destination closes both create and edit flows and returns users to the primary management view.

**Independent Test**: Complete the final Scheduling action in create and edit flows; verify successful saves navigate to the configuration list, while failures preserve the current step and entered values.

**Acceptance Scenarios**:

1. **Given** a new configuration is at the final save action, **When** all required final operations succeed, **Then** the application navigates to `/monitoring-configurations`.
2. **Given** an existing configuration is at the final save action, **When** all required final operations succeed, **Then** the application navigates to `/monitoring-configurations`.
3. **Given** validation or any required final save operation fails, **When** the failure is handled, **Then** the user remains on the current step, sees existing safe feedback, and retains recoverable input.
4. **Given** the user is redirected after success, **When** the list appears, **Then** it reflects current configuration data using the existing list loading/cache conventions.

### Edge Cases

- A row's manual execution request fails due to existing concurrency, validation, or service errors; show the existing safe failure feedback and allow a later retry when appropriate.
- A user rapidly activates the same row action; only one request is issued while the first is pending.
- Selected Scope has many items; the summary remains usable and does not cover the tree or fixed wizard navigation.
- Sticky behavior is unsuitable for a narrow stacked layout; the summary remains in normal flow and accessible.
- Final save partially fails after an earlier operation succeeded; do not redirect until every required operation succeeds and retain existing retry/recovery behavior.
- A create/edit operation succeeds but list refresh fails; follow existing list load/error behavior without undoing the successful save.

## Requirements

### Functional Requirements

- **FR-001**: Each Monitoring Configuration row MUST expose a manual execution action in the Actions area.
- **FR-002**: The row action MUST use the existing manual execution behavior and target only the Monitoring Configuration represented by that row; it MUST NOT add a second execution path or change concurrency/business rules.
- **FR-003**: The manual execution action MUST expose an accessible name and supplementary tooltip, support keyboard activation and visible focus, and prevent duplicate submission while its request is pending.
- **FR-004**: Manual execution success and failure MUST use existing application feedback conventions and safe error messages. Existing eligibility for disabled configurations MUST remain unchanged.
- **FR-005**: On desktop Scope layouts, Selected Scope MUST remain visible while the user scrolls a long GitLab hierarchy, constrained to the Scope content layout and without overlapping the page heading, stepper, or fixed bottom navigation.
- **FR-006**: On narrower layouts, Selected Scope MUST remain accessible; sticky positioning MAY be disabled when the content stacks, and the layout MUST avoid overlap and unreadable compression.
- **FR-007**: Feature 016 MUST preserve existing GitLab scope discovery, dynamic Group scope, selection, persistence, lazy loading, search, and unavailable-scope semantics.
- **FR-008**: After the final required save for a newly created Monitoring Configuration succeeds, the wizard MUST navigate through application routing to `/monitoring-configurations`.
- **FR-009**: After the final required save for an edited Monitoring Configuration succeeds, the wizard MUST navigate through application routing to `/monitoring-configurations`.
- **FR-010**: The wizard MUST NOT redirect on validation, policy, scope, schedule, or other required finalization failure; it MUST remain on the current step and preserve existing safe error and recoverable-input behavior.
- **FR-011**: Following successful final save, the configuration list MUST use existing query/cache refresh behavior so that saved data is current; navigation MUST NOT hardcode a host or port.
- **FR-012**: Feature 016 MUST preserve the Feature 015 five-step order and navigation, General-only Enable placement, and list-only Delete placement.
- **FR-013**: Feature 016 MUST NOT add persistence, database migrations, new execution or scheduling semantics, or unrelated product functionality.

### Key Entities

- **Monitoring Configuration row action**: A manual-execution request associated with the stable configuration identifier represented by one list row; execution state and lifecycle remain owned by existing execution behavior.
- **Selected Scope summary**: A presentation of the existing groups and repositories selected for the current Monitoring Configuration; its data and semantics are unchanged.
- **Final wizard save**: The existing final Scheduling action for create or edit, including all required existing saves; successful completion determines when the user returns to the list.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Every configuration row with the existing manual-execution capability presents an accessible action that issues no more than one request per activation while pending and targets the row's configuration.
- **SC-002**: On a desktop Scope layout with a long hierarchy, Selected Scope remains visible during scrolling without intersecting the page heading, stepper, or bottom navigation.
- **SC-003**: Successful final saves in both create and edit flows navigate to `/monitoring-configurations`; failed final saves do not navigate away.
- **SC-004**: Existing automated regression coverage for manual execution, scope behavior, and Feature 015 navigation continues to pass without backend or persistence changes.

## Assumptions

- The existing manual execution endpoint/client and success/error presentation are reused.
- The final Scheduling action is the completion point for both create and edit flows; existing intermediate saves and validation remain authoritative.
- Existing list loading is sufficient to show persisted values after navigation, or the current query/cache convention is used if applicable.
- Desktop is the primary target; on stacked narrow layouts, accessible normal-flow Selected Scope is preferable to sticky positioning.
- No visual reference changes the established Feature 013/014/015 behavior or authorizes unrelated scope.
