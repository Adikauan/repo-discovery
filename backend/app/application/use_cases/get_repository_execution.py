from app.domain.errors import NotFoundError


class GetRepositoryExecution:
    def __init__(self, uow):
        self.uow = uow

    def execute(self, execution_id, repository_execution_id):
        if self.uow.execution_repository.get(execution_id) is None:
            raise NotFoundError("Execution not found.")
        item = self.uow.repository_execution_repository.get(repository_execution_id, execution_id)
        if item is None:
            raise NotFoundError("Repository execution not found.")
        return item
