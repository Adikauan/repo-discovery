# Requirements Quality Checklist: Mining Findings

**Purpose**: Review whether Feature 010's finding, checkpoint, API, and dashboard requirements are complete, clear, consistent, and verifiable.
**Created**: 2026-09-30
**Feature**: [spec.md](../spec.md)

**Note**: This custom checklist is a reviewer-owned requirements-quality review artifact.
**Review Ownership**: Only the reviewer may mark these items complete.

## Requirement completeness

- [ ] CHK001 [Completeness] Does the configuration requirement define how the allowed email list is created, edited, validated, bounded, and captured in new executions? (FR-004–FR-006)
- [ ] CHK002 [Completeness] Does the snapshot requirement clearly cover both manual and scheduled executions while keeping credentials and policy internals out of public DTOs? (FR-005, FR-024)
- [ ] CHK003 [Completeness] Are baseline, incremental range, branch identity, checkpoint advancement, and historical rewrite behavior all specified? (FR-009–FR-013)
- [ ] CHK004 [Completeness] Are the exact Finding fields needed to explain the initial rule defined without requiring irrelevant file/line data? (FR-001–FR-002, FR-019)
- [ ] CHK005 [Completeness] Do read requirements specify execution scope, repository scope, detail lookup, filtering, deterministic ordering, and normalized not-found behavior? (FR-020–FR-021)

## Requirement clarity

- [ ] CHK006 [Clarity] Is “valid email” defined consistently for configured policy and provider commit identity, including trim, Unicode case-folding, and malformed values? (FR-004, FR-006–FR-007)
- [ ] CHK007 [Clarity] Is the empty allowlist outcome unambiguous for first-baseline and later incremental executions? (FR-007, FR-009–FR-010)
- [ ] CHK008 [Clarity] Is “inspect each commit exactly once” bounded to the checkpoint-to-HEAD range and stable commit hash, including duplicate provider page records? (FR-010, FR-015, FR-017)
- [ ] CHK009 [Clarity] Is the range-overflow outcome measurable, including the configured range, safe error code, no partial findings, and unchanged checkpoint? (FR-015)
- [ ] CHK010 [Clarity] Are missing and malformed author email identity states distinct, and is the non-retention of malformed raw input explicit? (FR-007, FR-019)

## Requirement consistency

- [ ] CHK011 [Consistency] Do the first-baseline and empty-allowlist rules agree that pre-baseline commits do not create findings? (FR-007, FR-009)
- [ ] CHK012 [Consistency] Do checkpoint advancement, repository success, Finding persistence, and both finding counters share one consistent success boundary? (FR-011, FR-016–FR-018)
- [ ] CHK013 [Consistency] Are finding immutability and no-triage constraints consistent across APIs, dashboard, and history requirements? (FR-003, FR-020–FR-023)
- [ ] CHK014 [Consistency] Are manual and scheduled executions explicitly required to use the same rule and checkpoint semantics? (FR-005, FR-024)

## Scenario and edge coverage

- [ ] CHK015 [Coverage] Are missing, whitespace-only, malformed, duplicate, and case-variant author emails covered by clear outcomes? (FR-006–FR-007)
- [ ] CHK016 [Coverage] Do repository-level provider/rule/persistence failures preserve the old checkpoint and allow unrelated repositories to continue? (FR-011, FR-016)
- [ ] CHK017 [Coverage] Does the history-rewrite requirement distinguish unreachable checkpoints from valid empty commit ranges and prohibit silent reset? (FR-013)
- [ ] CHK018 [Coverage] Does the API requirement explain how nested repository ownership is validated against the requested execution? (FR-001, FR-020–FR-021)
- [ ] CHK019 [Coverage] Does the dashboard requirement distinguish zero persisted findings from loading, unavailable data, and API failure? (FR-018, FR-022)

## Security, privacy, and acceptance quality

- [ ] CHK020 [Security] Are every finding field and API/log exclusion explicit enough to prevent credentials, raw provider payloads, malformed raw emails, or internal exceptions from escaping? (FR-007, FR-019, FR-026)
- [ ] CHK021 [Privacy] Is the visibility and retention intent for author email and optional author name clear enough for users reviewing findings? (FR-002, FR-019, FR-022, FR-026)
- [ ] CHK022 [Measurability] Can finding counters be objectively reconciled to persisted Finding rows for both repository and execution? (FR-018, SC-004)
- [ ] CHK023 [Measurability] Do success criteria make the bounded-range, idempotency, rollback, and historical-policy outcomes objectively verifiable? (SC-001–SC-007)
- [ ] CHK024 [Dependencies] Are Feature 006 snapshot/lifecycle, Feature 008 rule/checkpoint pipeline, Feature 009 scheduled execution, and Feature 007 dashboard responsibilities clearly separated? (FR-005, FR-008, FR-024, FR-022)

## Notes

- These items evaluate requirement quality, not implementation status.
- Keep all markers unchecked until reviewer evaluation.
- See [plan.md](../plan.md), [data-model.md](../data-model.md), and [contracts](../contracts/) for design details.
