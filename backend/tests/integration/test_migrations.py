from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def test_migration_upgrade_and_downgrade(test_database_url, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", test_database_url)
    from app.config import get_settings
    get_settings.cache_clear()
    config = Config("alembic.ini")
    command.upgrade(config, "head")
    engine = create_engine(test_database_url)
    assert 'mining_executions' in inspect(engine).get_table_names()
    indexes = inspect(engine).get_indexes('mining_executions')
    assert any(i['name'] == 'uq_execution_active_configuration' and i['unique'] for i in indexes)
    command.check(config)
    command.downgrade(config, "base")
    assert 'mining_executions' not in inspect(engine).get_table_names()
    engine.dispose()
