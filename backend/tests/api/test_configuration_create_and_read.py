from fastapi.testclient import TestClient

from app.api.dependencies import get_uow
from app.api.main import create_app
from tests.fakes import MemoryUnitOfWork


def test_create_without_identifier_generates_id_and_reads_back_configuration():
    uow = MemoryUnitOfWork()
    app = create_app()
    app.dependency_overrides[get_uow] = lambda: uow
    client = TestClient(app)
    response = client.post("/api/v1/monitoring-configurations", json={
        "name": "  API configuration ", "description": "  optional context ",
        "gitlab_url": " https://gitlab.example.com ",
    })
    assert response.status_code == 201
    body = response.json()
    assert body["id"] and body["enabled"] is False
    assert body["name"] == "API configuration"
    assert body["description"] == "optional context"
    assert body["gitlab_url"] == "https://gitlab.example.com"
    assert client.get(f"/api/v1/monitoring-configurations/{body['id']}").json() == body
    listed = client.get("/api/v1/monitoring-configurations").json()
    assert len(listed["items"]) == 1
    assert {key: value for key, value in listed["items"][0].items() if key != "scheduleSummary"} == body
    assert listed["items"][0]["scheduleSummary"] is None
    assert response.headers["location"] == f"/api/v1/monitoring-configurations/{body['id']}"


def test_client_identifier_is_rejected_and_keyed_request_replays():
    uow = MemoryUnitOfWork()
    app = create_app()
    app.dependency_overrides[get_uow] = lambda: uow
    client = TestClient(app)
    payload = {"name": "Idempotent", "gitlab_url": "https://gitlab.example.com"}
    invalid = client.post("/api/v1/monitoring-configurations", json={**payload, "id": "client-id"})
    assert invalid.status_code == 422
    first = client.post("/api/v1/monitoring-configurations", headers={"Idempotency-Key": "attempt-1"}, json=payload)
    replay = client.post("/api/v1/monitoring-configurations", headers={"Idempotency-Key": "attempt-1"}, json=payload)
    assert first.status_code == 201 and replay.status_code == 201
    assert first.json()["id"] == replay.json()["id"]
    assert len(uow.configurations) == 1
    assert client.post("/api/v1/monitoring-configurations", headers={"Idempotency-Key": "bad key"}, json=payload).status_code == 400


def test_invalid_normalized_fields_and_unknown_configuration_have_safe_problem_details():
    app = create_app(); app.dependency_overrides[get_uow] = lambda: MemoryUnitOfWork()
    client = TestClient(app)
    blank_name = client.post("/api/v1/monitoring-configurations", json={"name": "  ", "gitlab_url": "https://gitlab.example"})
    bad_url = client.post("/api/v1/monitoring-configurations", json={"name": "Valid", "gitlab_url": "ftp://gitlab.example"})
    missing = client.get("/api/v1/monitoring-configurations/00000000-0000-0000-0000-000000000001")
    assert blank_name.status_code == bad_url.status_code == 422
    assert blank_name.headers["content-type"].startswith("application/problem+json")
    assert missing.status_code == 404 and "stack" not in missing.text.lower()


def test_api_starts_without_creating_schema_and_serves_health():
    client = TestClient(create_app())
    assert client.get("/health").json() == {"status": "ok"}


def test_create_rejects_url_credentials_without_echoing_them():
    app = create_app()
    uow = MemoryUnitOfWork()
    app.dependency_overrides[get_uow] = lambda: uow
    client = TestClient(app)
    secret = "private-token-value"
    response = client.post("/api/v1/monitoring-configurations", json={
        "name": "Secure URL", "gitlab_url": f"https://user:{secret}@gitlab.example.com",
    })
    assert response.status_code == 422
    assert "credentials" in response.json()["detail"].lower()
    assert secret not in response.text
    assert "user" not in response.text
    assert uow.configurations == {}


def test_allowed_author_policy_is_normalized_and_included_in_idempotency():
    uow = MemoryUnitOfWork(); app = create_app(scheduler_enabled=False)
    app.dependency_overrides[get_uow] = lambda: uow
    client = TestClient(app)
    payload = {"name": "Authors", "gitlab_url": "https://gitlab.example.com",
               "allowed_author_emails": [" Alice@Example.com ", "bob@example.com"]}
    first = client.post("/api/v1/monitoring-configurations", headers={"Idempotency-Key": "authors-1"}, json=payload)
    replay = client.post("/api/v1/monitoring-configurations", headers={"Idempotency-Key": "authors-1"},
        json={**payload, "allowed_author_emails": ["BOB@example.com", "alice@example.com"]})
    assert first.status_code == replay.status_code == 201
    assert first.json()["allowed_author_emails"] == ["alice@example.com", "bob@example.com"]
    assert first.json()["id"] == replay.json()["id"]
    invalid = client.post("/api/v1/monitoring-configurations", json={"name": "Invalid",
        "gitlab_url": "https://gitlab.example.com", "allowed_author_emails": ["nope"]})
    assert invalid.status_code == 422 and "nope" not in invalid.text
