import pytest


@pytest.fixture
def scope_uow_factory(pg_uow_factory):
    """Provide a PostgreSQL-backed Unit of Work after Alembic has reached head."""
    return pg_uow_factory
