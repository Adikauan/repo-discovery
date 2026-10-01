from dataclasses import dataclass
from math import ceil
from app.domain.entities.mining_execution import MiningExecution, ExecutionStatus, TriggerType
from app.domain.errors import FieldValidationError, NotFoundError


@dataclass(frozen=True)
class ExecutionPage:
    items: list[MiningExecution]
    page: int
    page_size: int
    total_items: int

    @property
    def total_pages(self):
        return ceil(self.total_items / self.page_size)


class ListExecutions:
    def __init__(self, uow):
        self.uow = uow

    def execute(self, *, page=1, page_size=25, configuration_id=None, status=None, trigger_type=None):
        if type(page) is not int or page < 1 or type(page_size) is not int or not 1 <= page_size <= 100:
            raise FieldValidationError('page', 'invalid', 'Choose a valid page and page size between 1 and 100.')
        try:
            status = ExecutionStatus(status) if status is not None else None
            trigger_type = TriggerType(trigger_type) if trigger_type is not None else None
        except ValueError:
            raise FieldValidationError('filter', 'invalid', 'Choose a supported execution filter.') from None
        items, total = self.uow.execution_repository.page(page=page, page_size=page_size,
            configuration_id=configuration_id, status=status, trigger_type=trigger_type)
        return ExecutionPage(items, page, page_size, total)


class ListConfigurationExecutions(ListExecutions):
    def execute(self, configuration_id, **filters):
        if self.uow.configuration_repository.get(configuration_id) is None:
            raise NotFoundError('Monitoring Configuration not found.')
        return super().execute(configuration_id=configuration_id, **filters)
