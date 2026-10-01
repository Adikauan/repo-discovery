from app.domain.services.repository_file_filter import metadata_eligible, text_content_eligible
from app.domain.services.repository_summary_rule import RepositorySummaryRule
from app.domain.value_objects.repository_context import RepositoryContext, RepositoryFileMetadata


def test_summary_counts_metadata_only_and_excludes_paths_not_oversized_or_binary():
    context = RepositoryContext(7, "repo", "team/repo", "trunk", (
        RepositoryFileMetadata("src/main.PY", size_bytes=20_000_000),
        RepositoryFileMetadata("assets/logo.png", binary=True),
        RepositoryFileMetadata("README"),
        RepositoryFileMetadata("node_modules/pkg/index.js"),
        RepositoryFileMetadata("build/output.js"),
    ))
    result = RepositorySummaryRule().execute(context, max_extensions=100)
    assert result.file_count == 3
    assert result.observed_extensions == ("(none)", ".png", ".py")
    assert result.finding_count == 0
    assert metadata_eligible("src/keep.txt")
    assert not metadata_eligible("src/vendor/skip.txt")
    assert not text_content_eligible(1_048_577, 1_048_576, False)
    assert not text_content_eligible(10, 1_048_576, True)
    assert not text_content_eligible(10, 1_048_576, None)
    assert text_content_eligible(10, 1_048_576, False)


def test_extensions_are_case_normalized_sorted_and_respect_configured_limit():
    context = RepositoryContext(7, "repo", "team/repo", "trunk", tuple(
        RepositoryFileMetadata(path) for path in ("z/A.TS", "a/a.py", "b/a.md", "c/.gitignore", "d/noext")))
    rule = RepositorySummaryRule()
    assert rule.execute(context).observed_extensions == ("(none)", ".md", ".py", ".ts")
    short = rule.execute(context, max_extensions=2)
    assert short.observed_extensions == ("(none)", ".md") and short.extensions_truncated
