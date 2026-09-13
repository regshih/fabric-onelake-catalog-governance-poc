from pathlib import Path

import pytest

from onelake_governance.bootstrap import bootstrap_demo
from onelake_governance.client import FabricApiError


class Client:
    def __init__(self, state="Active"):
        self.state = state
        self.writes = []

    def workspaces(self):
        return []

    def capacities(self):
        return [{"id": "capacity-id", "displayName": "Capacity", "state": self.state}]

    @staticmethod
    def named(objects, name, object_type=None):
        return next(
            (
                obj
                for obj in objects
                if obj.get("displayName", "").casefold() == name.casefold()
                and (object_type is None or obj.get("type") == object_type)
            ),
            None,
        )


class Response:
    def __init__(self, body=None, status_code=201, headers=None):
        self.body = body or {}
        self.status_code = status_code
        self.headers = headers or {}
        self.content = b"x"


class ApplyingClient(Client):
    def __init__(self):
        super().__init__()
        self.workspace_values = []
        self.item_values = []

    def workspaces(self):
        return self.workspace_values

    def items(self, _workspace_id):
        return self.item_values

    def list_all(self, path):
        assert path == "domains"
        return [{"id": "domain-id", "displayName": "Approved"}]

    def request(self, method, path, **kwargs):
        self.writes.append((method, path, kwargs))
        if path == "workspaces":
            body = {
                "id": "workspace-id",
                "displayName": kwargs["json"]["displayName"],
                "description": kwargs["json"]["description"],
            }
            self.workspace_values.append(body)
            return Response(body)
        if path in {
            "workspaces/workspace-id/items",
            "workspaces/workspace-id/dataPipelines",
        }:
            payload = kwargs["json"]
            item_type = payload.get("type", "DataPipeline")
            body = {
                "id": f"{payload['displayName']}-id",
                "displayName": payload["displayName"],
                "description": payload["description"],
                "type": item_type,
            }
            self.item_values.append(body)
            return Response(body)
        if "/jobs/execute/instances" in path:
            return Response({}, status_code=202, headers={"Location": "poll"})
        return Response({})

    @staticmethod
    def wait_for_operation(response, timeout=None):
        if response.body:
            return response.body
        return {"status": "Completed"}


def test_bootstrap_dry_run_plans_without_writes():
    client = Client()
    result = bootstrap_demo(
        client,
        workspace_name="Demo",
        capacity_name="Capacity",
        root=Path.cwd(),
    )
    assert result["mode"] == "dry-run"
    assert result["workspace_status"] == "planned"
    assert len(result["items"]) == 4
    assert client.writes == []


def test_bootstrap_refuses_inactive_capacity_even_in_dry_run():
    with pytest.raises(FabricApiError, match="not active"):
        bootstrap_demo(
            Client(state="Inactive"),
            workspace_name="Demo",
            capacity_name="Capacity",
            root=Path.cwd(),
        )


def test_bootstrap_apply_creates_items_assigns_domain_and_runs_seed():
    client = ApplyingClient()
    result = bootstrap_demo(
        client,
        workspace_name="Demo",
        capacity_name="Capacity",
        domain_name="Approved",
        root=Path.cwd(),
        apply=True,
        run_seed=True,
    )
    assert result["workspace_status"] == "created"
    assert result["domain_status"] == "assigned"
    assert result["seed_status"] == "completed"
    assert len(result["items"]) == 4
    pipeline_create = next(
        call for call in client.writes if call[1] == "workspaces/workspace-id/dataPipelines"
    )
    encoded = str(pipeline_create[2]["json"])
    assert "{{" not in encoded
