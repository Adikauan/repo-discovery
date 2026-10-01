from app.domain.services.mining_rule import MiningRule
from app.domain.services.repository_file_filter import metadata_eligible
from app.domain.value_objects.repository_context import RepositoryContext
from app.domain.value_objects.repository_summary import RepositorySummaryResult


def _extension(path: str) -> str:
    name = path.rsplit("/", 1)[-1]
    dot = name.rfind(".")
    if dot <= 0 or dot == len(name) - 1:
        return "(none)"
    return name[dot:].casefold()


class RepositorySummaryRule:
    identifier = "repository-summary"
    version = "1"

    def execute(self, context: RepositoryContext, *, max_extensions: int = 100) -> RepositorySummaryResult:
        if type(max_extensions) is not int or not 1 <= max_extensions <= 100:
            raise ValueError("Maximum extensions must be between 1 and 100.")
        eligible = [item for item in context.files if metadata_eligible(item.path)]
        extensions = sorted({_extension(item.path) for item in eligible})
        truncated = len(extensions) > max_extensions
        return RepositorySummaryResult(context.branch, len(eligible), tuple(extensions[:max_extensions]), truncated, 0)
