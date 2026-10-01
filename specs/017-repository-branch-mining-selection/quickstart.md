# Quickstart: Repository Branch Mining Selection

## User flow

1. Create/open a Monitoring Configuration.
2. Configure GitLab Connection.
3. In Scope, select direct repositories and/or dynamic Groups. Scope does not select branches.
4. Open **Policy**. Directly selected repositories and current repositories under selected Groups are listed automatically.
5. For each effective repository, configure one or more GitLab-discovered branch Policies and allowed authors. A repository without a Policy is shown as **Policy required**.
6. Complete Scheduling if desired, then execute manually or wait for the configured schedule.

Example: Group `backend` currently contains `api-a` and `api-b`; both appear in Policy and require at least one branch Policy. If `api-c` later appears under that Group, it joins effective Scope dynamically, appears as **Policy required**, and blocks both manual and scheduled execution until configured. No default branch is inferred.

## Regression scenarios

1. Directly select a repository and configure Policy branch `dev-larah`, while GitLab reports `master` as default. The mining-target resolver must return that repository with `dev-larah`; there is no Scope target-branch record and no empty `branches: []` target response.
2. Configure multiple Policies such as `main` and `dev-larah`; verify each receives independent RepositoryExecution, baseline/checkpoint, authorization, Finding branch, and snapshot target context.
3. Remove or make one configured Policy branch unavailable; verify safe repository/branch failure without substituting a branch.
4. Leave any effective repository without Policy; verify manual and scheduled execution are rejected before a MiningExecution starts, with no partial subset.
5. Verify legacy branchless Group Policies do not authorize new execution commits and remain unchanged in historical snapshots.

## Migration notes

Migration sanitation is targeted across revisions `0010_repository_target_branches` and `0011_policy_mining_targets`. Revision 0010 deletes old checkpoint rows because their default-branch provenance cannot be proven for a Policy branch; it adds nullable `target_branch` to RepositoryExecution and leaves legacy rows unassigned rather than fabricating branch history. Revision 0011 drops obsolete Scope target-branch rules without converting them into Policies. Configuration, credentials, Scope, schedules, author policies, execution records, snapshots, and Findings remain. No broad development-history cleanup is performed.

## Validation commands

Run from the repository root (PowerShell):

```powershell
backend/.venv/Scripts/python.exe -m pytest backend/tests/unit -q -p no:cacheprovider
$entry = Get-Content .env | Where-Object { $_ -match '^TEST_DATABASE_URL=' } | Select-Object -First 1
$env:TEST_DATABASE_URL = $entry.Substring('TEST_DATABASE_URL='.Length).Trim().Trim('"')
$env:DATABASE_URL = $env:TEST_DATABASE_URL
backend/.venv/Scripts/python.exe -m pytest backend/tests -q -p no:cacheprovider
npx vitest run --pool=threads --maxWorkers=1
npm run build
```

PostgreSQL-specific migration and integration tests must use the configured `TEST_DATABASE_URL`; SQLite is not a substitute.

## Implementation validation record

Validation of the corrected Policy-sourced mining-target model:

- Backend full suite with PostgreSQL integration: **395 passed**, 79 warnings.
- Frontend suite: **211 passed** across 53 test files.
- Frontend production build: **passed**; Vite reported the existing large-chunk advisory (>500 kB).
- Migration integration: **passed**; obsolete Scope target rules are removed, legacy checkpoint rows are deleted, old RepositoryExecution target branch remains null, and unrelated records are preserved.
- Manual visual validation: **pending**; approved Feature 017 reference images were not present in the references folder, so no visual comparison is claimed.
