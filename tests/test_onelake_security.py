import copy

import pytest

from onelake_governance.client import FabricApiError
from onelake_governance.onelake_security import (
    apply_policy_role,
    merged_roles,
    remove_named_role,
    role_from_policy,
    roles_without,
)


def test_role_merge_preserves_unrelated_unknown_fields_and_does_not_mutate():
    current = [
        {
            "id": "server-only",
            "name": "DefaultReader",
            "kind": "Policy",
            "decisionRules": [{"effect": "Permit", "permission": []}],
            "members": {"fabricItemMembers": []},
            "futureServerField": "preserve-in-memory-but-not-request",
        }
    ]
    original = copy.deepcopy(current)
    desired = {
        "name": "PublicMetricsReader",
        "kind": "Policy",
        "decisionRules": [{"effect": "Permit", "permission": []}],
        "members": {"microsoftEntraMembers": []},
    }
    payload = merged_roles(current, desired)
    assert current == original
    assert [role["name"] for role in payload["value"]] == ["DefaultReader", "PublicMetricsReader"]
    assert "futureServerField" not in payload["value"][0]
    assert payload["value"][0]["members"] == {"fabricItemMembers": []}


def test_existing_named_role_is_replaced_once():
    desired = {"name": "Readers", "kind": "Policy", "decisionRules": [], "members": {}}
    payload = merged_roles([{"name": "Readers", "kind": "Policy", "decisionRules": []}], desired)
    assert payload["value"] == [desired]


def test_duplicate_named_role_fails_closed():
    with pytest.raises(FabricApiError, match="Multiple"):
        merged_roles([{"name": "Readers"}, {"name": "Readers"}], {"name": "Readers"})


def test_remove_role_preserves_every_other_writable_role_field():
    current = [
        {"name": "DefaultReader", "kind": "Policy", "decisionRules": [], "members": {}},
        {
            "name": "Restricted",
            "kind": "Policy",
            "decisionRules": [{"effect": "Permit"}],
            "members": {"microsoftEntraMembers": []},
            "serverOnly": "not writable",
        },
    ]

    payload = roles_without(current, "DefaultReader")

    assert payload == {
        "value": [
            {
                "name": "Restricted",
                "kind": "Policy",
                "decisionRules": [{"effect": "Permit"}],
                "members": {"microsoftEntraMembers": []},
            }
        ]
    }
    assert roles_without(current, "Missing") is None


def test_remove_duplicate_named_role_fails_closed():
    with pytest.raises(FabricApiError, match="Multiple"):
        roles_without([{"name": "Readers"}, {"name": "Readers"}], "Readers")


def test_role_reads_group_ids_from_environment_without_returning_them(monkeypatch):
    monkeypatch.setenv("GROUP_ID", "group-private")
    monkeypatch.setenv("TENANT_ID", "tenant-private")
    role = role_from_policy(
        {
            "name": "Readers",
            "member_group_env": "GROUP_ID",
            "tenant_id_env": "TENANT_ID",
            "paths": ["/Tables/public_metrics"],
        }
    )
    assert role["members"]["microsoftEntraMembers"][0]["objectId"] == "group-private"
    assert role["decisionRules"][0]["permission"][0]["attributeValueIncludedIn"] == [
        "/Tables/public_metrics"
    ]


def test_role_preserves_complete_rls_and_cls_constraints(monkeypatch):
    monkeypatch.setenv("GROUP_ID", "group-private")
    monkeypatch.setenv("TENANT_ID", "tenant-private")
    role = role_from_policy(
        {
            "name": "RestrictedReaders",
            "member_group_env": "GROUP_ID",
            "tenant_id_env": "TENANT_ID",
            "paths": ["/Tables/restricted_customer_metrics"],
            "row_constraints": [
                {
                    "tablePath": "/Tables/restricted_customer_metrics",
                    "value": (
                        "SELECT * FROM [restricted_customer_metrics] WHERE [region] = 'US'"
                    ),
                }
            ],
            "column_constraints": [
                {
                    "tablePath": "/Tables/restricted_customer_metrics",
                    "columnNames": ["customer_id", "region"],
                    "columnEffect": "Permit",
                    "columnAction": ["Read"],
                }
            ],
        }
    )
    constraints = role["decisionRules"][0]["constraints"]
    assert constraints["rows"][0]["value"].startswith("SELECT * FROM")
    assert constraints["columns"][0]["columnNames"] == ["customer_id", "region"]


