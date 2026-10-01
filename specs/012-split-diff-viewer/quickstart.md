# Quickstart: Split Diff Viewer Validation

## Prerequisites

- Install the existing frontend dependencies with `npm install` if needed.
- Use the current Feature 011 test fixtures; no backend, GitLab credential, database, or migration setup is required for the standard UI/parser tests.

## Focused validation

From the repository root:

```powershell
npm run test:run -- src/test/features/executions/split-diff-parser.test.ts src/test/features/executions/split-diff-viewer.test.tsx src/test/features/executions/finding-commit-diff.test.tsx src/test/features/executions/execution-accessibility.test.tsx
```

Expected outcomes include accurate hunk line numbers and replacement pairing, safe malformed-patch handling, accessible Before/After sides, retained file sidebar, no eager diff requests, and keyboard focus restoration.

## Full frontend validation

```powershell
npm run test:run
npm run build
```

The complete frontend suite should pass and the production TypeScript/Vite build should complete. Existing environment-specific Vitest process restrictions may require the repository's supported local runner configuration; do not change application behavior to work around a test-runner environment restriction.

## Manual review scenario

Open an Unauthorized Commit Author Finding, choose **View commit diff**, then select a file containing context, removed/added replacement lines, and multiple hunks. Verify the Before and After columns, line numbers, side-only placeholders, hunk separators, and existing partial-data notices. Also inspect a binary or too-large file to confirm it remains unavailable as text and the changed-file list remains present.
