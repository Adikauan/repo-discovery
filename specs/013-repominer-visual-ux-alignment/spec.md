# Feature Specification: RepoMiner Visual & UX Alignment

**Feature Branch**: `013-repominer-visual-ux-alignment`  
**Created**: 2026-09-30  
**Status**: Draft  
**Input**: User description: "Create Feature 013 - RepoMiner Visual & UX Alignment. Align the existing RepoMiner web application with the approved UX direction while preserving behavior from Features 001-012."

## User Scenarios & Testing

### User Story 1 - Navigate a coherent application (Priority: P1)

As a RepoMiner user, I want a consistent application shell and navigation, so I can find the existing configuration, execution, and settings workflows from any page.

**Why this priority**: The shell establishes the visual and navigational structure used by every other screen.

**Independent Test**: Navigate between Home, Monitoring Configurations, Executions, and Settings at desktop and narrow viewport widths; verify current-page indication and existing routes remain usable.

**Acceptance Scenarios**:

1. **Given** the user opens any supported application page, **When** the page is displayed, **Then** it uses the persistent left navigation, product identity, main content area, consistent page heading hierarchy, spacing, and content width.
2. **Given** the user views primary navigation, **When** they inspect its items, **Then** it includes only Home, Monitoring Configurations, Executions, and Settings, and each item leads to existing functionality.
3. **Given** the viewport narrows, **When** the shell is displayed, **Then** navigation and page content remain usable without introducing a separate mobile application or changing route behavior.
4. **Given** Home is opened, **When** dashboard summaries are shown, **Then** every displayed metric or chart is derived from existing execution/Finding data; unavailable data is omitted or explicitly marked unavailable, and no unsupported category or fabricated value appears.

---

### User Story 2 - Create and maintain a Monitoring Configuration (Priority: P1)

As a configuration owner, I want existing configuration tasks organized into a clear five-step flow, so I can review general settings, GitLab access, scope, author settings, and scheduling in a predictable order.

**Why this priority**: Configuration is the source of scope and behavior for existing manual and scheduled mining; visual restructuring must keep those established workflows reliable.

**Independent Test**: Create and edit a configuration using the five existing functional areas, including GitLab validation, hierarchical scope selection, allowed commit authors, and scheduling; verify saved behavior and historical execution semantics remain unchanged.

**Acceptance Scenarios**:

1. **Given** the user creates or edits a configuration, **When** the wizard is displayed, **Then** its steps are General, GitLab connection, Scope, Authors, and Scheduling.
2. **Given** the user edits General or GitLab connection details, **When** they save, **Then** existing validation, credential secrecy, and configuration persistence behavior remain unchanged.
3. **Given** the user selects scope, **When** they browse groups and repositories, **Then** existing search, hierarchy, expansion, multiple selection, selected-scope summary, unavailable historical-selection handling, and dynamic group semantics are preserved.
4. **Given** the user opens Authors, **When** they edit allowed commit authors, **Then** the existing global allowed-author configuration remains functional and retains Feature 010 semantics; any future repository/branch policy controls are clearly unavailable and do not save or affect mining.
5. **Given** the user edits Scheduling, **When** they configure or remove a schedule, **Then** recurrence, timezone, next-occurrence preview, DST, enablement, and removal behavior remain unchanged.
6. **Given** a configuration already exists, **When** the user views its details, **Then** its general settings, GitLab connection, scope, authors, schedule, and existing execution actions/history are presented in clearly grouped sections without adding business actions.

---

### User Story 3 - Review execution history and results (Priority: P1)

As a RepoMiner user, I want execution history, repository results, Findings, and commit changes presented consistently, so I can understand mining outcomes without changing their meaning.

**Why this priority**: Execution results are the product's primary output and must remain clear and trustworthy through the redesign.

**Independent Test**: Review manual and scheduled execution rows, open execution details, inspect repository results and Findings, and open a commit diff; verify statuses, historical context, counts, safe errors, and diff semantics match existing behavior.

**Acceptance Scenarios**:

