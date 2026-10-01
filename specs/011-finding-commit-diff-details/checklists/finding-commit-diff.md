# UX, API, and Security Requirements Checklist: Finding Commit Diff Details

**Purpose**: Review whether Feature 011 requirements are clear, complete, consistent, measurable, and ready for implementation.
**Created**: 2026-09-30
**Feature**: [spec.md](../spec.md)

**Note**: This custom checklist is based on Feature 011 requirements.
**Review Ownership**: This is a reviewer-owned requirements-quality artifact. Only the reviewer may approve items.
**Marker Semantics**: `[x]` means the criterion was reviewed and satisfied for requirements quality, not that implementation is complete.

## Requirement completeness and clarity

- [ ] CHK001 Are the supported Finding types and conditions for showing the diff action explicitly defined? [Completeness, Spec §FR-001]
- [ ] CHK002 Are all required persisted commit metadata fields and their nullable behavior clear? [Clarity, Spec §FR-002]
- [ ] CHK003 Are provider-derived change types and unknown-type behavior unambiguous for add, delete, modify, and rename? [Clarity, Spec §FR-003]
- [ ] CHK004 Are added, removed, and context line semantics defined for provider-returned unified diffs? [Completeness, Spec §FR-004]
- [ ] CHK005 Are the historical Finding, repository, commit, and instance sources clearly identified as authoritative? [Consistency, Spec §FR-005–FR-008]
- [ ] CHK006 Are unsupported Finding and missing commit/repository identity outcomes distinguished? [Coverage, Spec §FR-005, FR-010]

## API and security requirements

- [ ] CHK007 Are the diff route, response fields, and safe error codes consistent across spec, contract, and plan? [Consistency, Spec §FR-010, FR-019]
- [ ] CHK008 Is it explicit that no client-supplied project, commit, URL, or token may affect provider lookup? [Security, Spec §FR-005, FR-009]
- [ ] CHK009 Are credential unavailability and GitLab instance mismatch behaviors clear while preserving Finding availability? [Coverage, Spec §FR-008–FR-010]
- [ ] CHK010 Are all sensitive provider, credential, exception, and persistence details excluded from response and logs? [Security, Spec §FR-009–FR-010]
- [ ] CHK011 Is provider-side incomplete file pagination distinguished from application-side file/payload truncation? [Clarity, Spec §FR-011–FR-012]
- [ ] CHK012 Are file-count, per-file byte, and total byte limits explicit and measurable? [Measurability, Spec §FR-011]

## UX, accessibility, and edge coverage

- [ ] CHK013 Are binary/no-text, collapsed, too-large, and unknown empty-diff states distinguishable without unsupported claims? [Clarity, Spec §FR-012–FR-013]
- [ ] CHK014 Are request timing and duplicate-request behavior clear, including that listing Findings does not request diffs? [Completeness, Spec §FR-014]
- [ ] CHK015 Are dialog title, focus entry/return, keyboard close, file selection, loading, and error announcements covered? [Accessibility, Spec §FR-015]
- [ ] CHK016 Are narrow-screen behavior and long-line handling specified sufficiently to avoid application-wide overflow? [Coverage, Spec §FR-016]
- [ ] CHK017 Are retry, close-during-load, repeated-open, and partial-file-error scenarios addressed? [Edge Case, Spec §Edge Cases]
- [ ] CHK018 Are explicit exclusions consistent with the scope boundaries and existing detection behavior? [Consistency, Spec §FR-018]
- [ ] CHK019 Can the success criteria objectively establish on-demand-only retrieval, safe bounds, honesty about partial data, and retained Finding availability? [Measurability, Spec §SC-001–SC-007]

## Notes

- Leave every item unchecked until reviewer review; this command does not approve requirements.
- Items assess the quality of the requirements, not implementation behavior.
- `$speckit-implement` must not change reviewer-owned checklist markers.
