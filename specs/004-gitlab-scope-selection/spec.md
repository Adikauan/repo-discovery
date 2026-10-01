# Feature Specification: GitLab Scope Selection

**Feature Branch**: `004-gitlab-scope-selection`

**Created**: 2026-09-28

**Status**: Draft

**Input**: User description: "Create Feature 004 - GitLab Scope Selection. Let users browse the GitLab groups, subgroups, and repositories visible to a Monitoring Configuration's configured credential; select and persist group and repository scope rules; reconcile unavailable selections and GitLab URL changes; and manage the selection through an expandable tree and summary. Do not perform mining or execution."

## Clarifications

### Session 2026-09-28

- Q: Quando um grupo GitLab é selecionado, projetos apenas compartilhados com ele, mas pertencentes a outro grupo, devem entrar no escopo? → A: Não. Uma regra de grupo inclui somente projetos pertencentes ao grupo selecionado ou aos seus subgrupos; projetos apenas compartilhados de outra hierarquia ficam excluídos.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Browse and save a repository scope (Priority: P1)

As a user managing an existing Monitoring Configuration, I can browse its accessible GitLab hierarchy, choose groups and individual repositories, review the choices, and save them for later use.

**Why this priority**: Persisted scope is the core outcome of this feature; browsing and selection are useful only when the intended rules survive reopening the configuration.

**Independent Test**: With a configuration that has a GitLab URL and credential, load top-level groups, expand a group and nested subgroups, choose one group and repositories inside and outside it, save, reopen, and verify that the exact explicit choices reappear. Verify that an empty scope can also be saved and does not enable the configuration.

**Acceptance Scenarios**:

1. **Given** an active Monitoring Configuration has a GitLab URL and configured credential, **When** the user opens scope configuration, **Then** the user can see top-level groups without waiting for every group and repository in the instance to load.
2. **Given** a visible group contains subgroups and repositories, **When** the user expands it, **Then** its available children appear with distinct group and repository presentation and can be expanded to arbitrary depth.
3. **Given** repositories are visible, **When** the user selects one or several repositories and saves, **Then** those explicit repository selections are persisted and restored on reopening.
4. **Given** groups and repositories are visible, **When** the user selects one or several groups, optionally with individual repositories, and saves, **Then** the selected group rules and individual repository rules are persisted distinctly and restored on reopening.
5. **Given** a selected group covers a repository that is also selected explicitly, **When** the scope is interpreted, **Then** that repository is counted once while both explicit choices remain available for later editing.
6. **Given** the scope has selections, **When** the user removes a group, a repository, or all selections and saves, **Then** only the requested explicit choices are removed; an individually selected repository remains selected after its covering group is removed.
7. **Given** a user has changed selections but has not saved, **When** the user compares the tree and summary, **Then** the interface identifies the changes as unsaved and the persisted scope remains unchanged until save succeeds.
8. **Given** no groups or repositories are selected, **When** the user saves, **Then** the empty scope persists and the Monitoring Configuration's enabled state remains unchanged.

---

### User Story 2 - Understand selections and unavailable entities (Priority: P2)

As a returning user, I can distinguish selected groups, individual repositories, and selections that cannot currently be found, so I can retain or deliberately remove each rule.

**Why this priority**: A credential or GitLab hierarchy can change after saving. Silent removal would lose user intent, while silently treating identifiers from another instance as current entities could select the wrong repositories.

**Independent Test**: Save a group and repository, then simulate rename, move, deletion or lost access, credential replacement, and GitLab URL change. Reopen the scope; verify stable selections are retained, reachable metadata is refreshed, unresolved entries are flagged, and each can be explicitly removed. Verify old-instance identifiers are never matched to the new instance.

**Acceptance Scenarios**:

