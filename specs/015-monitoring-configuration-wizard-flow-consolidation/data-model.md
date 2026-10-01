# Data Model: Monitoring Configuration Wizard Flow Consolidation

Feature 015 adds no persisted entity or database schema.

## Existing MonitoringConfiguration

The current record remains the authoritative persisted configuration. Existing fields and meanings are unchanged, including name, description, GitLab URL, enabled state, and revision. The existing server create operation continues to receive a complete configuration with URL after candidate validation.

## In-memory create WizardDraft

| Field | Meaning | Lifetime / constraints |
|---|---|---|
| name | General step value | Required by existing configuration validation; held in memory until create succeeds |
| description | General step value | Existing nullable/optional behavior; held in memory until create succeeds |
| gitlabUrl | GitLab Connection candidate URL | Non-secret; retained in memory while moving backward/forward in the create wizard until create succeeds |
| createIdempotencyKey | Stable key for create retry | Held for one wizard attempt and reused on retry through the existing create API |
| configurationId | Identity returned by successful create | Added only after creation; used to resume credential persistence/validation without duplicate create |

This draft is frontend navigation state only. It is not written to PostgreSQL, browser storage, or an API draft store. The candidate URL is retained so backward navigation does not discard an unpersisted field.

### Excluded transient secret

The candidate access token is not part of `WizardDraft`. It is held only transiently by the GitLab credential input while the user validates and submits it. It must not enter local/session storage, URL state, logs, or a longer-lived shared context. It is cleared after submission or explicit discard.

## Existing step state

- **GitLab Connection edit**: persisted URL and configuration ETag; credential state/status comes from the existing safe status API. Raw stored credentials are not returned.
- **Scope**: existing scope draft plus its independent ETag; no semantic or identity changes.
- **Authors**: existing Feature 014 policies and configuration revision/CAS state; no changes.
- **Scheduling**: existing schedule record/draft and stale-write state; no changes.
- **WizardStep**: route-derived presentation state with exactly five labels and an active index; not persisted.

## Relationships and lifecycle

```text
In-memory General WizardDraft
  └── candidate GitLab validation (no persisted configuration)
       └── successful existing MonitoringConfiguration create
            └── persisted credential save + saved credential validation
                 └── existing scope -> author policies -> schedule operations
```

If candidate validation fails, no configuration or credential is stored. If create returns an ID but credential save/validation fails, the connection step retains that ID for retry. Historical executions, snapshots, Findings, and checkpoints are unaffected.