1. **Given** the user opens Executions, **When** the execution list is shown, **Then** existing filters and manual-execution actions remain available and columns present supported execution, configuration, status, trigger, timestamps, duration, and Finding count without fabricating data.
2. **Given** the user opens an execution, **When** its details are displayed, **Then** the existing Overview, Repositories, Findings, and Details tabs remain available with the same historical snapshot, counters, completion meaning, repository states, safe errors, and Findings.
3. **Given** an Unauthorized Commit Author Finding supports commit inspection, **When** the user opens its changes, **Then** the existing on-demand, Finding-ID-based dialog displays commit metadata, file sidebar, split Before/After lines, binary/large/truncated states, and safe loading/error/retry behavior.
4. **Given** execution or repository data is loading, empty, or unavailable due to an error, **When** the state is shown, **Then** the UI communicates it consistently and safely without exposing raw provider/backend errors.

---

### User Story 4 - Use consistent presentation across product data (Priority: P2)

As a RepoMiner user, I want lists, forms, cards, statuses, and actions to follow a shared visual language, so that existing workflows remain readable and predictable across pages.

**Why this priority**: Shared presentation improves comprehension and reduces visual inconsistency after the primary routes and results are organized.

**Independent Test**: Compare Monitoring Configurations, Executions, repository results, Findings, forms, and dialogs for consistent hierarchy, table behavior, status meaning, and accessible controls.

**Acceptance Scenarios**:

1. **Given** a page contains a list or table, **When** it is displayed, **Then** headers, row heights, status badges, action placement, overflow, and empty/loading/error states follow a consistent presentation while retaining semantic table structure.
2. **Given** the application displays existing statuses, **When** a status is communicated, **Then** pending, running, completed, partially completed, failed, enabled, and disabled have consistent labels and visual semantics, with meaning not conveyed by color alone.
3. **Given** the user encounters an icon-only action, **When** it is presented, **Then** it has an accessible name, keyboard behavior, and a tooltip where appropriate; existing textual actions are not mechanically replaced.
4. **Given** the user views forms, tables, cards, or dialogs on desktop, tablet, or narrow viewport, **When** content exceeds available space, **Then** it wraps or scrolls within the relevant region and does not cause uncontrolled page overflow.

### Edge Cases

- Home has no executions or Findings: display honest empty states and zero values only when supported by the available data.
- An existing API does not provide a proposed dashboard metric: omit it or show an explicitly unavailable placeholder; do not introduce fabricated values.
- A saved configuration contains historical scope items that are currently unavailable: preserve the existing unavailable-selection behavior.
- A GitLab credential is stored: never reveal it while presenting or editing the connection.
- A user leaves or returns to a wizard step with validation errors: retain existing validation and save semantics; visual restructuring must not silently discard or mutate configuration data.
- The user encounters an empty list, partial execution, failed repository, missing Finding diff, binary file, oversized diff, or truncated result: retain existing truthful state and safe error behavior.
- At a narrow viewport, tables and split diff content may scroll within their containers; the split diff must not change to unified mode.
- Reference images may be absent during specification creation and will be added later; their absence does not alter existing application behavior or authorize speculative features.

## Requirements

### Functional Requirements