1. **Given** a saved entity is renamed or moved within the same GitLab instance and remains accessible by its stable identifier, **When** the scope is reopened, **Then** its selection remains and its current descriptive information is shown.
2. **Given** a saved group or repository cannot currently be retrieved, **When** the scope is reopened, **Then** its persisted entry remains in the summary with an unavailable label and an explicit remove action; the tree remains usable.
3. **Given** a configured credential is replaced and an old selection becomes inaccessible, **When** the scope is reconciled, **Then** the selection remains persisted and is shown as unavailable rather than being deleted or replaced.
4. **Given** the GitLab instance URL changes after scope was saved, **When** the scope is reopened, **Then** the old scope is marked as belonging to a different instance, none of its identifiers are automatically interpreted against the new instance, and the user can remove the old entries and select new ones.
5. **Given** reconciliation or discovery fails temporarily, **When** the user views the scope, **Then** saved entries remain visible with an unresolved state and retry feedback; failure alone does not delete them.

---

### User Story 3 - Navigate a large hierarchy (Priority: P3)

As a user with access to many GitLab entities, I can expand only relevant branches, search the entities available to the scope interface, and continue selecting without loading the entire instance first.

**Why this priority**: Large and deeply nested GitLab instances must remain navigable, and navigation aids must never change saved intent.

**Independent Test**: Present multiple pages of top-level groups and group children, deeply nested subgroups, empty branches, and controlled errors. Verify all pages are reachable through the interface, progress and retry states appear per branch, search/filter changes only visibility, and selections persist when branches collapse or filters change.

**Acceptance Scenarios**:

1. **Given** the GitLab instance has many groups or projects, **When** the scope interface opens, **Then** the user can begin interacting with available top-level results before unrelated branches are retrieved.
2. **Given** a group has additional results beyond the first page, **When** the user continues browsing that group, **Then** all available pages can be reached without omissions or duplicate nodes.
3. **Given** a branch is loading, empty, or fails to load, **When** the user views that branch, **Then** the tree shows the corresponding loading, empty, or actionable error state without losing other loaded branches or unsaved selections.
4. **Given** a user filters the tree, **When** results are hidden and later restored, **Then** explicit selections and their persisted state are unchanged.
5. **Given** a selected descendant is known while its ancestor group is not selected, **When** the ancestor is displayed, **Then** it can indicate partial selection without creating a group-level rule.

### Edge Cases

