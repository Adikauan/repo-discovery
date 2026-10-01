from typing import Protocol
from uuid import UUID


class TargetBranchRepository(Protocol):
    def list_for_configuration(self, configuration_id: UUID): ...
    def replace_for_configuration(self, configuration_id: UUID, rules) -> None: ...
