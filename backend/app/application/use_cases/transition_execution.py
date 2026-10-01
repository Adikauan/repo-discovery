from datetime import UTC, datetime
from app.domain.errors import ConflictError, NotFoundError


def persist_transition(uow, current, target, now, *, error_code=None, repository_mining_completed=None):
    """Apply a domain transition while the caller owns the row lock/transaction."""
    changed = current.transition(target, now, expected_status=current.status, error_code=error_code,
                                 repository_mining_completed=repository_mining_completed)
    if not uow.execution_repository.transition(changed, current.status):
        raise ConflictError('The execution state changed. Reload before trying again.')
    return changed


class TransitionExecution:
    def __init__(self, uow, clock=None):
        self.uow = uow
        self.clock = clock or (lambda: datetime.now(UTC))

    def execute(self, identifier, expected_status, target, *, error_code=None, repository_mining_completed=None):
        try:
            current = self.uow.execution_repository.get(identifier, for_update=True)
            if current is None:
                raise NotFoundError('Execution not found.')
            if current.status != expected_status:
                raise ConflictError('The execution state changed. Reload before trying again.')
            result = persist_transition(self.uow, current, target, self.clock(), error_code=error_code,
                                        repository_mining_completed=repository_mining_completed)
            self.uow.commit()
            return result
        except Exception:
            self.uow.rollback()
            raise
