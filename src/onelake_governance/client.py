"""Small, testable Microsoft Fabric REST client with passwordless authentication."""

from __future__ import annotations

import email.utils
import re
import time
from collections.abc import Callable, Iterator, Mapping
from datetime import UTC, datetime
from typing import Any
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

import requests
from azure.identity import DefaultAzureCredential

FABRIC_API = "https://api.fabric.microsoft.com/v1"
FABRIC_SCOPE = "https://api.fabric.microsoft.com/.default"
TERMINAL_SUCCESS = frozenset({"Succeeded", "Completed", "Deduped"})
TERMINAL_FAILURE = frozenset({"Failed", "Cancelled", "Canceled"})


class FabricApiError(RuntimeError):
    """A Fabric request or long-running operation failed."""


def _retry_seconds(value: str | None, default: float) -> float:
    if not value:
        return default
    try:
        return max(0.0, float(value))
    except ValueError:
        try:
            parsed = email.utils.parsedate_to_datetime(value)
            return max(0.0, (parsed - datetime.now(UTC)).total_seconds())
        except (TypeError, ValueError):
            return default


def _with_continuation_token(url: str, token: str) -> str:
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query["continuationToken"] = token
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


class FabricClient:
    """Fabric REST client that never persists tokens or environment identifiers."""

    def __init__(
        self,
        credential: Any | None = None,
        *,
        session: requests.Session | None = None,
        base_url: str = FABRIC_API,
        request_timeout: float = 60,
        poll_interval: float = 5,
        lro_timeout: float = 1800,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
        epoch: Callable[[], float] = time.time,
    ) -> None:
        self.credential = credential or DefaultAzureCredential()
        self.session = session or requests.Session()
        self.base_url = base_url.rstrip("/")
        self.request_timeout = request_timeout
        self.poll_interval = poll_interval
        self.lro_timeout = lro_timeout
        self._sleep = sleep
        self._monotonic = monotonic
        self._epoch = epoch
        self._expires_on = 0.0

    def _authorize(self, *, force: bool = False) -> None:
        if not force and self._expires_on - self._epoch() > 300:
            return
        token = self.credential.get_token(FABRIC_SCOPE)
        self._expires_on = float(getattr(token, "expires_on", self._epoch() + 300))
        self.session.headers.update(
            {"Authorization": f"Bearer {token.token}", "Content-Type": "application/json"}
        )

    def url(self, path_or_url: str) -> str:
        if path_or_url.startswith(("https://", "http://")):
            return path_or_url
        return f"{self.base_url}/{path_or_url.lstrip('/')}"

    def request(self, method: str, path_or_url: str, **kwargs: Any) -> requests.Response:
        self._authorize()
        kwargs.setdefault("timeout", self.request_timeout)
        response = self.session.request(method, self.url(path_or_url), **kwargs)
        if response.status_code == 401:
            self._authorize(force=True)
            response = self.session.request(method, self.url(path_or_url), **kwargs)
        try:
            response.raise_for_status()
        except requests.HTTPError:
            # Do not echo response bodies: service errors can contain tenant-scoped identifiers.
            error_code = ""
            try:
                candidate = str(response.json().get("errorCode", ""))
                if re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", candidate):
                    error_code = f" ({candidate})"
            except (AttributeError, ValueError):
                pass
            raise FabricApiError(
                f"Fabric {method.upper()} request failed with HTTP {response.status_code}{error_code}"
            ) from None
        return response

    def optional_json(self, path: str) -> tuple[dict[str, Any] | None, str | None]:
        """Read an optional capability and return a privacy-safe reason if unavailable."""
        try:
            response = self.request("GET", path)
            body = response.json() if response.content else {}
            return (body if isinstance(body, dict) else {"value": body}), None
        except FabricApiError as exc:
            return None, str(exc)

    def pages(self, path_or_url: str) -> Iterator[Mapping[str, Any]]:
        url = self.url(path_or_url)
        while url:
            response = self.request("GET", url)
            body = response.json()
            if not isinstance(body, Mapping):
                raise FabricApiError("Fabric list response was not a JSON object")
            yield body
            continuation_uri = body.get("continuationUri")
            if continuation_uri:
                url = urljoin(url, str(continuation_uri))
            elif body.get("continuationToken"):
                url = _with_continuation_token(url, str(body["continuationToken"]))
            else:
                url = ""

    def list_all(self, path_or_url: str, *, key: str = "value") -> list[dict[str, Any]]:
        return [dict(item) for page in self.pages(path_or_url) for item in page.get(key, [])]

    @staticmethod
    def json(response: requests.Response) -> dict[str, Any]:
        if not response.content:
            return {}
        body = response.json()
        return body if isinstance(body, dict) else {"value": body}

    def wait_for_operation(
        self, response: requests.Response, *, timeout: float | None = None
    ) -> dict[str, Any]:
        if response.status_code != 202:
            return self.json(response)
        location = response.headers.get("Location")
        if not location:
            raise FabricApiError("Fabric returned 202 without a Location header")
        deadline = self._monotonic() + (self.lro_timeout if timeout is None else timeout)
        delay = _retry_seconds(response.headers.get("Retry-After"), self.poll_interval)
        last: dict[str, Any] = {}
        while self._monotonic() < deadline:
            self._sleep(min(delay, max(0.0, deadline - self._monotonic())))
            poll = self.request("GET", location)
            last = self.json(poll)
            status = str(last.get("status", ""))
            if status in TERMINAL_FAILURE:
                raise FabricApiError(f"Fabric operation ended with status {status}")
            if status in TERMINAL_SUCCESS:
                result_url = last.get("resultUrl") or poll.headers.get("Location")
                if result_url:
                    return self.json(self.request("GET", str(result_url))) or last
                return last
            delay = _retry_seconds(poll.headers.get("Retry-After"), self.poll_interval)
        raise TimeoutError("Fabric operation did not finish before the configured timeout")

    def workspaces(self) -> list[dict[str, Any]]:
        return self.list_all("workspaces")

    def capacities(self) -> list[dict[str, Any]]:
        return self.list_all("capacities")

    def items(self, workspace_id: str) -> list[dict[str, Any]]:
        return self.list_all(f"workspaces/{workspace_id}/items")

    @staticmethod
    def named(
        objects: list[dict[str, Any]], name: str, object_type: str | None = None
    ) -> dict[str, Any] | None:
        matches = [
            obj
            for obj in objects
            if str(obj.get("displayName", "")).casefold() == name.casefold()
            and (object_type is None or obj.get("type") == object_type)
        ]
        if len(matches) > 1:
            raise FabricApiError(f"More than one {object_type or 'object'} has the requested name")
        return matches[0] if matches else None
