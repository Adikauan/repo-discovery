# Policy-Sourced Mining Requirements Checklist

**Purpose**: Reviewer checklist for final Policy-sourced mining behavior. Existing checkbox states are preserved; this file remains reviewer-owned.
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [ ] CHK001 Does Scope select only Groups and repositories, with no mining-branch configuration?
- [ ] CHK002 Does Policy own the branch and allowed authors for every effective repository?
- [ ] CHK003 Do current repositories dynamically resolved under Groups appear in Policy?
- [ ] CHK004 Does every effective repository require at least one Policy before execution?
- [ ] CHK005 Does a newly discovered Group repository block execution until Policy is configured?

## Requirement Clarity

- [ ] CHK006 Is it explicit that no missing/unavailable Policy branch can fall back to GitLab `default_branch`?
- [ ] CHK007 Are multiple Repository + Branch Policies and their independent execution state defined?
- [ ] CHK008 Are Feature 014 Group author Policies explicitly inactive for new runs while old snapshots remain historical?

## Requirement Consistency

- [ ] CHK009 Do manual and scheduled execution use the same effective Scope, Policy completeness, and target resolver?
- [ ] CHK010 Do checkpoint, baseline, Finding, authorization, and snapshot all use the actual Policy branch?
- [ ] CHK011 Does the `dev-larah` regression prove Policy alone yields the mining target without Scope branch data?

## Edge Case Coverage

- [ ] CHK012 Is obsolete Scope target-rule storage removed without converting rows or damaging unrelated configuration?
- [ ] CHK013 Are incomplete coverage, provider failure, unavailable branches, and Group membership changes covered safely?