- A configuration is missing, retired, lacks a GitLab URL, or has no saved credential; discovery is unavailable and no credential is disclosed.
- The credential is revoked or lacks discovery permission although Feature 003 connection validation previously succeeded.
- GitLab returns an empty hierarchy, incomplete or malformed entity data, duplicate results across pages, a rate limit, an unavailable service, or a pagination failure after earlier pages loaded.
- A deeply nested branch has no fixed maximum depth; collapsed and filtered branches retain explicit draft selections.
- A saved entity is renamed or moved within the same instance, deleted, or inaccessible; inability to retrieve it cannot distinguish deletion from loss of access.
- A selected group's unseen or newly added descendant repositories remain covered by the group rule; the tree need not preload them.
- A repository is explicitly selected while covered by a selected ancestor group; removing that group reveals the repository's surviving explicit selection.
- A subgroup is explicitly selected under another selected group; removing the ancestor keeps the subgroup rule.
- A group with only some known descendants selected shows a partial visual state; unknown descendants do not imply a complete selection.
- The GitLab URL changes to another instance that happens to reuse the same numeric identifiers; prior rules remain associated with the old instance.
- The credential or URL changes while discovery or reconciliation is in progress; results for the previous connection cannot be presented as current results.
- A save fails or a concurrent edit changes the persisted scope; unsaved choices remain available for review, and a conflict does not silently overwrite another saved change.
- A user navigates away with unsaved changes, clears the scope, or removes an unavailable entry.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Scope discovery and adding selections MUST require an existing, active Monitoring Configuration with a GitLab instance URL and configured credential. Retrieving saved scope and removing existing rules MUST remain possible when the credential is absent. Missing prerequisites MUST produce clear, safe feedback.
- **FR-002**: The system MUST discover top-level groups, subgroups at arbitrary nesting depth, and repositories visible to that configuration's credential. Root-level entities MUST be available for interaction before descendant groups are fetched. Expanding a group MUST request only that group's direct children; unrelated branches and unrequested descendants MUST NOT be fetched to enable navigation. The system MUST NOT require materializing the complete hierarchy before navigation is available.
- **FR-003**: The system MUST make every available page of group, subgroup, and repository results reachable. It MUST NOT silently treat a partial page as the complete hierarchy or duplicate an entity when pages overlap.
- **FR-004**: Discovery results MUST contain only normalized navigation and selection metadata, including stable GitLab identifiers, entity type, current name/path where available, parent relationship, and whether more results are available. GitLab credentials, raw provider responses, and unrelated provider data MUST NOT be exposed.
- **FR-005**: The frontend MUST present an expandable and collapsible tree with visually distinct group and repository nodes, arbitrary depth, keyboard-accessible controls, and loading, empty, and recoverable error states for relevant branches.
- **FR-006**: Users MUST be able to select any combination of individual repositories and groups, including multiple of each, and MUST be able to remove any explicit selection or clear the entire scope.
- **FR-007**: A selected group MUST be persisted as an explicit group rule identified by a stable GitLab identifier. It covers that group's descendant hierarchy and projects belonging to the group or its subgroups whenever a future execution resolves the scope; projects merely shared with that hierarchy but owned elsewhere are excluded. It MUST NOT be replaced with a snapshot of currently visible descendant repositories.
- **FR-008**: An individually selected repository MUST be persisted as an explicit repository rule identified by a stable GitLab identifier, regardless of whether a parent group is selected. Effective repository coverage MUST deduplicate a repository covered by both an explicit repository rule and any selected ancestor group, while preserving both explicit rules for editing.
- **FR-009**: Tree selection presentation MUST distinguish an explicitly selected group from a group that is only partially selected because known descendants are explicitly selected. Descendants covered by a selected ancestor MAY be shown as included, but this MUST be visually distinguishable from an explicit rule. Partial display MUST NOT persist an implicit group rule. Unknown or unloaded descendants MUST NOT be treated as proof that all descendants are selected.
- **FR-010**: The Monitoring Configuration MUST persist the distinct group and repository rules and their originating GitLab instance identity. Mutable names and paths MAY be retained for display but MUST NOT be the sole entity identifiers.
- **FR-011**: Scope changes MUST use an explicit save action. Before a successful save, the interface MUST distinguish draft selections from persisted selections; failed saves MUST retain the draft for correction or retry. Navigation away with a changed draft MUST warn the user according to the application's form behavior.
- **FR-012**: The saved scope MUST be retrievable when the Monitoring Configuration is reopened. Reconciliation MUST use stable identifiers against the same GitLab instance, update display metadata for reachable renamed or moved entities, and preserve entries that cannot currently be retrieved.
- **FR-013**: The scope summary MUST separately show selected groups, selected repositories, and unavailable or unresolved persisted entries. Users MUST be able to remove unavailable entries explicitly. Discovery or reconciliation failure MUST NOT silently delete a saved rule.
- **FR-014**: Replacing or removing the GitLab credential MUST NOT automatically remove persisted scope. After credential replacement, selections that are no longer accessible MUST be shown as unavailable; when no credential is configured, saved scope remains visible but cannot be reconciled until access is restored.
- **FR-015**: If the Monitoring Configuration's GitLab URL changes to a different normalized instance identity, existing rules MUST remain associated with their original instance and be flagged as stale. They MUST NOT be interpreted against the new instance, even when identifiers match, or count toward effective coverage for the current instance. The user MAY remove old rules and select rules from the new instance; the system MUST NOT silently transfer or discard old rules.
- **FR-016**: Search or filtering MUST aid navigation without altering draft or persisted rules. Feature 004 requires search over currently available results only; global full-text search of an entire GitLab instance is not required.
- **FR-017**: The system MUST accept an empty saved scope. Saving, clearing, or reconciling scope MUST NOT automatically enable or disable the Monitoring Configuration or start repository work.
- **FR-018**: Discovery, reconciliation, and save failures MUST have safe, actionable categories without credential values or raw provider error bodies. A previous Feature 003 connection-validation success MUST NOT be represented as proof of discovery permission.
- **FR-019**: The backend MUST provide capabilities to retrieve top-level groups, group children and repositories, the saved scope, and to replace the saved explicit scope. The application MUST use normalized hierarchy concepts; GitLab-specific request and response details MUST remain behind the existing connection integration boundary.
- **FR-020**: Concurrent scope edits MUST NOT silently overwrite one another. If the saved scope changes after a user's draft was loaded, a stale save MUST report a conflict and allow the user to reload and review their choices.
- **FR-021**: Automated tests MUST cover top-level and nested discovery, repositories, pagination, every selection combination, partial selection, deselection, persistence and reload, unavailable entities, credential and URL changes, deduplication, errors, loading and empty states, and search/filter preservation. Normal automated tests MUST use controlled GitLab responses rather than a live GitLab instance.
- **FR-022**: This feature MUST NOT schedule or perform mining, clone repositories, process commits, create findings or execution history, build an execution dashboard, or add authentication or authorization.

