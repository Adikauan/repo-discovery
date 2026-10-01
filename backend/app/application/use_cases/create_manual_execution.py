from app.application.use_cases.create_mining_execution import CreateMiningExecution


class CreateManualExecution:
    """Compatibility adapter retaining the existing manual API use-case contract."""

    def __init__(self, uow, clock=None, threshold=300, orchestration=None, before_start=None, mining_pipeline=None):
        self.creation = CreateMiningExecution(uow, clock, threshold, orchestration, before_start, mining_pipeline)

    def execute(self, configuration_id, idempotency_key=None):
        return self.creation.execute(configuration_id, trigger_type='manual',
            idempotency_key=idempotency_key).execution