def test_role_requires_explicit_paths_and_environment(monkeypatch):
    monkeypatch.delenv("MISSING", raising=False)
    with pytest.raises(FabricApiError, match="Set MISSING"):
        role_from_policy(
            {
                "name": "Readers",
                "member_group_env": "MISSING",
                "tenant_id_env": "MISSING",
                "paths": ["/Tables/public_metrics"],
            }
        )


def test_role_rejects_predicate_only_rls(monkeypatch):
    monkeypatch.setenv("GROUP_ID", "group-private")
    monkeypatch.setenv("TENANT_ID", "tenant-private")
    with pytest.raises(FabricApiError, match="complete SELECT"):
        role_from_policy(
            {
                "name": "Readers",
                "member_group_env": "GROUP_ID",
                "tenant_id_env": "TENANT_ID",
                "paths": ["/Tables/restricted_customer_metrics"],
                "row_constraints": [
                    {
                        "tablePath": "/Tables/restricted_customer_metrics",
                        "value": "[region] = 'US'",
                    }
                ],
            }
        )


class Response:
    status_code = 200
    content = b"x"
    headers = {"ETag": '"current"'}

    @staticmethod
    def json():
        return {"value": [{"name": "DefaultReader", "decisionRules": [], "members": {}}]}


class Client:
    def __init__(self):
        self.calls = []

    @staticmethod
    def workspaces():
        return [{"id": "workspace-id", "displayName": "Demo"}]

    @staticmethod
    def items(_workspace_id):
        return [{"id": "lakehouse-id", "displayName": "Lake", "type": "Lakehouse"}]

    @staticmethod
    def named(objects, name, object_type=None):
        return next(
            (
                obj
                for obj in objects
                if obj["displayName"] == name
                and (object_type is None or obj.get("type") == object_type)
            ),
            None,
        )

    def request(self, method, path, **kwargs):
        self.calls.append((method, path, kwargs))
        return Response()

    @staticmethod
    def json(response):
        return response.json()


def test_apply_role_always_server_dry_runs_and_redacts_ids(monkeypatch):
    monkeypatch.setenv("GROUP_ID", "group-private")
    monkeypatch.setenv("TENANT_ID", "tenant-private")
    client = Client()
    result = apply_policy_role(
        client,
        "Demo",
        "Lake",
        {
            "name": "Readers",
            "member_group_env": "GROUP_ID",
            "tenant_id_env": "TENANT_ID",
            "paths": ["/Tables/public_metrics"],
        },
        apply=True,
    )
    assert [call[0] for call in client.calls] == ["GET", "PUT", "PUT"]
    assert client.calls[1][1].endswith("?dryRun=true")
    assert client.calls[1][2]["json"] == client.calls[2][2]["json"]
    assert "group-private" not in str(result)
    assert "tenant-private" not in str(result)


def test_remove_role_always_server_dry_runs_and_preserves_other_roles():
    client = Client()
    result = remove_named_role(client, "Demo", "Lake", "DefaultReader", apply=True)

    assert [call[0] for call in client.calls] == ["GET", "PUT", "PUT"]
    assert client.calls[1][1].endswith("?dryRun=true")
    assert client.calls[1][2]["json"] == {"value": []}
    assert client.calls[1][2]["json"] == client.calls[2][2]["json"]
    assert result["role_count_preserved"] == 0


def test_remove_role_preview_never_applies():
    client = Client()
    result = remove_named_role(client, "Demo", "Lake", "DefaultReader")

    assert [call[0] for call in client.calls] == ["GET", "PUT"]
    assert client.calls[1][1].endswith("?dryRun=true")
    assert result["mode"] == "server-dry-run"


def test_remove_missing_role_is_idempotent_no_op():
    class MissingRoleResponse(Response):
        @staticmethod
        def json():
            return {"value": [{"name": "Other", "decisionRules": [], "members": {}}]}

    class MissingRoleClient(Client):
        def request(self, method, path, **kwargs):
            self.calls.append((method, path, kwargs))
            return MissingRoleResponse()

    client = MissingRoleClient()
    result = remove_named_role(client, "Demo", "Lake", "DefaultReader", apply=True)

    assert [call[0] for call in client.calls] == ["GET"]
    assert result["mode"] == "no-op"


def test_remove_role_fails_closed_without_etag():
    class NoEtagResponse(Response):
        headers = {}

    class NoEtagClient(Client):
        def request(self, method, path, **kwargs):
            self.calls.append((method, path, kwargs))
            return NoEtagResponse()

    with pytest.raises(FabricApiError, match="no ETag"):
        remove_named_role(NoEtagClient(), "Demo", "Lake", "DefaultReader", apply=True)
