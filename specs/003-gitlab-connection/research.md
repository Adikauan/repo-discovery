# Research: GitLab Connection

## GitLab connection validation

- **Decision**: Validate a configured instance with one bounded, read-only `GET /api/v4/user` call. A successful authenticated-user response confirms reachability, authentication, and basic API access; discard the response body after checking status and the minimum expected response shape. Do not return, log, or persist profile data.
- **Rationale**: The user selected a minimal validation probe using an authenticated identity endpoint and explicitly deferred group permission checking to Feature 004. GitLab documents the endpoint in its [Users API](https://docs.gitlab.com/api/users/).
- **Alternatives considered**: A Groups API permission probe could more directly test future discovery permissions, but is deferred with that feature. Retrieving group/project collections and admin-only membership APIs are out of scope.

## Token authentication and least privilege

- **Decision**: Send the token in GitLab's `PRIVATE-TOKEN` request header and recommend the narrowest permission supporting the authenticated-user endpoint (commonly `read_user`). Do not require a specific token type; observed endpoint access determines validation success.
- **Rationale**: GitLab supports access-token authentication through documented request headers ([REST authentication](https://docs.gitlab.com/api/rest/authentication/)). The broader `api` scope includes write access and is unnecessary for this feature's read-only check ([access-token scopes](https://docs.gitlab.com/security/tokens/access_token_scopes/)).
- **Alternatives considered**: The broad `api` scope increases privilege beyond this feature. Do not parse a token string to infer scopes; validate the actual permitted operation. Feature 004 will determine and verify its own discovery permissions.

## URL handling and provider failures

- **Decision**: Treat the configured GitLab URL as the instance root, preserve a self-managed relative base path, normalize trailing slashes, and append the documented `/api/v4` prefix and endpoint path. Do not follow redirects while sending a credential. Map DNS/connect/TLS, timeout, 401, 403, 429, 5xx, and unexpected response shapes into typed normalized outcomes such as `invalid_credentials`, `forbidden`, `unreachable`, `timeout`, and `invalid_response`.
- **Rationale**: GitLab REST APIs use `/api/v4`, and self-managed installations can use relative paths ([REST API](https://docs.gitlab.com/api/rest/), [API style guide](https://docs.gitlab.com/development/api_styleguide/)). Redirects could move a credential to a different origin. Safe categories make the user outcome useful without forwarding provider response bodies, request headers, URLs, or exception text.
- **Alternatives considered**: Assuming the host root would break relative-path installations. Returning upstream messages is unsafe and unstable. Following redirects is unnecessary for a connection validation request and risks credential forwarding.

## Credential encryption and key configuration

- **Decision**: Use authenticated Fernet encryption from `cryptography` behind an application-owned credential-storage port. Persist only Fernet ciphertext and non-secret metadata. Supply the ordered Fernet key ring through secure deployment configuration, with the first key used for new encryption and configured prior keys available only for decryption during planned rotation.
- **Rationale**: Fernet provides authenticated symmetric encryption and the maintained `cryptography` package supports key rotation helpers ([Fernet documentation](https://cryptography.io/en/stable/fernet/)). OWASP recommends authenticated encryption, separation of encryption keys from encrypted data, and planned key lifecycle procedures ([Cryptographic Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html), [Key Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Key_Management_Cheat_Sheet.html)).
- **Alternatives considered**: Plaintext, reversible obfuscation, or a key stored beside ciphertext violate the security requirement. Hand-rolled cryptography is rejected. A cloud KMS/HSM would require an integration and deployment platform not present in this project; an application-owned port preserves that future option.
- **Operational note**: Losing all configured keys makes retained credentials irrecoverable. Keys must be backed up and supplied independently of database backups. A general key-management service and automated rotation workflow are outside Feature 003; configuration must support retaining old decrypt-only keys while an operator re-encrypts data before removing them.

## HTTP client dependency

- **Decision**: Promote the existing development-only HTTPX dependency to a production dependency for a synchronous GitLab HTTP adapter. Use explicit finite timeouts, redirects disabled, and an injectable transport/client.
- **Rationale**: HTTPX fits the existing synchronous FastAPI routes and SQLAlchemy sessions, provides explicit timeout and redirect behavior, and supports deterministic `MockTransport` tests. Production currently has no HTTP client dependency; standard-library urllib would make transport mocking and uniform timeout behavior less clear.
- **Alternatives considered**: An asynchronous client would require changing the existing synchronous request/session path without a current need. Adding an additional HTTP client library is unnecessary.

## Credential and validation metadata

- **Decision**: Store the credential in a dedicated one-to-one table keyed by Monitoring Configuration ID. Keep ciphertext outside the domain entity and API DTOs. Store current validation result/time and a non-secret credential revision plus GitLab URL fingerprint needed to prevent a stale validation result from being applied after a URL or token change. Preserve `last_successful_validation_at` after failed revalidation of the same credential while reporting failure as the latest outcome.
- **Rationale**: The existing Monitoring Configuration entity remains independent from secrets. Dedicated storage enables transactional replacement/removal, deletion when the configuration is retired, and a response DTO limited to presence and safe metadata. A validation result is associated with the exact credential revision and URL that were checked.
- **Alternatives considered**: Adding the secret to the Monitoring Configuration ORM/entity/response would increase accidental disclosure risk and couple unrelated fields. A complete validation audit-history subsystem is explicitly out of scope.
