from dataclasses import dataclass

import pytest
import requests

from onelake_governance.client import FabricApiError, FabricClient, _retry_seconds


@dataclass
class Token:
    token: str = "runtime-token"  # noqa: S105 - inert unit-test credential object
    expires_on: float = 99999999999


class Credential:
    def __init__(self):
        self.calls = 0

    def get_token(self, _scope):
        self.calls += 1
        return Token()


class Response:
    def __init__(self, body=None, status=200, headers=None, text=b"x"):
        self._body = body or {}
        self.status_code = status
        self.headers = headers or {}
        self.content = text

    def json(self):
        return self._body

    def raise_for_status(self):
        if self.status_code >= 400:
            error = requests.HTTPError("private service body")
            error.response = self
            raise error


class Session:
    def __init__(self, responses):
        self.responses = list(responses)
        self.headers = {}
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        return self.responses.pop(0)


def test_auth_is_cached_and_request_uses_base_url():
    credential = Credential()
    session = Session([Response(), Response()])
    client = FabricClient(credential, session=session, epoch=lambda: 1)
    client.request("GET", "workspaces")
    client.request("GET", "capacities")
    assert credential.calls == 1
    assert session.headers["Authorization"] == "Bearer runtime-token"
    assert session.calls[0][1].endswith("/workspaces")


def test_error_does_not_echo_service_body():
    client = FabricClient(Credential(), session=Session([Response(status=403)]), epoch=lambda: 1)
    with pytest.raises(FabricApiError, match="HTTP 403") as exc:
        client.request("GET", "private")
    assert "private service body" not in str(exc.value)


def test_pages_follow_continuation_token():
    session = Session(
        [
            Response({"value": [{"name": "a"}], "continuationToken": "next"}),
            Response({"value": [{"name": "b"}]}),
        ]
    )
    client = FabricClient(Credential(), session=session, epoch=lambda: 1)
    assert [item["name"] for item in client.list_all("items")] == ["a", "b"]
    assert "continuationToken=next" in session.calls[1][1]


def test_wait_for_operation_returns_result():
    session = Session(
        [
            Response({"status": "Succeeded", "resultUrl": "https://result"}),
            Response({"id": "private-id"}),
        ]
    )
    client = FabricClient(
        Credential(),
        session=session,
        sleep=lambda _value: None,
        monotonic=lambda: 0,
        epoch=lambda: 1,
    )
    initial = Response(status=202, headers={"Location": "https://poll", "Retry-After": "0"})
    assert client.wait_for_operation(initial) == {"id": "private-id"}


def test_optional_json_returns_safe_reason():
    client = FabricClient(Credential(), session=Session([Response(status=404)]), epoch=lambda: 1)
    body, reason = client.optional_json("missing")
    assert body is None
    assert reason == "Fabric GET request failed with HTTP 404"


def test_retry_parsing_defaults_on_invalid_value():
    assert _retry_seconds("2", 5) == 2
    assert _retry_seconds("invalid", 5) == 5
    assert _retry_seconds(None, 5) == 5


def test_named_is_case_insensitive_and_rejects_duplicates():
    values = [{"displayName": "Demo", "type": "Lakehouse"}]
    assert FabricClient.named(values, "demo", "Lakehouse") == values[0]
    with pytest.raises(FabricApiError, match="More than one"):
        FabricClient.named(values * 2, "demo")
