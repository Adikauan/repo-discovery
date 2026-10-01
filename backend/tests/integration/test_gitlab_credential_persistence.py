from datetime import UTC, datetime
from uuid import uuid4

from app.domain.monitoring_configuration import MonitoringConfiguration


def test_encrypted_credential_round_trip_and_cas(pg_uow_factory):
    identifier = uuid4(); now = datetime(2026, 9, 28, tzinfo=UTC)
    first = pg_uow_factory(); first.configuration_repository.add(MonitoringConfiguration.create(
        identifier=identifier, name="CAS", gitlab_url="https://gitlab.example", now=now)); first.commit()
    uow = pg_uow_factory(); assert uow.credential_repository.replace(identifier, b"cipher-one", None, now); uow.commit()
    left, right = pg_uow_factory(), pg_uow_factory()
    assert left.credential_repository.get(identifier).revision == right.credential_repository.get(identifier).revision == 1
    assert left.credential_repository.replace(identifier, b"cipher-two", 1, now); left.commit()
    assert not right.credential_repository.replace(identifier, b"cipher-stale", 1, now); right.rollback()
    final = pg_uow_factory().credential_repository.get(identifier)
    assert final.revision == 2 and final.encrypted_token == b"cipher-two"