- **FR-001**: The application MUST present a consistent shell with product identity, persistent primary navigation, a main content area, consistent page-heading hierarchy, deliberate content width, spacing, cards, and actions.
- **FR-002**: Primary navigation MUST expose only existing Home, Monitoring Configurations, Executions, and Settings routes; it MUST identify the current route and MUST NOT add unsupported modules.
- **FR-003**: Home MUST replace placeholder-oriented content with summaries derived only from currently available execution and Finding data. It MAY display execution counts/status, supported repository totals, Finding counts, recent executions, and execution history/distribution only when derivable from existing data. It MUST omit unsupported metrics or identify them as unavailable and MUST NOT fabricate analytics.
- **FR-004**: The Monitoring Configurations list MUST present existing configuration name, description, GitLab URL, enabled state, schedule summary when configured, updated date, and existing actions in a readable table-oriented layout with the existing search/filter behavior and a clear New Configuration action.
- **FR-005**: Configuration create/edit MUST present the existing functionality in the ordered steps General, GitLab connection, Scope, Authors, and Scheduling.
- **FR-006**: General and GitLab connection steps MUST preserve existing fields, validation, credential validation feedback, credential secrecy, save behavior, and persistence semantics.
- **FR-007**: The Scope step MUST preserve hierarchical group/repository browsing, search, expansion, multiple selection, selected-scope summary, unavailable historical selections, and Feature 004 dynamic group semantics.
- **FR-008**: The Authors step MUST preserve the existing global allowed-commit-author editor and Feature 010 semantics. Any visual affordance for future repository/branch policies MUST be disabled or explicitly unavailable and MUST NOT persist, affect execution snapshots, or alter mining behavior.
- **FR-009**: The Authors step MUST NOT implement branch discovery for policy editing, repository/group-specific policies, branch-specific authorization, new policy persistence, new snapshot policy schema, or new Unauthorized Commit Author semantics.
- **FR-010**: The Scheduling step MUST preserve existing recurrence, local time, IANA timezone, enable/disable, next-occurrence preview, DST, and schedule-removal behavior.
- **FR-011**: Configuration details/edit MUST group existing general, GitLab, scope, author, schedule, and execution/history information into clear sections and MUST NOT introduce business actions.
- **FR-012**: The Executions page MUST retain existing filters and manual-execution behavior and present available execution, configuration, status, trigger, created/started/completed timestamps, duration, and Finding count without fabricating values.
- **FR-013**: Execution Details MUST preserve the existing Overview, Repositories, Findings, and Details tabs and their current lifecycle, timestamps, snapshot, counters, completion meaning, repository data, Finding data, and safe errors.
- **FR-014**: Repository results and Findings MUST present only existing persisted data, including supported Unauthorized Commit Author information and the existing commit-diff action.
- **FR-015**: The Commit Diff dialog MUST preserve Feature 011/012 behavior: on-demand Finding-based lookup, commit metadata, changed-file sidebar, selected-file state, split Before/After view and independent line numbers, hunk and change semantics, loading/error/retry, completeness, binary, oversized, and truncation indicators, security, and accessibility.
- **FR-016**: Shared presentation MUST standardize existing table structure, readable row height, headings, card/form spacing, action placement, status indicators, and loading/empty/error states across affected screens, while retaining semantic and keyboard-accessible controls.
- **FR-017**: Statuses MUST retain existing business meanings and use consistent labels and visual semantics; status MUST be communicated by text or accessible name as well as color.
- **FR-018**: The application MUST remain usable on desktop and reasonable tablet/narrow viewport sizes. Navigation, wizard, cards, tables, and dialogs MUST stay within the viewport or use controlled local scrolling; split diff sides MUST remain side by side.
- **FR-019**: Feature 013 MUST preserve compatibility of existing public API contracts. Existing fields, meanings, routes, and write semantics MUST NOT be removed, renamed, reinterpreted, or made incompatible. Additive read-only projections are allowed only when required to expose already-existing data for the redesigned UI. Visual refactoring MUST NOT change CRUD behavior, GitLab credential handling, scope semantics, scheduling semantics, execution lifecycle, repository mining, Finding/checkpoint behavior, historical snapshots, or diff retrieval/interpretation.
- **FR-020**: Feature 013 MAY add minimal additive read-only projections or endpoints when existing APIs cannot expose already-existing data required by the approved visual design without inefficient or misleading client-side reconstruction. Such additions MUST expose existing data only, remain read-only and backwards-compatible, avoid new persistence and domain behavior, and remain narrowly scoped to Feature 013 presentation needs. The only currently approved additions are the Home summary, configuration `scheduleSummary`, and execution `findingCount` projections; no other backend contract expansion is approved.
- **FR-021**: The application MUST NOT add word/keyword/table discovery, semantic or code-pattern analysis, AI/LLM/SLM, code-quality scoring, generalized analytics, mining rules, Finding types, branch-author policy behavior, review/triage, or unsupported report generation.
- **FR-022**: Automated accessibility coverage MUST be updated for affected shell, forms, wizard, tables, dialogs, and icon actions; keyboard navigation, visible focus, form labels/error association, table semantics, dialog focus management, contrast, and non-color status communication MUST be preserved or improved.
- **FR-023**: Visual validation MUST compare the implemented affected screens with the reference images added under `specs/013-repominer-visual-ux-alignment/references/`, using them as directional guidance for proportions, hierarchy, spacing, composition, and responsive presentation. Functional requirements and Features 001-012 behavior take precedence over decorative reference details.

