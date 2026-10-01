# Feature Specification: Monitoring Configuration Wizard Flow Consolidation

**Feature Branch**: `015-monitoring-configuration-wizard-flow-consolidation`

**Created**: 2026-09-30

**Status**: Draft

**Input**: User description: "Create Feature 015 - Monitoring Configuration Wizard Flow Consolidation. Consolidate configuration creation and editing into the five ordered steps General, GitLab Connection, Scope, Authors, Scheduling, assign fields and actions to their proper step, and use fixed bottom navigation without changing existing business behavior."

## Clarifications

### Session 2026-09-30

- Q: When a step has an existing explicit Save action, should the bottom-bar Next action save and validate that step before advancing? → A: Next runs the existing validation and save, then advances only if both succeed.
- Q: When creating a configuration, how should General’s Next behave when the existing create operation requires a GitLab URL, but the URL belongs only in GitLab Connection? → A: Keep General data in the in-memory wizard draft; create the configuration on GitLab Connection Next after URL and credential validation.
- Q: How should token validation work when the existing validator requires a configuration ID, but create mode is meant to create the configuration only after validation? → A: Validate the candidate URL and token through a minimal server-side operation that does not persist a configuration; then create the configuration and save the validated credential on Next.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Create or edit through one ordered flow (Priority: P1)

As a user configuring repository monitoring, I want to create or edit a Monitoring Configuration through one ordered five-step flow so that I can find each responsibility in a predictable place and keep the same configuration context throughout.

**Why this priority**: The primary purpose is to remove the fragmented configuration experience for both new and existing configurations.

**Independent Test**: Create a configuration and open an existing configuration for editing; in both cases verify the same five steps and that next/previous navigation follows their defined order without changing the configuration being edited.

**Acceptance Scenarios**:

1. **Given** a user starts a new Monitoring Configuration, **When** they proceed through the wizard, **Then** the steps are General, GitLab Connection, Scope, Authors, and Scheduling in that order; General Next retains its valid data in the in-memory wizard draft, the server validates the candidate GitLab URL and token without creating a configuration, and GitLab Connection Next creates the configuration and securely saves the validated credential before advancing.
2. **Given** a user opens an existing configuration, **When** they edit it, **Then** they use the same five-step structure and the same configuration remains selected throughout navigation.
3. **Given** a user is on General, **When** they view the bottom navigation, **Then** no nonexistent previous wizard step is offered.
4. **Given** a user is on Scheduling, **When** they view the bottom navigation, **Then** the previous action returns to Authors and the right-side action completes or saves using the existing final-step behavior, without presenting another step.

---

### User Story 2 - Find each setting and action in its owning step (Priority: P1)

As a user maintaining a Monitoring Configuration, I want each existing setting and action to appear only in its designated area so that the wizard has one clear navigation model and cannot suggest that a setting belongs to multiple steps.

**Why this priority**: Misplaced GitLab and scheduling fields, plus duplicate detail shortcuts, are the concrete inconsistencies this feature resolves.

**Independent Test**: Inspect each step and the configuration list/detail surfaces; verify field ownership and that Enable/Disable and Delete are available only in their specified locations.

**Acceptance Scenarios**:

1. **Given** a user views General, **When** its fields and actions are displayed, **Then** it contains Name, Description, and Enable/Disable, and contains no GitLab URL or credentials, Scope, author policies, or Scheduling settings.
2. **Given** a user views GitLab Connection, **When** connection controls are displayed, **Then** GitLab URL, credential status, validation, and existing credential replacement/removal behavior are available there, and Scheduling controls are absent.
3. **Given** a user views Scope, Authors, or Scheduling, **When** that step is displayed, **Then** it contains only its existing responsibility and Enable/Disable and Delete are absent.
4. **Given** a user opens the Monitoring Configurations list, **When** they manage a configuration, **Then** New, Open/Edit, and Delete are available there, while Delete is absent from the wizard and configuration detail header.
5. **Given** a user views configuration navigation or a detail header, **When** they look for section shortcuts, **Then** Edit General, Configure GitLab Scope, Configure Scheduling, and global Enable/Delete shortcuts are absent.

---

### User Story 3 - Navigate without losing work (Priority: P2)

As a user completing configuration, I want fixed previous/next navigation that respects the current step's validation and unsaved-change behavior so that I can move through the flow without losing valid edits or bypassing required checks.

**Why this priority**: Centralized navigation is useful only when it remains safe for existing save and validation behavior.

**Independent Test**: Make valid and invalid edits in each step, navigate forward and backward, and verify existing save, validation, and unsaved-change handling remains effective.

**Acceptance Scenarios**:

