# Feature Specification: Monitoring Configuration CRUD

**Feature Branch**: `002-monitoring-configuration-crud`

**Created**: 2026-09-28

**Status**: Draft

**Input**: User description: "Create Feature 002 - Monitoring Configuration CRUD. Allow users to create, list, view, edit, enable, disable, and delete monitoring configurations containing only identity and lifecycle information. Provide validation, persistence, frontend and backend CRUD, API contracts, and user feedback while deferring GitLab credentials and connection validation, repository/group discovery and selection, scheduling configuration, mining, executions, findings, analytics, authentication, and authorization. Reuse the Feature 001 application shell without redesigning it."

## Clarifications

### Session 2026-09-28

- Q: If two changes are made to the same configuration before either user sees the other’s save, what should happen when the later save arrives? → A: Reject a save based on outdated values; show a conflict and let the user reload or reapply.
- Q: How should the system distinguish a retried create request from a separate request to create a configuration with the same values? → A: The backend generates the Monitoring Configuration identifier. A client may optionally supply an idempotency key for retry replay; it is not the configuration identifier and is not required for creation.
- Q: Should a newly created Monitoring Configuration be enabled or disabled by default? → A: Every new configuration is created disabled; enabling is a separate explicit action after creation.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Create and Find a Monitoring Configuration (Priority: P1)

As a platform user, I can create a monitoring configuration and find it in the configuration
listing so that the application has a named, persisted record for future mining capabilities.

**Why this priority**: Creation and discoverability establish the core value of this feature and
provide the record that later configuration and mining capabilities will extend.

**Independent Test**: Create a valid configuration, then verify its saved values appear in the
listing and its details page. Submit missing or invalid required values and verify that no record is
created and the affected fields explain how to correct the input.

**Acceptance Scenarios**:

1. **Given** the user is on the configuration listing, **When** they choose to create a
   configuration, **Then** a form is shown for name, optional description, and GitLab instance URL;
   enabled status is not editable until after creation.
2. **Given** the required values are valid, **When** the user saves the form, **Then** the
   configuration is persisted with a unique identifier and creation and update dates, success is
   communicated, and the created configuration can be opened.
3. **Given** the name or GitLab instance URL is missing or invalid, **When** the user submits the
   form, **Then** field-specific validation is shown and no configuration is persisted.
4. **Given** saved configurations exist, **When** the user searches by name, **Then** the listing
   shows only active configurations whose names match the trimmed query without case sensitivity.
5. **Given** a configuration is listed, **When** the user chooses its details or edit action,
   **Then** the corresponding configuration page opens.
6. **Given** a create request includes an optional idempotency key and succeeded but its response
   was not received, **When** the same request is retried with the same key and values, **Then** the
   original result, including the backend-generated configuration identifier, is returned and no
   duplicate configuration is created. Without a key, each accepted create request is a separate
   creation intent; clients are not required to provide a configuration identifier.
7. **Given** the user creates a valid configuration, **When** creation succeeds, **Then** the
   saved configuration is disabled and can be enabled only through a separate explicit action
   afterward.

---

### User Story 2 - Review and Update a Monitoring Configuration (Priority: P2)

As a platform user, I can review and edit an existing configuration, including its enabled status,
so that its identity and future availability remain accurate.

**Why this priority**: Users need to maintain configuration values and control whether a
configuration remains available to future scheduled-execution capabilities.

**Independent Test**: Open a persisted configuration, verify all defined fields, edit each editable
field, and verify the saved values and update date. Verify that its identifier and creation date
remain unchanged, and that invalid updates leave the previous saved values intact.

**Acceptance Scenarios**:

1. **Given** an active configuration exists, **When** the user opens its details, **Then** its
   name, description, GitLab instance URL, enabled status, creation date, and last update date are
   displayed.
2. **Given** the user edits an active configuration with valid values, **When** the change is
   saved, **Then** the edited values are persisted, the identifier and creation date are preserved,
   the last update date reflects the successful change, and success feedback is shown.
3. **Given** an edit contains a missing required value or invalid URL, **When** it is saved,
   **Then** the relevant validation feedback is shown and the previously saved configuration is
   unchanged.
4. **Given** an active configuration is enabled, **When** the user disables it, **Then** its
   status changes to disabled and the update date reflects the change without starting mining.
