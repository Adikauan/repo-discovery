from datetime import UTC, datetime, time
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

from app.domain.entities.monitoring_schedule import MonitoringSchedule
from app.infrastructure.database.models import MonitoringScheduleRecord
from app.infrastructure.database.sqlalchemy_repositories import SqlAlchemyMonitoringScheduleRepository


def test_absent_record_is_virtual_unconfigured_version_zero():
    session = Mock()
    session.get.return_value = None
    result = SqlAlchemyMonitoringScheduleRepository(session).get(uuid4())
    assert not result.configured and result.version == 0 and result.updated_at is None


def test_unconfigured_tombstone_is_read_with_retained_version():
    identifier = uuid4()
    session = Mock()
    session.get.return_value = SimpleNamespace(configured=False, version=4, updated_at=datetime.now(UTC))
    result = SqlAlchemyMonitoringScheduleRepository(session).get(identifier)
    assert result.monitoring_configuration_id == identifier
    assert not result.configured and result.version == 4


def test_insert_uses_conflict_safe_virtual_version_compare_and_swap():
    identifier = uuid4()
    session = Mock()
    session.execute.return_value.scalar_one_or_none.return_value = identifier
    schedule = MonitoringSchedule.create(configuration_id=identifier, recurrence_type="daily", enabled=True,
        execution_time=time(9, 30), timezone="UTC", now=datetime(2026, 1, 1, tzinfo=UTC))
    assert SqlAlchemyMonitoringScheduleRepository(session).replace(schedule, 0)
    statement = session.execute.call_args.args[0]
    assert "ON CONFLICT" in str(statement.compile(dialect=__import__("sqlalchemy.dialects.postgresql", fromlist=["dialect"]).dialect()))


def test_update_uses_expected_version_and_returns_cas_result():
    identifier = uuid4()
    session = Mock()
    session.execute.return_value.rowcount = 0
    schedule = MonitoringSchedule.create(configuration_id=identifier, recurrence_type="daily", enabled=True,
        execution_time=time(9, 30), timezone="UTC", now=datetime(2026, 1, 1, tzinfo=UTC), version=3)
    assert not SqlAlchemyMonitoringScheduleRepository(session).replace(schedule, 2)
    compiled = session.execute.call_args.args[0].compile(
        dialect=__import__("sqlalchemy.dialects.postgresql", fromlist=["dialect"]).dialect())
    assert "version = %(version_1)s" in str(compiled)


def test_list_eligible_returns_enabled_active_configuration_schedule_pairs():
    identifier = uuid4()
    created = datetime(2026, 1, 1, tzinfo=UTC)
    configuration = SimpleNamespace(id=identifier, name="enabled", description=None,
        gitlab_url="https://gitlab.example", enabled=True, created_at=created,
        updated_at=created, revision=1, retired_at=None)
    schedule = SimpleNamespace(configured=True, version=3, recurrence_type="weekly", enabled=True,
        execution_time=time(10), timezone="UTC", day_of_week=1, day_of_month=None,
        created_at=created, updated_at=created)
    session = Mock()
    session.execute.return_value.all.return_value = [(configuration, schedule)]
    result = SqlAlchemyMonitoringScheduleRepository(session).list_eligible()
    assert len(result) == 1
    assert result[0][0].id == identifier and result[0][1].version == 3
    assert result[0][1].recurrence_type.value == "weekly"