1. **Given** any wizard step, **When** the user scrolls the page, **Then** the bottom navigation remains visible and the content remains reachable above it.
2. **Given** a step has required validation or save behavior, **When** the user activates Next or the final action, **Then** the existing validation and save run before navigation, and the user advances only if both succeed.
3. **Given** the user has unsaved changes, **When** they navigate backward or leave the wizard, **Then** the existing safe unsaved-change behavior is preserved and changes are not silently discarded.
4. **Given** the viewport is narrow, **When** the wizard is used, **Then** both navigation actions remain understandable and operable, content remains scrollable, and the bar does not obscure controls or keyboard focus.

### Edge Cases

- A new configuration must establish its existing configuration identity before later steps can operate; failure to save the initial General data must not advance into an unrelated or invalid configuration context.
- If validation or a save action fails, the user remains on the current step with the existing safe error feedback and entered values retained where supported.
- If the configuration identifier in an edit route is invalid or unavailable, existing error handling is used and no other configuration is loaded in its place.
- Long step content and focused controls remain accessible while the fixed bottom bar is present.
- Navigating away from a dirty step follows the existing unsaved-change behavior; the wizard must not introduce silent loss.
- Existing GitLab credential masking, validation, replacement, and removal protections remain in effect after moving the URL and credential controls.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The create and edit experiences MUST present exactly five ordered steps: General, GitLab Connection, Scope, Authors, and Scheduling.
- **FR-002**: The same logical wizard MUST be used for new and existing Monitoring Configurations. In create mode, General values MUST remain in the in-memory wizard draft until GitLab Connection successfully creates the configuration; from then on, the returned configuration identity MUST remain stable throughout the remaining steps. In edit mode, the existing configuration identity MUST remain stable throughout.
- **FR-003**: General MUST own Name, Description, and the existing Enable/Disable action. General MUST NOT display GitLab connection fields, Scope controls, author policies, or Scheduling controls.
- **FR-004**: GitLab Connection MUST be the only wizard step that owns GitLab URL, credential interaction/status, connection validation, and existing credential replacement/removal behavior. Stored credentials MUST remain protected and MUST NOT be revealed. In create mode, candidate URL/token validation MUST be performed server-side without creating or persisting a configuration; the validation response MUST contain only safe status information.
- **FR-005**: GitLab Connection MUST NOT display Scheduling controls, Scope controls, or author policies.
- **FR-006**: Scope MUST contain only existing GitLab group/repository discovery and selection, selected-scope summary, and unavailable-scope handling. Existing dynamic Group scope semantics MUST remain unchanged.
- **FR-007**: Authors MUST contain only existing Feature 014 author-policy configuration, including repository branch policies and Group policies; it MUST NOT contain General, GitLab connection, Scope-selection, or Scheduling controls.
- **FR-008**: Scheduling MUST be the only wizard step that presents existing scheduling settings and actions, including recurrence, time, timezone, enabled state, preview, and disable/remove behavior where supported. Existing scheduling semantics MUST remain unchanged.
- **FR-009**: Each wizard step MUST provide a bottom navigation bar that remains visible at the viewport bottom while the main content scrolls. The content area MUST reserve sufficient space so that the bar does not cover content or controls.
- **FR-010**: The bottom navigation MUST place previous-step navigation on the left and next-step or existing final/save action on the right. General MUST NOT offer a previous wizard step; Scheduling MUST NOT offer a subsequent wizard step.
- **FR-011**: The step indicator MUST show the five steps in the defined order and communicate the active step accessibly.
- **FR-012**: In edit mode and after configuration creation, when the user activates Next or the final action, the wizard MUST run the current step's existing validation and save behavior, then advance or complete only after success. In create mode, General Next MUST validate and retain its values in the in-memory wizard draft without creating a configuration. The GitLab Connection step MUST first validate the candidate URL and token through the server-side non-persisting operation; GitLab Connection Next MUST then create the configuration with the General values and URL, securely save the validated credential, and advance only after success. If creation succeeds but credential saving fails, the wizard MUST retain the created configuration identity on the connection step and support retry without creating a duplicate. Other failed validation or persistence MUST keep the user on the current step with recoverable values. The wizard MUST NOT silently discard valid edits.
- **FR-013**: Backward navigation and leaving the wizard MUST preserve the application's existing unsaved-change handling for General, GitLab Connection, Scope, Authors, and Scheduling.
- **FR-014**: The Monitoring Configurations list MUST remain the entry point for creating/opening configurations and the only location from which deletion can be initiated. Existing delete confirmation and backend rules MUST remain unchanged.
- **FR-015**: Configuration headers and details MUST NOT expose competing shortcuts for Edit General, Configure GitLab Scope, Configure Scheduling, Enable, or Delete.
- **FR-016**: Enable/Disable MUST be exposed only in General. It MUST NOT appear in other wizard steps or as a global/detail-header action.
- **FR-017**: Existing routes MAY remain internally, but user-facing navigation MUST behave as one sequential wizard. Deep links MUST retain the requested configuration context and invalid identifiers MUST use existing error handling.
- **FR-018**: GitLab URL ownership MUST move from General to GitLab Connection without changing the existing persisted meaning or security behavior.
- **FR-019**: Scheduling controls MUST move from GitLab Connection to Scheduling and MUST NOT be duplicated in another step.
- **FR-020**: The fixed navigation, step indicator, and action relocation MUST NOT add domain behavior, new persistence, or changes to GitLab, Scope, author-policy, scheduler, execution, mining, or Finding semantics.
- **FR-021**: Previous/next controls MUST be keyboard accessible, visibly focused, descriptively named, and expose correct disabled states. Fixed navigation MUST NOT obscure keyboard focus.
- **FR-022**: The wizard MUST remain usable at narrower viewport widths; its content MUST remain scrollable and its navigation actions MUST remain understandable and operable.
- **FR-023**: The visual references added under `specs/015-monitoring-configuration-wizard-flow-consolidation/references/` MUST be used during later planning and visual validation as layout guidance only. They MUST NOT override this specification or prior approved behavior.
- **FR-024**: Candidate URL/token validation for a new configuration MUST use the existing server-side GitLab integration, MUST NOT persist the candidate or a draft configuration, MUST NOT return or log the token, and MUST return only normalized safe validation status.