5. **Given** an active configuration is disabled, **When** the user enables it, **Then** its
   status changes to enabled and the update date reflects the change without starting mining.
6. **Given** a requested configuration does not exist or is no longer available, **When** the user
   opens or updates it, **Then** a clear unavailable-configuration state is shown and no other
   configuration is changed.
7. **Given** another change has already saved since the user loaded a configuration, **When** the
   user submits their stale edit, **Then** the save is rejected as a conflict, current saved values
   are preserved, and the user can reload or reapply their changes.

---

### User Story 3 - Delete a Monitoring Configuration Safely (Priority: P3)

As a platform user, I can explicitly confirm deletion of a configuration so that it is removed
from active management without preventing future execution history from retaining its context.

**Why this priority**: Deletion is necessary for lifecycle management, but requires an explicit
confirmation and history-compatible behavior because future executions may refer to a configuration.

**Independent Test**: Request deletion and cancel to verify the configuration remains active.
Confirm deletion and verify that it leaves the active listing and ordinary details/edit access,
while the retained configuration reference remains available to future history relationships.

**Acceptance Scenarios**:

1. **Given** an active configuration, **When** the user requests deletion, **Then** a confirmation
   prompt identifies the configuration and offers confirm and cancel actions.
2. **Given** the confirmation prompt is open, **When** the user cancels, **Then** the configuration
   remains active and unchanged.
3. **Given** the user confirms deletion, **When** the operation succeeds, **Then** the
   configuration is removed from active listing and ordinary user-facing management, and clear
   success feedback is shown.
4. **Given** deletion is confirmed, **When** the configuration is retired, **Then** its retained
   identity and configuration values remain available for future historical execution references;
   deletion does not cascade to unrelated records.
5. **Given** deletion fails, **When** the operation returns an error, **Then** the configuration
   remains available and an understandable error with recovery guidance is shown.

### Edge Cases

- Name contains only whitespace, has leading/trailing whitespace, or differs from another
  configuration only by capitalization.
- Optional description is absent, empty, whitespace-only, or contains leading/trailing whitespace.
- GitLab instance URL is absent, whitespace-only, malformed, relative, has an unsupported scheme,
  or includes surrounding whitespace.
- A user searches with an empty or whitespace-only query, no match, or a query containing percent,
  underscore, asterisk, backslash, brackets, or other characters that must be treated literally.
- The listing contains no active configurations, is loading, or cannot be retrieved because of an
  API or network error.
- A configuration becomes unavailable between opening its details and saving an edit or confirming
  deletion.
- Another edit is saved after a user loads the configuration but before that user submits their
  changes.
- A repeated enable/disable request asks for the status the configuration already has.
- A create or update request is repeated after an uncertain response or retry.
- An optional idempotency key is reused with different values, or a client attempts to provide a
  configuration identifier in the create body.
- Two configurations have the same name; uniqueness is guaranteed by identifier, not name.
- Deletion is requested for an already deleted or unknown identifier.
- A configuration is deleted after future features have associated historical records with it.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST represent a Monitoring Configuration with a unique identifier, name,
  optional description, GitLab instance URL, enabled status, creation date, and last update date.
- **FR-002**: Users MUST be able to access a persisted listing of active Monitoring Configurations
  that displays name, useful description, GitLab instance URL, enabled or disabled status, creation
  date, last update date, and available actions.
- **FR-003**: The listing MUST support loading, empty, and error states with clear user-facing
  messages and an appropriate retry action when retrieval can be retried.
- **FR-004**: Users MUST be able to search active configurations by name using a query trimmed of
  leading and trailing whitespace and matched as a case-insensitive substring. An empty or
  whitespace-only query MUST apply no filter and show all active configurations. Query characters
  MUST be treated literally: `%`, `_`, `*`, and other wildcard-like or escape characters MUST NOT
  change the matching semantics. If SQL `LIKE`/`ILIKE` is used internally, the implementation MUST
  escape its wildcard and escape characters so they are searched literally.
- **FR-005**: Users MUST be able to navigate from the listing to create a configuration, view its
  details, and edit an active configuration.
- **FR-006**: Users MUST be able to create a configuration with a name, optional description, and
  GitLab instance URL. The system MUST create every new configuration with enabled set to false;
  changing it to enabled MUST require a separate explicit user action after creation.
