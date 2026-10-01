from typing import Protocol
from uuid import UUID

from app.domain.entities.mining_scope import MiningScope


class MiningScopeRepository(Protocol):
    def get(self, configuration_id: UUID) -> MiningScope: ...

    def replace(self, scope: MiningScope, expected_version: int) -> bool: ...

    def refresh_metadata(self, scope: MiningScope) -> None: ...
