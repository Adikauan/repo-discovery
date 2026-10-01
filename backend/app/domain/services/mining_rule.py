from typing import Protocol
from dataclasses import dataclass

from app.domain.value_objects.repository_context import RepositoryContext
from app.domain.value_objects.repository_summary import RepositorySummaryResult
from app.domain.value_objects.finding_candidate import FindingCandidate


@dataclass(frozen=True, slots=True)
class MiningRuleResult:
    facts: object | None = None
    findings: tuple[FindingCandidate, ...] = ()


class MiningRule(Protocol):
    identifier: str
    version: str

    def execute(self, context: RepositoryContext, *, max_extensions: int = 100) -> RepositorySummaryResult | MiningRuleResult: ...