- **FR-007**: A configuration name MUST be non-empty after leading and trailing whitespace is
  removed. Names MUST NOT be required to be unique.
- **FR-008**: A GitLab instance URL MUST be non-empty after leading and trailing whitespace is
  removed and MUST identify an absolute HTTP or HTTPS URL with a host. Surrounding whitespace MUST
  be ignored when validating and saving the URL.
- **FR-009**: Optional descriptions MUST be stored as absent when omitted or whitespace-only;
  non-empty descriptions MUST have surrounding whitespace removed.
- **FR-010**: Invalid fields MUST receive clear, field-associated validation feedback. Invalid
  create or update requests MUST NOT persist partial or invalid changes.
- **FR-011**: Successful creation MUST persist the configuration with a unique stable identifier,
  generated by the backend, a creation date, and a last update date. The create response MUST
  return the generated identifier and MUST provide success feedback and a path to the created
  configuration. Clients MUST NOT choose or provide the configuration identifier.
- **FR-012**: The system MUST provide a retrievable details view for an active configuration with
  its name, description, GitLab instance URL, enabled status, creation date, and last update date.
- **FR-013**: Users MUST be able to edit the name, description, GitLab instance URL, and enabled
  status of an active configuration using the same validation rules as creation.
- **FR-014**: A successful edit MUST preserve the configuration identifier and creation date and
  MUST update the last update date. A rejected or failed edit MUST preserve all previously saved
  values. An edit based on a configuration version that is no longer current MUST be rejected as a
  conflict; the user MUST be able to reload the current values or reapply their changes.
- **FR-015**: Users MUST be able to enable or disable an active configuration after it has been
  created. Changing this
  status MUST NOT start a mining execution. Repeating a request for the current status MUST be safe
  and MUST NOT create additional side effects.
- **FR-016**: Successful changes to a configuration MUST update its last update date; requests
  that leave all saved values unchanged MUST NOT make the last update date appear newer.
- **FR-017**: Users MUST be able to delete a configuration only after confirming an explicit
  deletion prompt. Canceling MUST leave it unchanged.
- **FR-018**: Deletion MUST logically retire a configuration from active listings and ordinary
  user-facing detail/edit operations while retaining its identifier and configuration values for
  future historical execution references. Deletion MUST NOT cascade to unrelated records, and
  restoring a retired configuration is outside this feature.
- **FR-019**: The system MUST provide clear feedback for successful creation, update, deletion,
  enable/disable actions, validation failures, API failures, unavailable configurations, and empty
  listings. Errors MUST use understandable language and provide recovery guidance when available.
- **FR-020**: The frontend and backend MUST exchange explicit, versionable contracts for create,
  list, retrieve, update, delete, and lifecycle status changes. Contracts MUST define accepted
  values and user-relevant validation, conflict, and error outcomes without exposing
  persistence-provider details. Updates MUST identify the configuration version the user edited so
  stale edits can be rejected without overwriting newer saved values. The backend MUST generate the
  Monitoring Configuration identifier; create requests MUST NOT require or accept a
  client-selected configuration identifier, and the create response MUST return the generated ID.
  A separate optional idempotency key MAY be provided to identify a create-request retry; it is not
  a Monitoring Configuration identifier. If present, it MUST be a non-empty value of at most 128
  visible ASCII characters, with no whitespace or control characters; it is opaque and is not
  required to be a UUID. An invalid key MUST be rejected without creating a configuration.
- **FR-021**: When a create request includes an idempotency key, repeating it with the same key and
  semantically identical normalized values MUST return the original outcome, including the same
  backend-generated configuration identifier, without creating a duplicate. Reusing that key with
  different values MUST return a conflict without creating or changing a configuration. A different
  key, or a request without a key, MUST represent a separate creation intent, even when its values
  match another configuration. If supplied, an idempotency key MUST satisfy the format defined in
  FR-020 and MUST NOT be interpreted as or used in place of a configuration identifier. Repeated
  enable/disable requests for the current status MUST remain safe and produce no additional side
  effects.
- **FR-022**: Configuration validation and lifecycle rules MUST have one authoritative
  implementation in the appropriate domain or application boundary and MUST NOT be independently
  duplicated in interface layers.
- **FR-023**: The Monitoring Configuration pages MUST use Feature 001's established application
  shell, navigation, theme, and shared presentation patterns without redesigning them.
