from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings


@lru_cache
def build_session_factory():
    engine = create_engine(get_settings().database_url, pool_pre_ping=True)
    return sessionmaker(bind=engine, class_=Session, expire_on_commit=False)


def begin_execution_snapshot(session: Session) -> None:
    """Use one consistent view for configuration and selected scope during creation."""
    session.connection(execution_options={'isolation_level': 'REPEATABLE READ'})
