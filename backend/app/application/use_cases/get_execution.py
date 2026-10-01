from app.domain.errors import NotFoundError


def snapshot_projection(snapshot):
    return dict(configuration_id=snapshot.configuration_id, configuration_name=snapshot.configuration_name,
        configuration_enabled=snapshot.configuration_enabled, gitlab_url=snapshot.gitlab_url,
        configuration_revision=snapshot.configuration_revision,
        scope=dict(groups=[dict(gitlab_group_id=g.gitlab_group_id, name=g.name, full_path=g.full_path) for g in snapshot.groups],
            repositories=[dict(gitlab_project_id=r.gitlab_project_id, name=r.name, full_path=r.full_path) for r in snapshot.repositories]))


class GetExecution:
    def __init__(self, uow):
        self.uow = uow

    def execute(self, identifier):
        item = self.uow.execution_repository.get(identifier)
        if item is None:
            raise NotFoundError('Execution not found.')
        return item
