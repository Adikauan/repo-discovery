from dataclasses import dataclass
from typing import Literal

ValidationOutcome = Literal[
    "success", "invalid_url", "invalid_credentials", "forbidden", "unreachable", "timeout",
    "invalid_response", "rate_limited", "provider_unavailable",
]


@dataclass(frozen=True, slots=True)
class ConnectionValidationResult:
    outcome: ValidationOutcome
    message: str

    @property
    def succeeded(self) -> bool:
        return self.outcome == "success"
