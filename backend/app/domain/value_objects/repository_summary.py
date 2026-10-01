from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RepositorySummaryResult:
    processed_branch: str
    file_count: int
    observed_extensions: tuple[str, ...]
    extensions_truncated: bool = False
    finding_count: int = 0

    def __post_init__(self):
        if not self.processed_branch or self.file_count < 0 or self.finding_count != 0:
            raise ValueError("Repository summaries require factual nonnegative values and no findings.")
        if len(self.observed_extensions) > 100 or tuple(sorted(set(self.observed_extensions))) != self.observed_extensions:
            raise ValueError("Repository extensions must be unique, sorted, and bounded.")
