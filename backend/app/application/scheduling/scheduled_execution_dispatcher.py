from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.application.use_cases.create_mining_execution import CreateMiningExecution, ExecutionCreationResult
from app.domain.errors import ConflictError, FieldValidationError


@dataclass(frozen=True, slots=True)
class ScheduledOccurrenceCandidate:
    monitoring_configuration_id: UUID
    scheduled_occurrence: datetime
    expected_schedule_version: int


class ScheduledExecutionDispatcher:
    """Adapt a due schedule occurrence to the shared execution creation and mining path."""

    def __init__(self, uow_factory, pipeline_factory, *, clock=None, threshold=300):
        self.uow_factory = uow_factory
        self.pipeline_factory = pipeline_factory
        self.clock = clock
        self.threshold = threshold

    def dispatch(self, candidate: ScheduledOccurrenceCandidate) -> ExecutionCreationResult:
        uow = self.uow_factory()
        try:
            pipeline = self.pipeline_factory(uow)
            return CreateMiningExecution(uow, clock=self.clock, threshold=self.threshold,
                mining_pipeline=pipeline).execute(candidate.monitoring_configuration_id,
                    trigger_type="scheduled", scheduled_occurrence=candidate.scheduled_occurrence,
                    expected_schedule_version=candidate.expected_schedule_version)
        except ConflictError:
            uow.rollback()
            return ExecutionCreationResult("conflict")
        except FieldValidationError:
            uow.rollback()
            return ExecutionCreationResult("ineligible")
        finally:
            session = getattr(uow, "session", None)
            if session is not None:
                session.close()
