# GitLab Candidate Validation Contract

This additive, non-persisting operation supports create mode before a Monitoring Configuration ID exists. It reuses the existing GitLab connection abstraction; it does not browse repositories or change provider behavior.

## Request

`POST /api/v1/gitlab-connections/validate-candidate`

```json
{
  "gitlab_url": "https://gitlab.example.com",
  "token": "<transient candidate token>"
}
```

The URL and token are transient request values. The server validates the URL using current application rules and calls the existing GitLab connection client. The operation performs no configuration, credential, scope, schedule, execution, or policy reads/writes.

## Successful transport response

```json
{
  "state": "validated",
  "result": "success",
  "message": "Connection validated.",
  "checked_at": "2026-09-30T12:00:00Z"
}
```

For provider-reported invalid credentials or inaccessible instances, return a normalized failed state/result and safe application message using the existing validation result vocabulary. Invalid URL/shape uses existing Problem Details field-validation conventions. Provider exceptions must be mapped to safe errors; raw provider bodies, exception text, headers, and secrets are not returned.

## Security and persistence requirements

- Never return the token or include it in errors, logs, telemetry, or response metadata.
- Do not persist the candidate token or validation result.
- Reuse the existing server-side GitLab connection client; never call GitLab from the browser.
- After successful prevalidation, the existing configuration create operation persists only configuration values; the existing secure credential endpoint stores the token encrypted, followed by the existing saved-credential validation operation.
- On post-create failure, the frontend retains the returned configuration ID and retries remaining operations without creating another configuration.

## Compatibility

Existing Monitoring Configuration create/update, GitLab credential, credential validation, scope, policy, and scheduling contracts remain unchanged. This is an additive validation contract only.
