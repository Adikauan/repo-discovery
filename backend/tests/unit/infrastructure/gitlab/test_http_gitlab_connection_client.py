import httpx

from app.infrastructure.gitlab.http_gitlab_connection_client import HttpGitLabConnectionClient


def client(handler):
    return HttpGitLabConnectionClient(httpx.Timeout(connect=5, read=10, write=5, pool=5), httpx.MockTransport(handler))


def test_adapter_uses_only_user_endpoint_private_header_and_preserves_base_path():
    seen = {}
    def handler(request):
        seen["url"] = str(request.url); seen["token"] = request.headers.get("PRIVATE-TOKEN")
        return httpx.Response(200, json={"id": 1})
    result = client(handler).validate("https://gitlab.example/root/", "sentinel")
    assert result.outcome == "success"
    assert seen == {"url": "https://gitlab.example/root/api/v4/user", "token": "sentinel"}


def test_adapter_normalizes_statuses_and_never_returns_provider_body():
    for status, expected in [(401, "invalid_credentials"), (403, "forbidden"), (429, "rate_limited"), (503, "provider_unavailable")]:
        result = client(lambda request, status=status: httpx.Response(status, text="secret upstream body")).validate("https://gitlab.example", "token")
        assert result.outcome == expected and "secret" not in result.message
    assert client(lambda request: httpx.Response(200, json={})).validate("https://gitlab.example", "token").outcome == "invalid_response"
    assert client(lambda request: (_ for _ in ()).throw(httpx.ReadTimeout("x"))).validate("https://gitlab.example", "token").outcome == "timeout"
