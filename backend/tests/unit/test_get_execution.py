from uuid import uuid4
import pytest
from app.application.use_cases.get_execution import GetExecution, snapshot_projection
from app.application.use_cases.create_manual_execution import CreateManualExecution
from app.domain.errors import NotFoundError
from tests.unit.test_create_manual_execution import setup
from tests.unit.test_mining_execution import NOW


def test_get_safe_snapshot_duration_and_not_found():
    uow, config = setup()
    item = CreateManualExecution(uow, clock=lambda: NOW).execute(config.id)
    assert GetExecution(uow).execute(item.id).duration_seconds == 0
    snapshot = snapshot_projection(item.snapshot)
    assert set(snapshot) == {'configuration_id','configuration_name','configuration_enabled','gitlab_url','configuration_revision','scope'}
    with pytest.raises(NotFoundError):
        GetExecution(uow).execute(uuid4())
