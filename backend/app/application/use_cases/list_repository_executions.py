from app.domain.errors import NotFoundError


class ListRepositoryExecutions:
    def __init__(self, uow):
        self.uow = uow

    def execute(self, execution_id, *, page=1, page_size=25):
        if self.uow.execution_repository.get(execution_id) is None:
            raise NotFoundError("Execution not found.")
        items, total = self.uow.repository_execution_repository.list_for_execution(execution_id, page=page, page_size=page_size)
        return {"items": items, "page": page, "page_size": page_size, "total_items": total}
