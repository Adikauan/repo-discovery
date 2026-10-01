class FieldValidationError(ValueError):
    def __init__(self, field: str, code: str, message: str):
        super().__init__(message)
        self.field = field
        self.code = code
        self.message = message


class NotFoundError(LookupError):
    pass


class ConflictError(RuntimeError):
    pass


class CredentialReplacementConflict(ConflictError):
    pass


class CredentialServiceUnavailable(RuntimeError):
    pass


class GitLabDiscoveryError(RuntimeError):
    def __init__(self, outcome: str):
        self.outcome = outcome
        super().__init__(outcome)


class IdempotencyConflict(ConflictError):
    pass


class StaleConfigurationError(ConflictError):
    pass


class AuthorPolicyApiError(RuntimeError):
    DETAILS = {
        "scope_repository_not_selected": (422, "The repository is not directly selected in this configuration."),
        "scope_group_not_selected": (422, "The Group is not selected in this configuration."),
        "group_policy_discontinued": (422, "Group author Policies are no longer accepted for new execution configuration."),
        "gitlab_credential_missing": (503, "A usable GitLab credential is unavailable."),
        "gitlab_instance_mismatch": (409, "The configured GitLab instance differs from the selected scope."),
        "repository_not_found": (404, "The selected repository is unavailable."),
        "repository_forbidden": (403, "The selected repository cannot be accessed."),
        "repository_timeout": (504, "GitLab did not respond in time. Try again."),
        "repository_invalid_response": (502, "GitLab returned an invalid repository response."),
        "author_policy_not_found": (404, "Author policy not found."),
    }

    def __init__(self, code: str):
        if code not in self.DETAILS:
            code = "repository_invalid_response"
        self.code = code
        self.status, self.detail = self.DETAILS[code]
        super().__init__(self.detail)


class MissingPreconditionError(ConflictError):
    pass


class DuplicateIdempotencyKey(RuntimeError):
    pass


class DuplicateScheduledOccurrence(RuntimeError):
    pass


class BadRequestError(ValueError):
    pass


class CommitDiffError(RuntimeError):
    """Allow-listed safe error for on-demand Finding diff retrieval."""
    DETAILS = {
        "finding_not_found": (404, "Finding not found."),
        "finding_diff_not_applicable": (409, "Commit diff is not available for this Finding."),
        "gitlab_credential_missing": (503, "A usable GitLab credential is unavailable."),
        "gitlab_instance_mismatch": (409, "The configured GitLab instance differs from the execution snapshot."),
        "commit_not_found": (404, "The commit associated with this Finding could not be found."),
        "commit_diff_forbidden": (403, "GitLab denied access to this commit diff."),
        "commit_diff_timeout": (504, "GitLab did not respond in time. Try again."),
        "commit_diff_unavailable": (503, "The commit diff is temporarily unavailable. Try again."),
        "commit_diff_invalid_response": (502, "GitLab returned an invalid commit diff response."),
    }

    def __init__(self, code: str):
        if code not in self.DETAILS:
            code = "commit_diff_unavailable"
        self.code = code
        self.status, self.detail = self.DETAILS[code]
        super().__init__(self.detail)
