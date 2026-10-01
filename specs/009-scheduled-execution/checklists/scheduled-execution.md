# Reliability Checklist: Scheduled Execution

**Purpose**: Reviewer checklist for recurrence, dispatch safety, persistence, and operational behavior
**Created**: 2026-09-30
**Feature**: [spec.md](../spec.md)

**Note**: This custom checklist is reviewer-owned. Items remain unchecked until a reviewer evaluates the requirements; `[x]` denotes requirements review, not implementation completion.

## Recurrence and eligibility

- [ ] CHK001 Does the scheduler delegate daily, weekly, monthly, timezone, monthly clamp, and DST calculations to the Feature 005 authority?
- [ ] CHK002 Are both Monitoring Configuration and schedule enabled states required at dispatch time?
- [ ] CHK003 Are disabled, retired, deleted, or version-changed candidates prevented from creating a Mining Execution?
- [ ] CHK004 Does startup establish a future-only baseline and exclude missed offline occurrences?
- [ ] CHK005 Is occurrence due handling deterministic at equality and scan-boundary instants?

## Execution lifecycle and concurrency

- [ ] CHK006 Do manual and scheduled creation use the same MiningExecution lifecycle and Feature 008 pipeline?
- [ ] CHK007 Does the existing Feature 006 active-configuration guard remain the sole active execution rule?
- [ ] CHK008 Does a non-stale active manual execution cause the scheduled occurrence to be skipped without queuing?
- [ ] CHK009 Does a scheduled winner cause the manual loser to receive the existing normalized conflict?
- [ ] CHK010 Can only the winning execution enter repository mining?
- [ ] CHK011 Does a duplicate trigger remain idempotent after completion/failure and after process restart?
- [ ] CHK012 Does an active scheduled execution survive restart without automatic re-invocation?
- [ ] CHK013 Are Feature 006 stale reconciliation and interruption behavior reused without a second recovery model?

## Historical integrity and security

- [ ] CHK014 Does the immutable snapshot capture the exact schedule occurrence/version and current configuration/scope at acceptance?
- [ ] CHK015 Are schedule edits and deletion prevented from rewriting prior execution snapshots/results?
- [ ] CHK016 Are credentials excluded from schedule trigger context, MiningExecution occurrence key, and scheduler logs?
- [ ] CHK017 Are provider errors and runtime details kept within existing safe error/logging conventions?
- [ ] CHK018 Are failed and partially completed mining outcomes visible through ordinary execution history and repository results?

## Persistence and operation

- [ ] CHK019 Does the PostgreSQL uniqueness constraint prevent two MiningExecutions for the same configuration and scheduled occurrence?
- [ ] CHK020 Does the migration preserve existing rows with a null occurrence identity and preserve execution retention?
- [ ] CHK021 Are dispatch transactions committed before repository mining/network activity begins?
- [ ] CHK022 Is scheduler startup/shutdown wired to the application lifespan without adding a new dependency or an unbounded task per schedule?
- [ ] CHK023 Is exactly one scheduler-enabled application instance per deployment documented and operationally enforced by deployment configuration?
- [ ] CHK024 Is process-local scheduled worker concurrency bounded and is full capacity handled without a queue or delayed dispatch?
- [ ] CHK025 Are scheduler outcomes observable without secret or provider detail leakage?
- [ ] CHK026 Are daily/weekly/monthly, restart, edit/removal, duplicate, race, failed, and partial execution cases covered deterministically?
- [ ] CHK027 Are PostgreSQL uniqueness and manual/scheduled race results reported only when those tests actually execute against PostgreSQL?

## Scope boundaries

- [ ] CHK028 Does this feature avoid a second mining pipeline, scheduled-run entity, public mutation API, distributed scheduler, work backlog, or leader election?
- [ ] CHK029 Does this feature avoid catch-up, automatic retry/recovery, UI redesign, real-time transport, AI, findings analysis, and new mining rules?

## Notes

- Review the consistency between [spec.md](../spec.md), [plan.md](../plan.md), [data-model.md](../data-model.md), [contracts/scheduler-dispatch.md](../contracts/scheduler-dispatch.md), and [tasks.md](../tasks.md).
- PostgreSQL-dependent criteria require a real PostgreSQL validation environment.