- **FR-024**: Future capability areas such as GitLab connection, repository scope, scheduling, and
  executions MAY appear as truthful placeholders; they MUST NOT perform or imply implemented
  behavior in this feature.
- **FR-025**: This feature MUST NOT implement GitLab credentials or authentication, GitLab
  connection validation, group or repository discovery or selection, scheduling configuration,
  mining, execution history processing, findings, dashboard analytics, authentication, or
  authorization.

### Key Entities *(include if feature involves data)*

- **Monitoring Configuration**: A persisted, user-managed definition for future repository mining
  intent. It has a unique stable identifier, trimmed name, optional normalized description,
  absolute GitLab instance URL, enabled status, creation date, and last update date. Names are not
  unique. A retired configuration retains its identifier and configuration values for historical
  references and is unavailable through ordinary active-configuration management.
- **Configuration Lifecycle**: The user-visible active/retired lifecycle and enabled/disabled
  availability of a Monitoring Configuration. Retired configurations are excluded from active
  management; enabled status does not execute mining.
- **Configuration Change Request**: A user request to create, update, change enabled status, or
  delete a configuration, with field-level validation outcomes and a user-relevant success or
  failure result.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A valid configuration created through the user workflow is retrievable from the
  active listing and its details view with the submitted normalized values.
- **SC-002**: Every missing or invalid required name or GitLab URL case is rejected with feedback
  associated with the affected field, and rejected changes leave persisted values unchanged.
- **SC-003**: Editing any supported field preserves the identifier and creation date; a successful
  actual change advances the last update date, while an unchanged request does not.
- **SC-004**: The listing can distinguish and present loading, empty, populated, and retrieval-error
  states, and a user can find a configuration by a case-insensitive substring of its name.
- **SC-005**: Enable, disable, and delete actions produce the defined persisted lifecycle outcome
  and user feedback; none starts mining, and canceled deletion leaves the configuration unchanged.
- **SC-006**: Deleted configurations disappear from active listing and ordinary user-facing
  management while retaining their identity and values for future historical references; unrelated
  records remain unchanged.
- **SC-007**: All in-scope operations are available through explicit frontend/backend contracts
  with validation and error outcomes that do not depend on persistence-provider details.
- **SC-008**: All in-scope configuration workflows remain within the established Feature 001 shell
  and do not invoke or imply capabilities explicitly deferred by this specification.
- **SC-009**: Repeating a successful create request with the same optional idempotency key and
  normalized values returns the original result, including the same backend-generated configuration
  identifier, and leaves exactly one created configuration; reuse of that key with different values
  is rejected without changing saved data. A create request without a key is accepted without a
  client-provided configuration identifier.
- **SC-010**: Every newly created configuration is saved with enabled set to false and remains
  unavailable for future scheduled execution until a separate explicit enable action succeeds.

## Assumptions

- Users operate the existing single-user application experience; authentication and authorization
  are out of scope and no ownership or role-specific behavior is introduced.
- Configuration names are not unique. The system-generated identifier is the uniqueness boundary.
- Names and non-empty descriptions are trimmed before persistence; blank optional descriptions are
  normalized to absent. URL surrounding whitespace is trimmed before validation and persistence.
- Name search is a case-insensitive substring match against active configurations; a blank search
  query returns every active configuration.
- Creation date is assigned on successful creation. Last update date is assigned on creation and
  changes only after a successful change to saved values.
- Deletion is logical retirement. The record's stable identifier and configuration values remain
  retained so later execution-history features can preserve references and configuration snapshots;
  this feature provides no restore workflow.
- An enabled configuration is available to future scheduling behavior, but Feature 002 does not
  create schedules or execute mining.
- New configurations are always persisted disabled because later credential, repository-scope,
  and scheduling features may still be incomplete; enabling is a separate post-creation user action.
- Dates are presented in a consistent human-readable form using the user's local display context;
  stored date semantics and exact formatting are implementation-plan decisions.
- API consumers need the operations and outcomes defined above; public contract versioning and
  compatible evolution follow the project constitution.
- The backend generates the unique Monitoring Configuration identifier and returns it in the create
  response. A client may use an optional idempotency key to make retries after an uncertain response
  replay the same outcome; ordinary creation does not require a client-provided identifier. Separate
  intentional creates without a key are separate requests.
- Feature 001 supplies the existing application shell, routes, theme, and reusable visual patterns.
