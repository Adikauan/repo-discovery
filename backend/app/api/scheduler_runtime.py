from app.application.scheduling.scheduled_execution_dispatcher import ScheduledExecutionDispatcher
from app.application.use_cases.process_mining_execution import ProcessMiningExecution
from app.config import get_settings
from app.api.dependencies import (get_credential_cipher, get_gitlab_repository_client,
                                  get_mining_worker_uow_factory)
from app.infrastructure.database.session import build_session_factory
from app.infrastructure.database.sqlalchemy_repositories import SqlAlchemyUnitOfWork
from app.infrastructure.scheduling.scheduler_runner import SchedulerRunner


def create_scheduler_runner() -> SchedulerRunner:
    settings = get_settings()
    session_factory = build_session_factory()
    uow_factory = lambda: SqlAlchemyUnitOfWork(session_factory())
    provider = get_gitlab_repository_client()
    cipher = get_credential_cipher()
    repository_worker_uow_factory = get_mining_worker_uow_factory()

    def pipeline_factory(uow):
        return ProcessMiningExecution(uow, provider, cipher,
            concurrency=settings.repository_mining_concurrency,
            max_file_bytes=settings.repository_mining_max_file_bytes,
            max_extensions=settings.repository_mining_max_extensions,
            max_commits=settings.mining_max_commits_per_repository_execution,
            worker_uow_factory=repository_worker_uow_factory)

    dispatcher = ScheduledExecutionDispatcher(uow_factory, pipeline_factory,
        threshold=settings.execution_staleness_threshold_seconds)
    return SchedulerRunner(uow_factory, dispatcher,
        poll_interval_seconds=settings.schedule_poll_interval_seconds,
        concurrency=settings.scheduled_execution_concurrency)
