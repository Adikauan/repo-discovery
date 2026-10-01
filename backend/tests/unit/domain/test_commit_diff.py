from app.domain.value_objects.commit_diff import (
    CommitDiffFile,
    CommitDiffProviderResult,
    bound_utf8,
    normalize_commit_diff,
)


def file(old="src/a", new="src/a", diff="", **kwargs):
    return CommitDiffFile(old, new, "modified", diff or None, text_diff_available=bool(diff), **kwargs)


def test_total_diff_budget_below_exact_and_over_limit_counts_only_diff_utf8_bytes():
    assert normalize_commit_diff([file(diff="é")], "complete", max_files=10,
        max_file_bytes=10, max_total_bytes=3).total_diff_bytes == 2
    exact = normalize_commit_diff([file(diff="éa")], "complete", max_files=10,
        max_file_bytes=10, max_total_bytes=3)
    assert exact.total_diff_bytes == 3 and exact.files[0].diff == "éa"
    over = normalize_commit_diff([file(diff="éab")], "complete", max_files=10,
        max_file_bytes=10, max_total_bytes=3)
    assert over.total_diff_bytes == 3 and over.files[0].diff == "éa"
    assert over.files[0].diff_truncated is True


def test_metadata_does_not_consume_total_diff_budget():
    item = file(old="x" * 4096, new="y" * 4096, diff="a")
    result = normalize_commit_diff([item], "complete", max_files=10, max_file_bytes=10,
        max_total_bytes=1, max_path_bytes=4096)
    assert result.total_diff_bytes == 1
    assert result.files[0].old_path == "x" * 4096


def test_utf8_path_is_bounded_without_splitting_a_code_point():
    value, clipped = bound_utf8("abéz", 4)
    assert value == "abé" and clipped is True


def test_file_count_limit_requires_evidence_for_truncated_completeness():
    values = [file(old=f"{index}", new=f"{index}", diff="x") for index in range(3)]
    result = normalize_commit_diff(values, "unknown", max_files=2, max_file_bytes=10,
        max_total_bytes=100)
    assert len(result.files) == 2
    assert result.files_completeness == "truncated"


def test_completeness_states_are_independent_from_file_patch_states():
    assert normalize_commit_diff([file(diff="x", collapsed=True)], "complete",
        max_files=1, max_file_bytes=10, max_total_bytes=10).files_completeness == "complete"
    assert normalize_commit_diff([file(diff="x")], "truncated",
        max_files=1, max_file_bytes=10, max_total_bytes=10).files_completeness == "truncated"
    assert normalize_commit_diff([file(diff="x")], "unknown",
        max_files=1, max_file_bytes=10, max_total_bytes=10).files_completeness == "unknown"


def test_unknown_change_type_and_empty_patch_are_preserved_as_unavailable_text():
    item = CommitDiffFile("old", "new", None, None, False)
    result = normalize_commit_diff([item], "unknown", max_files=1, max_file_bytes=10, max_total_bytes=10)
    assert result.files[0].change_type is None
    assert result.files[0].diff is None and result.files[0].text_diff_available is False
