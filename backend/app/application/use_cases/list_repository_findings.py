from app.domain.errors import NotFoundError


class ListRepositoryFindings:
    def __init__(self, uow): self.uow = uow
    def execute(self, execution_id, repository_execution_id, *, page=1, page_size=25, rule_id=None, severity=None):
        if self.uow.execution_repository.get(execution_id) is None: raise NotFoundError("Execution not found.")
        if self.uow.repository_execution_repository.get(repository_execution_id, execution_id) is None:
            raise NotFoundError("Repository execution not found.")
        items, total = self.uow.finding_repository.list_for_repository(repository_execution_id,
            page=page, page_size=page_size, rule_id=rule_id, severity=severity)
        return {"items": items, "total_items": total}
