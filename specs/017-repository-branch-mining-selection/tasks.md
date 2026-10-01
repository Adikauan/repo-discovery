# Tasks: Repository Branch Mining Selection

**Input**: Final Feature 017 artifacts in this directory. The previous Scope TargetBranchRule implementation is obsolete; its completed tasks are superseded by this corrective implementation plan.

## Phase 1 — Domain, persistence, migration

- [x] T001 Add tests for `MiningTarget` identity and complete Policy coverage using stable repository IDs and branch names.
- [x] T002 Implement the derived `MiningTarget` model/resolver from effective repositories plus Repository + Branch Policies; Group policies and Scope branch records must not participate.
- [x] T003 Add/validate PostgreSQL migrations: revision 0010 invalidates unprovable legacy checkpoints and leaves old execution target branches null; revision 0011 drops obsolete Scope target-rule storage without conversion, preserving unrelated policy/configuration/security/scope/schedule/history data.
- [x] T004 Add PostgreSQL migration integration tests proving obsolete target-rule removal, preservation of unrelated rows, and no fabricated Policy conversion.
- [x] T005 Add regression tests showing legacy branchless Group Policy rows remain stored but cannot be written/edited as active policy, resolved for new mining, or copied to new snapshots.

## Phase 2 — Shared effective Scope and Policy contracts

- [x] T006 Extract/reuse one effective-repository projection from `ResolveEffectiveScope` for direct repositories and current selected-Group descendants, deduplicated by GitLab repository ID.
- [x] T007 Extend Policy read contract to expose every effective repository, its direct/Group source metadata, active branch policies, and derived `configured` / `policy_required` status.
- [x] T008 Update Policy mutation and branch-discovery ownership validation to accept only currently effective repositories, including dynamic Group descendants; reject unrelated IDs and all new Group-policy writes.
- [x] T009 Add API tests for direct and Group-derived repository listing, dynamic descendants, branch discovery ownership, policy CRUD, duplicate Repository + Branch rejection, revision conflicts, and safe Problem Details.
- [x] T010 Remove obsolete Target Branch API, client, route, schemas, repository port, active entity, persistence model, and active-contract documentation; retain only explanatory migration notes and the legacy V3 snapshot DTO/reader required for historical reads and safe pending-work rejection.

## Phase 3 — Snapshot, preflight, and shared mining target resolution

- [x] T011 Add snapshot V4 tests for concrete effective repositories and Repository + Branch targets with normalized authors; assert credentials and Group Policies are absent and V1–V3 remain history-readable.
- [x] T012 Implement snapshot V4 and reject pending V3 Scope-target snapshots safely instead of resuming obsolete branch rules.
- [x] T013 Add shared execution-creation preflight tests proving incomplete coverage rejects before a MiningExecution is persisted for both manual and scheduled triggers.
- [x] T014 Inject the same effective-Scope/Policy completeness/target resolver into shared `CreateMiningExecution`; fail the whole request with standard 422/ineligible scheduled outcome if any effective repository lacks a Policy.
- [x] T015 Add resolver tests for direct repository Policy, selected Group descendants, newly discovered descendant becoming `policy_required`, multiple branches, and no partial target set.
- [x] T016 Add the `dev-larah` regression: directly selected repository + Policy branch `dev-larah` resolves to `(repository, dev-larah)` without any Scope branch record or empty target list.
- [x] T017 Update `ProcessMiningExecution` to fan out exclusively from snapshot V4 `MiningTarget` entries; preserve branch-specific baseline/checkpoint, author comparison, RepositoryExecution, Finding, failure isolation, and never read `default_branch` as a fallback.
- [x] T018 Add tests for target branch actually mined when GitLab default is different, multiple Policy branches, unavailable Policy branch safely failing, exact checkpoint isolation, per-branch baseline, Finding branch, and snapshot branch.
- [x] T019 Add manual/scheduled parity tests proving both use the same preflight and exact target set; a new uncovered Group repository blocks both triggers.

## Phase 4 — Frontend Scope and Policy migration

- [x] T020 Remove Scope target-branch controls and API integration from `GitLabScopePage`; retain Group/repository selection, sticky Selected Scope, and all prior Scope semantics.
- [x] T021 Rename user-facing Authors step/page/heading/stepper/breadcrumb/navigation copy to **Policy**, preserving route compatibility where useful.
- [x] T022 Update Policy page to show every effective direct and Group-derived repository once, its configured/Policy required state, and existing Repository + Branch policy editors; do not add a second repository picker.
- [x] T023 Ensure Policy editor branch discovery and mutations use current effective repositories and exclude inactive Group policies from editing and submission.
- [x] T024 Add frontend tests for direct repository and dynamic Group descendant display, Policy required state, branch discovery, multiple policies, duplicate prevention, Group legacy omission, and no Scope branch selector.
- [x] T025 Add user-facing execution validation feedback for incomplete Policy coverage while preserving server validation as authoritative.

## Phase 5 — Cross-cutting regression and validation

- [x] T026 Add/adjust tests confirming Feature 014 branch-specific allowed-author evaluation receives the actual Policy mining branch; historical Feature 014 Group-policy snapshots remain readable and unchanged.
- [x] T027 Verify branch-aware checkpoint identity and baseline behavior after obsolete Scope-rule migration; no checkpoint crosses Repository + Branch identities.
- [x] T028 Run PostgreSQL migration and integration tests with `TEST_DATABASE_URL`; record exact results and targeted checkpoint/Scope-rule sanitation in `quickstart.md`.
- [x] T029 Run backend unit/API/integration suites, including Features 008/009/010/014 and manual/scheduled parity; fix implementation regressions.
- [x] T030 Run frontend component/accessibility tests and production build; fix implementation regressions.
- [x] T031 Review logs, Problem Details, snapshots, and API payloads for credential disclosure; verify no default-branch fallback or obsolete Scope-target path remains.
- [ ] T032 Perform manual Policy/Scope visual validation if an application and references are available; do not mark complete without actual review.
- [x] T033 Run final artifact/code convergence review and complete only implementation tasks with evidence.

## Dependency order

1. T001–T005 establish domain and safe storage transition.
2. T006–T010 establish effective repository projection and API contracts before UI or execution consumers.
3. T011–T019 depend on the shared resolver and snapshot contract; preflight must be in shared creation so manual/scheduled parity is structural.
4. T020–T025 migrate UI only after contract behavior is fixed; T021/T022 are sequential because they share wizard/page files.
5. T026–T033 are final regression, PostgreSQL, accessibility, visual, and convergence validation.

Tasks touching `models.py`, SQLAlchemy repositories, `create_mining_execution.py`, `process_mining_execution.py`, the Policy page, or Scope page are sequential when file ownership overlaps. PostgreSQL tests must use PostgreSQL, never SQLite. Manual visual validation remains open until performed.

## Requirement traceability

- FR-001–FR-005 / SC-001–SC-003: T006–T010, T020–T024.
- FR-006–FR-008 / SC-004: T006–T009, T013–T016, T019, T022, T025.
- FR-009–FR-013 / SC-005–SC-007: T011–T019, T026–T027.
- FR-014–FR-015: T011–T012, T017–T018, T026.
- FR-016–FR-017 / SC-008–SC-009: T003–T005, T010–T012, T023, T028, T031.
- FR-018–FR-023: T003–T005, T013–T019, T025–T033.
