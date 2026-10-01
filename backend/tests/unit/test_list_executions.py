from dataclasses import replace
from uuid import UUID
import pytest
from app.application.use_cases.list_executions import ListExecutions, ListConfigurationExecutions
from app.application.use_cases.create_manual_execution import CreateManualExecution
from app.domain.errors import FieldValidationError, NotFoundError
from tests.unit.test_create_manual_execution import setup
from tests.unit.test_mining_execution import NOW


def test_filters_ties_pages_and_retired_history():
    uow, config = setup()
    original = CreateManualExecution(uow, clock=lambda: NOW).execute(config.id)
    uow.executions = {UUID(int=i): replace(original, id=UUID(int=i)) for i in range(1, 4)}
    result = ListExecutions(uow).execute(page=1, page_size=2, status='completed', trigger_type='manual')
    assert [i.id.int for i in result.items] == [3, 2] and result.total_items == 3 and result.total_pages == 2
    assert len(ListExecutions(uow).execute(status='failed').items) == 0
    assert ListExecutions(uow).execute(page=2, page_size=2).items[0].id.int == 1
    uow.configurations[config.id] = config.retire(NOW)
    assert ListConfigurationExecutions(uow).execute(config.id).total_items == 3
    with pytest.raises(NotFoundError):
        ListConfigurationExecutions(uow).execute(UUID(int=0))


@pytest.mark.parametrize('page,size', [(0, 1), (1, 0), (1, 101)])
def test_page_bounds(page, size):
    uow, _ = setup()
    with pytest.raises(FieldValidationError):
        ListExecutions(uow).execute(page=page, page_size=size)
