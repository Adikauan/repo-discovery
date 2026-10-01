from __future__ import annotations

from collections.abc import Iterator
import os

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://unused:unused@localhost/unused")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:5173")

import pytest


@pytest.fixture
def utc_clock():
    from datetime import UTC, datetime

    return lambda: datetime(2026, 9, 28, 12, 0, tzinfo=UTC)


@pytest.fixture
def gitlab_node_factory():
    """Build provider-independent normalized hierarchy rows for scope tests."""
    def build(identifier: int, kind: str = "group", *, name: str | None = None,
              full_path: str | None = None, parent_group_id: int | None = None):
        return {
            "id": identifier,
            "type": kind,
            "name": name or f"node-{identifier}",
            "full_path": full_path or f"namespace/node-{identifier}",
            "parent_group_id": parent_group_id,
            "expandable": kind == "group",
        }
    return build


@pytest.fixture
def gitlab_page_factory():
    """Build a controlled GitLab REST page and its pagination header."""
    def build(items, next_page: str = ""):
        return {"json": list(items), "headers": {"X-Next-Page": next_page}}
    return build


@pytest.fixture
def author_policy_payload_factory():
    """Build scope-bound policy payloads without embedding GitLab credentials."""
    def build(*, configuration_id="configuration-1", scope_type="repository_branch",
              gitlab_id=42, branch="main", allowed_author_emails=()):
        payload = {
            "monitoring_configuration_id": configuration_id,
            "scope_type": scope_type,
            "gitlab_id": gitlab_id,
            "allowed_author_emails": list(allowed_author_emails),
        }
        if scope_type == "repository_branch":
            payload["branch"] = branch
        return payload
    return build


@pytest.fixture
def gitlab_branch_factory():
    """Build provider-independent normalized branch rows for policy tests."""
    def build(name: str, *, commit_sha: str = "a" * 40, default: bool = False):
        return {"name": name, "commit_sha": commit_sha, "default": default}
    return build


@pytest.fixture
def test_database_url() -> Iterator[str]:
    """Integration tests require a dedicated PostgreSQL database configured by the caller."""
    import os

    value = os.getenv("TEST_DATABASE_URL")
    if not value:
        pytest.skip("Set TEST_DATABASE_URL to a dedicated PostgreSQL test database")
    yield value


@pytest.fixture
def pg_uow_factory(test_database_url):
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.config import get_settings
    from app.infrastructure.database.sqlalchemy_repositories import SqlAlchemyUnitOfWork

    os.environ["DATABASE_URL"] = test_database_url
    get_settings.cache_clear()
    config = Config("alembic.ini")
    command.upgrade(config, "head")
    engine = create_engine(test_database_url)
    factory = sessionmaker(engine, expire_on_commit=False)
    opened = []
    def create_uow():
        uow = SqlAlchemyUnitOfWork(factory())
        opened.append(uow)
        return uow
    try:
        yield create_uow
    finally:
        for uow in opened:
            uow.session.close()
        command.downgrade(config, "base")
        engine.dispose()
