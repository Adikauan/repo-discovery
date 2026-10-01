from uuid import uuid4

from scripts import sanitize_legacy_branch_history as cleanup


class Result:
    rowcount = 1


class Connection:
    def __init__(self): self.statements = []
    def execute(self, statement, parameters):
        self.statements.append((str(statement), parameters))
        return Result()


class Engine:
    def __init__(self): self.connection = Connection()
    def begin(self): return self
    def __enter__(self): return self.connection
    def __exit__(self, *_): return False


def test_cleanup_deletes_only_selected_history_in_dependency_order():
    engine = Engine()
    configuration_id = uuid4()
    counts = cleanup.sanitize(engine, configuration_id)
    statements = [sql for sql, _ in engine.connection.statements]
    assert ["DELETE FROM findings", "DELETE FROM repository_executions",
            "DELETE FROM mining_executions", "DELETE FROM repository_checkpoints"] == [
        next(token for token in ("DELETE FROM findings", "DELETE FROM repository_executions",
            "DELETE FROM mining_executions", "DELETE FROM repository_checkpoints") if token in sql)
        for sql in statements]
    assert all(parameters["configuration_id"] == configuration_id for _, parameters in engine.connection.statements)
    assert counts == {"findings": 1, "repository_executions": 1, "mining_executions": 1, "repository_checkpoints": 1}
    joined_sql = " ".join(statements)
    for preserved in ("monitoring_configurations", "gitlab_credentials", "monitoring_configuration_scopes",
                      "target_branch_rules", "author_policies", "monitoring_schedules"):
        assert f"DELETE FROM {preserved}" not in joined_sql