### Key Entities *(include if feature involves data)*

- **Monitoring Configuration**: Existing configuration being created or edited; its identity and persisted settings remain authoritative and unchanged by the navigation redesign.
- **Wizard Step**: One of the five ordered user-facing configuration responsibilities; it represents navigation state and does not create new persisted domain state.
- **Configuration Setting**: An existing setting assigned to exactly one owning step in the user interface, while retaining its current business meaning and persistence behavior.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In both create and edit flows, users encounter exactly five steps in this order: General, GitLab Connection, Scope, Authors, Scheduling.
- **SC-002**: All specified settings appear in their owning step; General displays no GitLab URL or credential fields, and GitLab Connection displays no Scheduling controls.
- **SC-003**: Across the wizard, Enable/Disable is available in exactly one step (General), and Delete is available from exactly one surface (Monitoring Configurations list).
- **SC-004**: Every step displays the fixed bottom navigation; during scrolling, the bar remains visible and no page content or focused control is hidden behind it.
- **SC-005**: All four forward transitions and all four backward transitions reach the adjacent step; create mode preserves General values in memory until the GitLab Connection step creates the configuration, and the returned identity remains stable thereafter.
- **SC-006**: A failed required validation/save does not advance the wizard; successful Next/final actions save before advancing/completing, and existing unsaved-change behavior prevents silent loss when moving backward or leaving.
- **SC-009**: In create mode, failed candidate GitLab validation leaves no persisted configuration; if creation succeeds but credential saving fails, retry retains the created configuration identity and does not create a duplicate.
- **SC-007**: Existing GitLab credential, Scope, author-policy, scheduling, enable/disable, and delete behaviors continue to pass their applicable regression checks without changes in business semantics.
- **SC-008**: On a narrow supported viewport, users can operate both navigation actions and reach all step content without the bottom bar covering controls.

## Assumptions

- Existing APIs and persistence already support all fields and actions; the feature is a frontend flow and responsibility reorganization unless planning identifies a concrete existing contract obstacle.
- Existing per-step validation and save operations remain authoritative. The bottom-bar Next/final action invokes the existing validation and save for the current step and advances/completes only after success; backward/exit navigation continues to use existing unsaved-change behavior.
- In new-configuration mode, no persisted draft is created. General Next retains validated General values in memory; GitLab Connection validates the candidate URL and token through a minimal server-side operation that performs no persistence and returns safe status only. GitLab Connection Next then creates the configuration, securely saves the validated credential, and carries the returned configuration identity through Scope, Authors, and Scheduling. If credential saving fails after creation, retries use the returned ID rather than creating another configuration.
- The first step's left side is empty because there is no previous wizard step.
- The final Scheduling action uses the existing completion/save behavior and does not create another step.
- Existing URLs may be retained internally if they present the unified five-step user experience and preserve configuration context.
- Visual references will be supplied after this specification is created. Their absence does not block specification; planning and later manual visual validation will use them once present.
