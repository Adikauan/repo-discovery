from datetime import UTC, datetime

from app.domain.services.unauthorized_commit_author_rule import UnauthorizedCommitAuthorRule
from app.domain.value_objects.normalized_commit import NormalizedCommit


def commit(sha, email, name="ignored"):
    return NormalizedCommit(sha * 40, email, name, datetime(2026, 1, 1, tzinfo=UTC), "message\x00 with controls")


def test_authorized_emails_are_trimmed_casefolded_and_deduplicated():
    result = UnauthorizedCommitAuthorRule().execute(
        [commit("a", " Alice@Example.com ")], ["alice@example.com", " ALICE@example.com "])
    assert result == ()


def test_empty_policy_marks_valid_author_unauthorized_and_deduplicates_commits():
    candidate = commit("b", "writer@example.com")
    result = UnauthorizedCommitAuthorRule().execute([candidate, candidate], [])
    assert len(result) == 1
    assert result[0].severity == "warning" and result[0].author_email == "writer@example.com"
    assert "message" in result[0].commit_message_summary and "\x00" not in result[0].commit_message_summary


def test_missing_and_malformed_email_are_findings_without_raw_identity():
    results = UnauthorizedCommitAuthorRule().execute([
        commit("c", None), commit("d", "  "), commit("e", "not-an-email")], ["valid@example.com"])
    assert [item.author_email_state for item in results] == ["missing", "missing", "malformed"]
    assert all(item.author_email is None for item in results)
    assert "not-an-email" not in repr(results)


def test_author_name_never_authorizes_a_commit():
    result = UnauthorizedCommitAuthorRule().execute([commit("f", "unknown@example.com", "Alice")], ["alice@example.com"])
    assert len(result) == 1

