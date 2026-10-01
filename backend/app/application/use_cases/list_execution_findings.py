from app.domain.errors import NotFoundError


class ListExecutionFindings:
    def __init__(self, uow): self.uow = uow
    def execute(self, execution_id, *, page=1, page_size=25, repository_id=None, rule_id=None, severity=None):
        if self.uow.execution_repository.get(execution_id) is None: raise NotFoundError("Execution not found.")
        rows, total = self.uow.finding_repository.list_for_execution(execution_id, page=page, page_size=page_size,
            repository_id=repository_id, rule_id=rule_id, severity=severity)
        paths = {}
        items = []
        for row in rows:
            if isinstance(row, tuple): item, path = row
            else:
                item = row
                repository = self.uow.repository_execution_repository.get(item.repository_execution_id)
                path = repository.repository_full_path if repository else ""
                name = repository.repository_name if repository else ""
                execution = repository.mining_execution_id if repository else None
                branch = repository.processed_branch if repository else None
            if isinstance(row, tuple):
                repository = self.uow.repository_execution_repository.get(item.repository_execution_id)
                name = repository.repository_name if repository else ""
                execution = repository.mining_execution_id if repository else None
                branch = repository.processed_branch if repository else None
            items.append(item); paths[item.repository_execution_id] = (path, name, execution, branch)
        return {"items": items, "total_items": total, "repository_paths": paths}
