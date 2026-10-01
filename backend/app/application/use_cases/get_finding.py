from app.domain.errors import NotFoundError


class GetFinding:
    def __init__(self, uow): self.uow = uow
    def execute(self, identifier):
        finding = self.uow.finding_repository.get(identifier)
        if finding is None: raise NotFoundError("Finding not found.")
        repository = self.uow.repository_execution_repository.get(finding.repository_execution_id)
        execution = self.uow.execution_repository.get(repository.mining_execution_id) if repository else None
        if repository is None or execution is None: raise NotFoundError("Finding not found.")
        return finding, repository
