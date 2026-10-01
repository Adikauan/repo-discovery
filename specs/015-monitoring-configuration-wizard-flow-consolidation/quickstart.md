# Quickstart: Feature 015 Validation

## Prerequisites

- Existing frontend dependencies installed (`npm install`).
- Backend test dependencies installed in the backend's configured virtual environment.
- Frontend and backend use the existing application test configuration; no database migration or new environment variable is required.

## Automated validation

From the repository root:

```powershell
npm run test:run
npm run build
```

From `backend/` using the project's configured Python environment:

```powershell
pytest tests/unit/application/test_gitlab_candidate_validation.py tests/api/test_gitlab_candidate_validation.py
```

Use mocked GitLab connection clients in automated candidate-validation tests. Those tests must verify normalized success/failure, no persistence, and no credential disclosure.

## Manual create-flow check

1. Open Monitoring Configurations and choose New configuration.
2. Enter General values and activate Next. Confirm no configuration is created and the wizard advances to GitLab Connection.
3. Enter the GitLab URL/token and validate. Confirm only safe status is shown.
4. Activate Next. Confirm one configuration is created, its credential is securely saved/validated, and Scope opens with the returned configuration identity.
5. Simulate candidate failure and a credential-save failure. Confirm candidate failure creates nothing and post-create retry does not create a duplicate.

## Manual edit/navigation check

1. Open Edit from the configuration list and verify the same five-step order.
2. Save valid/invalid values with Next in each step. Confirm failed save/validation stays on that step.
3. Change Scope/Authors/Scheduling drafts and use Back/exit. Confirm the existing discard guard remains.
4. Confirm Enable/Disable is only in General, Delete only in the list, and no section shortcuts appear in the configuration header.

## Visual and responsive review

Compare the step screens with the supplied references in `references/` and Feature 013/014 list styling. Ensure the bottom bar remains fixed within main content, does not cover scrollable controls, and the wizard stays usable at narrow widths. Record manual visual work as complete only after actually comparing the running UI with the images.
