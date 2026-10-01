# Finding Commit Diff API Contract

## Read Finding's commit diff

`GET /api/v1/findings/{finding_id}/diff`

No query or body parameters are accepted. In particular, the caller cannot supply a project ID, commit hash, GitLab URL, or credential.

The API resolves the Finding, its RepositoryExecution, MiningExecution, and immutable execution snapshot. It validates that the Finding is commit-based and uses only the stored commit hash, stable repository project ID, and matching historical GitLab instance context for the provider request.

### Success response

```json
{
  "findingId": "uuid",
  "repositoryName": "service",
  "repositoryNameTruncated": false,
  "repositoryFullPath": "group/service",
  "repositoryFullPathTruncated": false,
  "commitHash": "full-sha",
  "authorName": "Contributor",
  "authorEmail": "contributor@example.com",
  "authoredAt": "2026-09-30T12:00:00Z",
  "commitMessageSummary": "A bounded sanitized message",
  "filesCompleteness": "complete",
  "files": [
    {
      "oldPath": "src/old.ts",
      "newPath": "src/new.ts",
      "changeType": "renamed",
      "diff": "@@ -1 +1 @@\n-old\n+new\n",
      "textDiffAvailable": true,
      "binary": null,
      "collapsed": false,
      "tooLarge": false,
      "diffTruncated": false,
      "oldPathTruncated": false,
      "newPathTruncated": false
    }
  ]
}
```

Finding commit metadata is read from the persisted Finding; provider lookup is limited to its changed-file diff. Optional fields can be null. Change type is nullable if provider flags do not establish it. The response preserves deterministic provider order and returns at most 100 file entries. `repositoryName` is bounded to 200 UTF-8 bytes; `repositoryFullPath`, `oldPath`, and `newPath` are each bounded to 4096 UTF-8 bytes. The corresponding name/path `*Truncated` flags indicate clipping. Existing Finding fields retain their Feature 010 bounds: commit hash at most 64 hexadecimal characters, author email at most 254 characters, author name at most 200 Unicode code points, and message summary at most 500 Unicode code points.

The diff-text budget is defined exactly as:

```text
total_diff_bytes = sum(UTF8_BYTE_LENGTH(file.diff) for each non-null diff returned)
```

`total_diff_bytes` MUST be at most 2 MiB, and each `diff` MUST be at most 256 KiB. These limits count only normalized textual diff fields. They do not count JSON syntax or serialization overhead, field names, commit metadata, paths, booleans, timestamps, or other metadata. When the cumulative budget is reached, the server follows deterministic provider order, includes only the UTF-8-safe prefix that fits for the current patch if any, and omits subsequent diff text. Every clipped/omitted patch is marked `diffTruncated: true`; paths and other bounded file metadata remain available.

`filesCompleteness` is required and has exactly these meanings:

| Value | Meaning |
|---|---|
| `complete` | Reliable provider/pagination evidence establishes that all changed-file entries are returned. |
| `truncated` | The application or provider has evidence that additional changed-file entries exist but were omitted. |
| `unknown` | Available provider response/version metadata does not establish whether additional changed-file entries exist. |

Never infer `complete` or `truncated` from absent provider metadata. Application omission due to the 100-file cap is `truncated` only when evidence establishes additional entries; otherwise completeness is `unknown`. Per-file `collapsed`, `tooLarge`, `binary` (nullable unless provider identifies it), and `diffTruncated` describe patch availability and are independent of `filesCompleteness`. Binary/no-text entries remain listed with `textDiffAvailable: false` and nullable `diff`.

The UI shows no completeness warning for `complete`, a factual “Additional changed files were omitted” warning for `truncated`, and a calm informational note that GitLab did not provide enough information to confirm whether all changed files were returned for `unknown`.

### Errors

Use existing Problem Details format and safe normalized codes:

| HTTP | Code | Meaning |
|---|---|---|
| 404 | `finding_not_found` | Finding absent |
| 409 | `finding_diff_not_applicable` | Finding lacks supported commit identity/type |
| 404 | `commit_not_found` | Provider no longer has this commit/diff |
| 403 | `commit_diff_forbidden` | Current credential cannot access diff |
| 503 | `gitlab_credential_missing` | Secure credential unavailable |
| 409 | `gitlab_instance_mismatch` | Active connection differs from snapshot instance |
| 504 | `commit_diff_timeout` | Provider request timed out |
| 502 | `commit_diff_invalid_response` | Provider data is malformed |
| 502/503 | `commit_diff_unavailable` | Other normalized provider unavailability |

No raw provider body, exception, DB error, credentials, headers, or internal snapshot fields are returned. These errors do not mutate or remove the Finding.