### Key Entities

- **Monitoring Configuration**: Existing configuration with its general data, GitLab connection, scope, global allowed authors, and schedule; Feature 013 changes its presentation only.
- **Mining Execution**: Existing manual or scheduled execution with lifecycle, trigger, snapshot, counters, repositories, Findings, and existing details.
- **Repository Execution**: Existing repository-level result belonging to a Mining Execution, including its status, summary, timestamps, Finding count, and safe error.
- **Finding**: Existing immutable historical mining result, including supported Unauthorized Commit Author context and commit-diff access.
- **Visual Reference**: An image added after specification creation to guide visual composition only; it is not a source of new functional behavior.

## Success Criteria

### Measurable Outcomes

- **SC-001**: All existing primary routes are reachable through the four supported navigation items, and the selected route is identifiable to visual and assistive-technology users.
- **SC-002**: Every Home metric/chart shown in the interface can be traced to currently available persisted execution or Finding data; unsupported metrics are omitted or labeled unavailable, with no fabricated values.
- **SC-003**: Users can complete existing configuration create/edit workflows across the five named steps, and saved scope, allowed authors, schedule, and credentials retain their prior functional semantics.
- **SC-004**: Execution list, details, repository results, Findings, and commit diff expose the same available historical values and supported actions as before visual alignment.
- **SC-005**: Affected tables, forms, cards, statuses, actions, and asynchronous states use consistent presentation and preserve semantic structure, accessible names, keyboard operation, visible focus, and non-color status meaning.
- **SC-006**: At representative desktop, tablet, and narrow viewport sizes, navigation and content remain usable without uncontrolled page overflow; tables and split diff use contained scrolling where necessary.
- **SC-007**: The visual redesign adds no persistence/migrations and introduces no unsupported analysis, mining, Finding, policy, review, or scheduling capability.
- **SC-008**: Manual visual review covers every reference image supplied for the application shell, Home, configuration list/wizard/details, scheduling, execution list/details, Findings, and commit diff; any intentional differences are documented and existing behavior takes precedence.

## Assumptions

- Existing routes, API clients, query/state behavior, components, and tests are reused; working business logic is not rewritten solely to achieve visual consistency.
- The primary target is desktop web, with reasonable tablet and narrow viewport support rather than a separate mobile product.
- The current global allowed-author list remains the only active author policy during Feature 013. Repository/branch policy configuration is deferred to a subsequent functional feature.
- Home summaries use existing list/detail data when adequate. Planning may justify a minimal read-only aggregation contract only if existing APIs cannot present an explicitly required, derivable metric; no new persistence is introduced.
- Reference images will be added by the user after initial specification creation. Until then, visual details are described behaviorally and may be refined during planning without changing the functional scope.
- Existing API contracts remain backwards-compatible. Only the three additive read-only projections explicitly listed in FR-020 are currently approved; reuse an existing endpoint/DTO when it already provides the required information cleanly, and justify each projection against inefficient or misleading alternatives.

## Out of Scope

- New mining functionality, MiningExecution/RepositoryExecution/Finding semantics, scheduler behavior, GitLab scope rules, credential behavior, checkpoint behavior, or diff retrieval semantics.
- Repository-, group-, or branch-specific author policy persistence or execution behavior.
- Word discovery, keyword discovery, table discovery, code-pattern or semantic analysis, AI/LLM/SLM, code-quality scoring, or generalized analytics.
- New Finding types, code review, Finding triage, unsupported report generation, and new domain persistence for visual redesign.
- Rebuilding the frontend, replacing the existing routing/API/query architecture, introducing another UI framework, or creating a separate mobile application.
