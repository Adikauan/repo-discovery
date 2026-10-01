from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class CreateRequestReceipt:
    request_key: str
    request_fingerprint: str
    response_snapshot: dict[str, Any]


class CreateRequestStore(Protocol):
    def get(self, request_key: str) -> CreateRequestReceipt | None: ...
    def add(self, receipt: CreateRequestReceipt) -> None: ...
