# Data Model: Finding Commit Diff Details

Feature 011 adds no persistence entities and performs no schema migration. It reads the existing Finding -> RepositoryExecution -> MiningExecution ownership chain and immutable execution snapshot defined by Feature 010/006.

## Read models

### CommitDiffDetails

An ephemeral normalized application/API response for one persisted commit-based Finding.

| Field | Meaning | Source |
|---|---|---|
| `finding_id` | Existing Finding identifier | Finding |
| `repository_name` / `repository_full_path` | Historical repository display | RepositoryExecution |
| `repository_name_truncated` / `repository_full_path_truncated` | Whether API display value was clipped to its 200/4096 UTF-8 byte bound | Response normalizer |
| `commit_hash` | Commit SHA to inspect | Finding |
| `author_email`, `author_name`, `authored_at`, `commit_message_summary` | Persisted historical metadata when available | Finding |
| `files` | Bounded changed-file entries in deterministic provider order | GitLab diff adapter |
| `files_completeness` | `complete`, `truncated`, or `unknown`; never inferred from missing evidence | Adapter + bounder |
| `total_diff_bytes` | Internal budget calculation: sum of UTF-8 byte lengths of returned non-null textual diff fields; not required as a public response field | Normalized returned `files` |

No current repository HEAD is consulted. No arbitrary request-supplied project, SHA, URL or token is accepted.

### ChangedFileDiff

| Field | Meaning |
|---|---|
| `old_path`, `new_path` | Provider paths; retain both for rename/delete/add semantics |
| `old_path_truncated`, `new_path_truncated` | Whether a path was clipped to its 4096 UTF-8 byte bound |
| `change_type` | `added`, `modified`, `deleted`, `renamed`, or null when provider metadata is insufficient |
| `diff` | Bounded unified patch text, nullable if unavailable |
| `text_diff_available` | Whether text patch content is present |
| `binary` | Provider-reported binary state when reliably available, otherwise null |
| `collapsed`, `too_large` | Provider-supplied patch states, nullable/false when provider version does not return them |
| `diff_truncated` | Patch text was clipped or omitted by application byte bounds |

The response-level file bound is 100 entries. Patch bounds are 256 KiB UTF-8 bytes per file and 2 MiB cumulative UTF-8 bytes of returned patch text. `total_diff_bytes = sum(len(file.diff.encode("utf-8")))` for each non-null returned `diff`; JSON serialization, field names, commit metadata, paths, booleans, timestamps, and other metadata do not consume this budget. Bound repository name to 200 UTF-8 bytes and repository/old/new paths to 4096 UTF-8 bytes each; report clipping separately. Existing Finding metadata is already bounded by Feature 010 (commit hash 64 hex characters; author email 254 characters; author name 200 Unicode code points; message summary 500 Unicode code points). Keep file metadata when patch text is truncated or unavailable. When cumulative budget is exceeded, process files in deterministic provider order, include only the UTF-8-safe prefix that fits for the current patch, then omit subsequent patches and flag each affected `diff_truncated`. `files_completeness` describes only changed-file list completeness, not patch completeness: `complete` requires reliable evidence, `truncated` requires evidence that additional file entries were omitted, and `unknown` means evidence is insufficient. Per-file binary/collapsed/too-large/diff-truncated states remain independent. `change_type` is derived only from provider flags when unambiguous; no type is guessed from paths alone.

## Validation and access rules

- Finding must exist and use the Unauthorized Commit Author rule with a usable persisted commit hash.
- Its owning RepositoryExecution must expose the stable GitLab project ID and its MiningExecution must expose the immutable snapshot connection/instance identity.
- Before any provider call, validate that the active secure GitLab connection belongs to the same instance as the snapshot. Resolve/decrypt credential via existing service only for the necessary call lifetime.
- All provider lookup arguments come from those persisted objects. Finding mismatch and missing credentials/instance map to normalized safe errors.
- Findings remain readable even if the on-demand diff cannot be retrieved.
- Provider transport DTOs and credentials never enter this read model.
