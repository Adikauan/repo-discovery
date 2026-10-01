import asyncio

from app.api.main import create_app


class CountingRunner:
    def __init__(self):
        self.starts = 0
        self.stops = 0

    async def start(self):
        self.starts += 1

    async def stop(self):
        self.stops += 1


def test_scheduler_enabled_process_starts_one_runner_and_reuses_it_on_repeated_lifespan():
    created = []
    app = create_app(scheduler_enabled=True, scheduler_runner_factory=lambda: created.append(CountingRunner()) or created[-1])

    async def exercise():
        async with app.router.lifespan_context(app):
            assert app.state.scheduler_runner is created[0]
        async with app.router.lifespan_context(app):
            assert app.state.scheduler_runner is created[0]

    asyncio.run(exercise())
    assert len(created) == 1
    assert created[0].starts == 2 and created[0].stops == 2


def test_scheduler_disabled_api_worker_does_not_create_or_start_runner():
    created = []
    app = create_app(scheduler_enabled=False,
        scheduler_runner_factory=lambda: created.append(CountingRunner()) or created[-1])

    async def exercise():
        async with app.router.lifespan_context(app):
            assert app.state.scheduler_runner is None

    asyncio.run(exercise())
    assert created == []


def test_scheduler_runner_stops_cleanly_when_application_lifespan_exits():
    runner = CountingRunner()
    app = create_app(scheduler_enabled=True, scheduler_runner_factory=lambda: runner)

    async def exercise():
        async with app.router.lifespan_context(app):
            assert runner.starts == 1
        assert runner.stops == 1

    asyncio.run(exercise())