### Key Entities *(include if feature involves data)*

- **Monitoring Configuration**: Existing configuration that owns a GitLab URL, credential status, and one editable mining scope; its lifecycle and enabled state remain independent of scope editing.
- **GitLab hierarchy entity**: A currently discoverable group, subgroup, or repository identified by a stable GitLab identifier within one instance, with a type, parent relationship, and descriptive display metadata.
- **Scope rule**: An explicit user selection of a group or repository, identified by entity type, stable identifier, and originating instance identity. A group rule represents future descendant coverage; a repository rule represents one repository.
- **Persisted scope**: The saved set of explicit scope rules, including its change state for safe concurrent editing. An empty set is valid.
- **Scope reconciliation state**: The current assessment of each persisted rule as accessible, unavailable/unresolved, or stale because it belongs to another GitLab instance. This state does not erase the underlying rule.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Using only visible application controls, a user can open scope configuration, browse the hierarchy, expand at least one nested group, select at least one group or repository, review the selected-scope summary, and save successfully. A frontend end-to-end or integration-style test with representative mocked GitLab hierarchy data MUST cover this complete workflow. Formal usability timing and participant-completion rates are future product metrics, not Feature 004 acceptance criteria.
- **SC-002**: In a deterministic test hierarchy of at least 1,000 entities distributed across multiple root groups and nested branches, the initial load retrieves only root-level entities and makes them interactive before any descendants are fetched. Expanding one group requests only that group's direct children; other branches remain unloaded until expanded. Every page of the requested node's direct children is reachable without loading unrequested descendant pages.
- **SC-003**: Across all defined selection and deselection scenarios, 100% of saved scopes restore the same explicit group and repository rules; a covered repository appears only once in effective coverage.
- **SC-004**: In 100% of tested deletion, lost-access, credential-change, and instance-change scenarios, persisted selections remain visible until explicitly removed, and no old-instance identifier is treated as a selection from the new instance.
- **SC-005**: In 100% of tested loading, empty, and failure scenarios, users receive a discernible state and can continue using unaffected tree branches and the saved-scope summary.
- **SC-006**: In 100% of tested search, filter, collapse, and reopen scenarios, navigation changes do not alter the saved selection without an explicit successful save.

## Assumptions

- Feature 003 provides the existing GitLab URL, encrypted credential, and connection integration boundary. Basic connection validation may succeed even when discovery permissions are insufficient.
- A GitLab entity's stable identifier is meaningful only together with the normalized identity of its GitLab instance. A URL change that normalizes to the same instance identity does not make scope stale.
- An unavailable selection means it could not currently be retrieved; the interface does not claim whether it was deleted or access was revoked.
- Search initially covers loaded or otherwise currently available results. The implementation plan may add provider-backed search without changing selection semantics.
- This feature records future mining intent. Later execution features will resolve effective repositories and define execution-time treatment of unavailable rules.
