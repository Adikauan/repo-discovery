# Allowed Author Email Configuration and Execution Snapshot Contract

## Monitoring Configuration write/read contract

Extend the existing `POST /api/v1/monitoring-configurations` and `PUT /api/v1/monitoring-configurations/{id}` JSON bodies with:

```json
{
  "allowedAuthorEmails": ["developer@example.com"]
}
```

The field is optional on legacy clients and defaults to an empty list. Responses may include the persisted configuration value because it is editable policy, but it must not include credentials. Create idempotency fingerprints include the normalized list. Update retains required `If-Match`/ETag revision behavior.

Validation:

- Array contains at most 500 entries.
- Each entry is at most 254 characters and must validate as an email.
- Trim surrounding whitespace, Unicode case-fold, deduplicate, then sort normalized values before persistence.
- Invalid entries produce the existing normalized field-validation response and do not partially update configuration.
- Empty list is accepted and means each valid new commit author is unauthorized.

## Execution snapshot behavior

At execution creation, store `allowed_author_emails` as an immutable sorted tuple/value in the existing snapshot. Manual and scheduled execution creation use the same capture method. Missing value in previously persisted snapshots is interpreted as empty. The public `SnapshotResponse` omits this internal rule policy by default. No credentials or provider response data are captured.
