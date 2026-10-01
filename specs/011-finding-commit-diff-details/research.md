# Research: Finding Commit Diff Details

## Decisions

### Retrieve diffs on demand; do not persist patches

**Decision**: Fetch a diff only when a user opens a Finding's details. Do not store patch text in Finding, RepositoryExecution, MiningExecution, or a new table.

**Rationale**: This is the user's selected Option A. Existing immutable Finding records already store the repository/commit identity needed to request a diff. Patches can be large; persisting them duplicates provider data and expands storage/migrations. The accepted tradeoff is that a historical Finding can outlive the provider's diff availability; the UI retains the Finding and reports a normalized safe retrieval error.

**Alternatives considered**: Capture and persist during mining. Rejected for this feature because it increases database usage and changes Feature 008/010 processing success semantics.

### Use GitLab's commit diff operation

**Decision**: Extend the existing GitLab repository-client port and HTTP adapter with normalized commit diff retrieval, based on the stored project ID and commit hash.

**Rationale**: GitLab documents `GET /projects/:id/repository/commits/:sha/diff`, including old/new paths, per-file patch, new/renamed/deleted flags, and (in current versions) `collapsed` and `too_large`. The API is subject to server diff limits; the response must preserve known limitations rather than present partial data as complete. The API reference documents `collapsed` and `too_large` attributes as introduced in GitLab 18.4.

**Alternatives considered**: Reconstruct diff locally from current repository contents or snapshots. Rejected because provider commit diffs are authoritative for the stored commit, while local reconstruction risks resolving different content and adds unnecessary retrieval.

**Source**: [GitLab Commits API](https://docs.gitlab.com/api/commits/) (Retrieve commit diff).

### Bound response data in the application

**Decision**: Defaults are 100 changed-file entries, 256 KiB UTF-8 patch text per file, and 2 MiB aggregate patch text. The aggregate budget is only the sum of UTF-8 byte lengths of normalized non-null `diff` fields; it excludes JSON serialization and all metadata. Bound each old/new path to 4096 UTF-8 bytes separately. Changed-file list completeness is `complete`, `truncated`, or `unknown`, based only on evidence.

**Rationale**: The feature requires explicit safety limits. Conservative finite diff-text defaults prevent unbounded patch output while retaining metadata. The diff-text budget is not an HTTP/JSON response-size quota. Keep file metadata even when patch text is clipped. Completeness must remain unknown when GitLab does not supply evidence.

**Alternatives considered**: Persist patches or fail the whole response when one diff is large. Rejected: persistence is explicitly declined; failing all files would hide useful bounded metadata when only one patch is large.

### Binary and empty patch handling

**Decision**: Do not fetch file content to classify binary changes. Keep such entries in the list and return a textual-diff availability flag. Preserve GitLab's collapsed/too-large states separately.

**Rationale**: The user explicitly requires binary entries to remain visible and says a file's missing textual patch must not fail the commit details. Without a provider binary flag, an empty patch cannot be confidently labeled binary; present it as “Text diff unavailable” rather than assert a binary diagnosis.

## Resolved planning questions

- UI: responsive MUI dialog launched from each applicable Finding. No full-page review application.
- API: `GET /api/v1/findings/{finding_id}/diff`, with no client-controlled provider identifiers.
- Cache: no new persistent cache; no eager fetch; repeated open after close fetches again unless existing request lifecycle naturally retains currently loaded dialog state.
- Database: no migration or persistence model.
