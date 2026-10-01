# Quickstart: GitLab Connection

This feature builds on the existing Feature 002 local PostgreSQL/Compose application.

## Local encryption configuration

1. Install backend dependencies through the repository's documented backend workflow. The implementation adds `cryptography` and makes HTTPX a runtime dependency.
2. Generate a Fernet key locally with `cryptography.fernet.Fernet.generate_key()` and put it only in the ignored local `.env` or a secret manager as `GITLAB_CREDENTIAL_ENCRYPTION_KEYS=<placeholder-key>`. For rotation, configure comma-separated keys with the new key first and old decrypt-only keys afterward. `.env.example` must contain only a placeholder, never a real key.
3. Never paste a real key into source files, commit it, print it in logs, or store it in the same database as credentials. Preserve a secure backup separately from the database. A lost key means stored credentials cannot be recovered.
4. Start or rebuild the existing Compose services so backend settings receive the key. Missing/malformed key configuration must fail safely; it must never activate plaintext storage.

Automated tests use generated ephemeral keys and fake GitLab transport; they require no real GitLab token.

Credential and candidate tokens are opaque, nonblank values limited to 2048 UTF-8 bytes. The GitLab HTTP adapter defaults to connect/read/write/pool timeouts of 5/10/5/5 seconds. Override them with `GITLAB_CONNECT_TIMEOUT_SECONDS`, `GITLAB_READ_TIMEOUT_SECONDS`, `GITLAB_WRITE_TIMEOUT_SECONDS`, and `GITLAB_POOL_TIMEOUT_SECONDS`; every value must be finite and greater than zero.

## Manual connection flow

1. Open an existing Monitoring Configuration details page.
2. Enter a GitLab access token in the masked credential field and save. The interface should clear the field and report configured/not validated; the configuration remains disabled unless separately enabled through existing Feature 002 behavior.
3. Explicitly validate the saved token, or submit a one-time candidate token for validation without saving. Verify safe success/failure feedback and that no discovery data is shown.
4. Replace or remove the credential through explicit controls. Removing it leaves the Monitoring Configuration intact.

Use an authorized test GitLab account and the narrowest token permission supporting the authenticated-user endpoint (commonly `read_user`). This validation does not confirm permissions required by later group/repository discovery. Never place a real token in command history, test fixtures, screenshots, issue text, API logs or source control. Prefer a disposable token and revoke it after manual testing.

## Verification

- Run backend unit/API/integration tests and frontend test suite.
- Apply Alembic upgrade and verify downgrade in an isolated test database.
- Verify PostgreSQL stores only encrypted bytes and API/status/log/frontend storage contain no token sentinel.
- Use HTTPX `MockTransport` for all automated upstream response and failure scenarios.
- Verify `GET /api/v4/user` is the only validation request and redirects are not followed.
- Run ordinary backend and frontend tests without a live PostgreSQL instance. When PostgreSQL is unavailable, report migration and PostgreSQL integration checks separately; do not substitute SQLite.
