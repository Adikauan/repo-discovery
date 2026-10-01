# Repository Mining and Analytics Platform

## GitLab connection credentials

Feature 003 stores one encrypted GitLab token per Monitoring Configuration. Generate a Fernet key locally with `cryptography.fernet.Fernet.generate_key()` and place it only in the ignored `.env` file as `GITLAB_CREDENTIAL_ENCRYPTION_KEYS`. For rotation, list the new encryption key first and retain older decrypt-only keys until stored credentials have been re-encrypted. Back up keys separately from the database; losing every configured key makes stored credentials unrecoverable.

Tokens are opaque, must be nonblank, and are limited to 2048 UTF-8 bytes. Use the narrowest permission supporting `GET /api/v4/user`—commonly `read_user`. Validation checks reachability, authentication, and that endpoint only; it does not certify repository-discovery permissions.

The GitLab HTTP client uses configurable connect/read/write/pool defaults of 5/10/5/5 seconds and never follows redirects or retries automatically. See [the Feature 003 quickstart](specs/003-gitlab-connection/quickstart.md) for setup and verification.

## Scheduled execution deployment mode

Feature 009 supports one scheduler runner per deployment. For local development with a single backend process, `SCHEDULER_ENABLED` defaults to `true`. In a deployment with multiple API worker processes, configure exactly one designated process with `SCHEDULER_ENABLED=true` and set it to `false` for every additional API worker. Only the enabled process starts the polling runner from FastAPI lifespan. This is an operational deployment constraint: Feature 009 does not coordinate multiple scheduler processes, elect a leader, or provide cross-process locking. Do not run more than one scheduler-enabled process for the same deployment.
