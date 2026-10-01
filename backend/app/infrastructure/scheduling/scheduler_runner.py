import asyncio
import logging
from datetime import UTC, datetime

from app.application.scheduling.scheduled_execution_dispatcher import ScheduledOccurrenceCandidate
from app.domain.services.schedule_calculator import calculate_next_occurrence

logger = logging.getLogger(__name__)


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Scheduler clock and persisted timestamps must be timezone-aware.")
    return value.astimezone(UTC)


class SchedulerRunner:
    """One process-local serialized scanner with bounded, non-queued workers."""

    def __init__(self, schedule_uow_factory, dispatcher, *, poll_interval_seconds=10,
                 concurrency=4, clock=None):
        if type(poll_interval_seconds) is not int or not 1 <= poll_interval_seconds <= 60:
            raise ValueError("Schedule poll interval must be between 1 and 60 seconds.")
        if type(concurrency) is not int or not 1 <= concurrency <= 8:
            raise ValueError("Scheduled execution concurrency must be between 1 and 8.")
        self.schedule_uow_factory = schedule_uow_factory
        self.dispatcher = dispatcher
        self.poll_interval_seconds = poll_interval_seconds
        self.concurrency = concurrency
        self.clock = clock or (lambda: datetime.now(UTC))
        self._task: asyncio.Task | None = None
        self._stop_event: asyncio.Event | None = None
        self._workers: set[asyncio.Task] = set()
        self._watermark: datetime | None = None
        self._scan_lock = asyncio.Lock()

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    @property
    def watermark(self) -> datetime | None:
        return self._watermark

    @property
    def active_worker_count(self) -> int:
        return sum(not worker.done() for worker in self._workers)

    async def start(self) -> None:
        if self.running:
            return
        self._watermark = _aware_utc(self.clock())
        self._stop_event = asyncio.Event()
        self._task = asyncio.create_task(self._run(), name="scheduled-execution-runner")
        logger.info("Scheduled execution runner started", extra={"startup_baseline": self._watermark.isoformat()})

    async def stop(self) -> None:
        if self._stop_event is not None:
            self._stop_event.set()
        if self._task is not None:
            await self._task
        if self._workers:
            await asyncio.gather(*tuple(self._workers), return_exceptions=True)
        self._task = None
        self._stop_event = None
        logger.info("Scheduled execution runner stopped")

    async def _run(self) -> None:
        assert self._stop_event is not None
        while not self._stop_event.is_set():
            await self.scan_once()
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self.poll_interval_seconds)
            except TimeoutError:
                pass

    async def scan_once(self, *, tick_instant: datetime | None = None) -> None:
        async with self._scan_lock:
            await self._scan_once(tick_instant=tick_instant)

    async def _scan_once(self, *, tick_instant: datetime | None = None) -> None:
        tick = _aware_utc(tick_instant or self.clock())
        if self._watermark is None:
            self._watermark = tick
        try:
            eligible = await asyncio.to_thread(self._load_eligible)
        except Exception:
            logger.error("Scheduled execution reconciliation could not read persisted schedules")
            return

        candidates = []
        for configuration, schedule in eligible:
            try:
                reference = max(self._watermark, _aware_utc(schedule.updated_at))
                occurrence = calculate_next_occurrence(schedule, reference)
            except Exception:
                logger.error("Scheduled execution reconciliation skipped invalid persisted schedule",
                    extra={"schedule_id": str(configuration.id)})
                continue
            if occurrence <= tick:
                candidates.append(ScheduledOccurrenceCandidate(configuration.id, occurrence, schedule.version))
        candidates.sort(key=lambda item: (item.scheduled_occurrence, str(item.monitoring_configuration_id)))

        for candidate in candidates:
            self._discard_finished_workers()
            if self.active_worker_count >= self.concurrency:
                logger.info("Scheduled occurrence skipped because worker capacity is full", extra={
                    "configuration_id": str(candidate.monitoring_configuration_id),
                    "occurrence": candidate.scheduled_occurrence.isoformat(),
                    "reason": "capacity_skipped",
                })
                continue
            worker = asyncio.create_task(asyncio.to_thread(self.dispatcher.dispatch, candidate),
                name=f"scheduled-execution-{candidate.monitoring_configuration_id}")
            self._workers.add(worker)
            worker.add_done_callback(lambda task, item=candidate: self._worker_done(task, item))

        self._watermark = tick

    def _load_eligible(self):
        uow = self.schedule_uow_factory()
        try:
            return uow.schedule_repository.list_eligible()
        finally:
            session = getattr(uow, "session", None)
            if session is not None:
                session.close()

    def _discard_finished_workers(self) -> None:
        self._workers = {worker for worker in self._workers if not worker.done()}

    def _worker_done(self, task: asyncio.Task, candidate: ScheduledOccurrenceCandidate) -> None:
        self._workers.discard(task)
        try:
            outcome = task.result()
            reason = outcome.outcome
            execution_id = str(outcome.execution.id) if outcome.execution is not None else None
        except Exception:
            reason = "dispatch_failed"
            execution_id = None
        logger.info("Scheduled occurrence evaluated", extra={
            "configuration_id": str(candidate.monitoring_configuration_id),
            "occurrence": candidate.scheduled_occurrence.isoformat(),
            "execution_id": execution_id,
            "outcome": reason,
        })
