from collections.abc import Generator

import httpx

from app.config import get_settings
from app.infrastructure.crypto.fernet_credential_cipher import FernetCredentialCipher
from app.infrastructure.database.session import build_session_factory
from app.infrastructure.database.sqlalchemy_repositories import SqlAlchemyUnitOfWork
from app.infrastructure.gitlab.http_gitlab_connection_client import HttpGitLabConnectionClient
from app.infrastructure.gitlab.http_gitlab_repository_client import HttpGitLabRepositoryClient
from app.domain.errors import CredentialServiceUnavailable


def get_uow() -> Generator[SqlAlchemyUnitOfWork, None, None]:
    factory = build_session_factory()
    session = factory()
    try: yield SqlAlchemyUnitOfWork(session)
    finally: session.close()


def get_credential_cipher():
    try:
        return FernetCredentialCipher(get_settings().gitlab_encryption_key_ring)
    except CredentialServiceUnavailable:
        return None


def get_gitlab_client():
    settings = get_settings()
    timeout = httpx.Timeout(
        connect=settings.gitlab_connect_timeout_seconds,
        read=settings.gitlab_read_timeout_seconds,
        write=settings.gitlab_write_timeout_seconds,
        pool=settings.gitlab_pool_timeout_seconds,
    )
    return HttpGitLabConnectionClient(timeout)


def get_gitlab_repository_client():
    settings = get_settings()
    timeout = httpx.Timeout(connect=settings.gitlab_connect_timeout_seconds,
        read=settings.gitlab_read_timeout_seconds, write=settings.gitlab_write_timeout_seconds,
        pool=settings.gitlab_pool_timeout_seconds)
    return HttpGitLabRepositoryClient(timeout, max_tree_entries=settings.repository_mining_max_tree_entries)


def get_mining_worker_uow_factory():
    factory = build_session_factory()
    return lambda: SqlAlchemyUnitOfWork(factory())
