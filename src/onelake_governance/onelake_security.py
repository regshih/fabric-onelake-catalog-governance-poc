"""Safely merge policy-defined OneLake security roles using ETags and server dry-run."""

from __future__ import annotations

import copy
import os
import re
from typing import Any

from .client import FabricApiError, FabricClient

WRITABLE_ROLE_FIELDS = ("name", "kind", "decisionRules", "members")
RLS_STATEMENT = re.compile(r"^SELECT\s+\*\s+FROM\s+.+\s+WHERE\s+.+$", re.IGNORECASE | re.DOTALL)


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value or value.startswith("<"):
        raise FabricApiError(f"Set {name} in the process environment; do not commit the value")
    return value


def _validated_row_constraints(settings: dict[str, Any]) -> list[dict[str, Any]]:
    rows = settings.get("row_constraints", [])
    for row in rows:
        value = str(row.get("value", "")).strip()
        if not RLS_STATEMENT.fullmatch(value):
            raise FabricApiError(
                "Each OneLake RLS rule must be a complete SELECT * FROM ... WHERE ... statement"
            )
    return rows


def role_from_policy(settings: dict[str, Any]) -> dict[str, Any]:
    group_id = _required_env(str(settings["member_group_env"]))
    tenant_id = _required_env(str(settings["tenant_id_env"]))
    paths = [str(path) for path in settings.get("paths", [])]
    if not paths:
        raise FabricApiError("A OneLake role must grant at least one explicit path")
    action = str(settings.get("action", "Read"))
    decision_rule: dict[str, Any] = {
        "effect": "Permit",
        "permission": [
            {"attributeName": "Path", "attributeValueIncludedIn": paths},
            {"attributeName": "Action", "attributeValueIncludedIn": [action]},
        ],
    }
    constraints: dict[str, Any] = {}
    if settings.get("column_constraints"):
        constraints["columns"] = settings["column_constraints"]
    row_constraints = _validated_row_constraints(settings)
    if row_constraints:
        constraints["rows"] = row_constraints
    if constraints:
        decision_rule["constraints"] = constraints
    return {
        "name": str(settings["name"]),
        "kind": "Policy",
        "decisionRules": [decision_rule],
        "members": {
            "microsoftEntraMembers": [
                {"tenantId": tenant_id, "objectId": group_id, "objectType": "Group"}
            ]
        },
    }


def merged_roles(current_roles: list[dict[str, Any]], desired: dict[str, Any]) -> dict[str, Any]:
    """Preserve every existing writable field while upserting exactly one named role."""
    roles = copy.deepcopy(current_roles)
    matches = [index for index, role in enumerate(roles) if role.get("name") == desired["name"]]
    if len(matches) > 1:
        raise FabricApiError("Multiple OneLake roles have the policy role name")
    if matches:
        roles[matches[0]] = desired
    else:
        roles.append(desired)
    return {
        "value": [{key: role[key] for key in WRITABLE_ROLE_FIELDS if key in role} for role in roles]
    }


def roles_without(current_roles: list[dict[str, Any]], role_name: str) -> dict[str, Any] | None:
    """Return a full-replacement payload without one uniquely named role."""
    matches = [role for role in current_roles if role.get("name") == role_name]
    if len(matches) > 1:
        raise FabricApiError("Multiple OneLake roles have the requested role name")
    if not matches:
        return None
    remaining = [role for role in current_roles if role.get("name") != role_name]
    return {
        "value": [
            {key: role[key] for key in WRITABLE_ROLE_FIELDS if key in role} for role in remaining
        ]
    }


def apply_policy_role(
    client: FabricClient,
    workspace_name: str,
    lakehouse_name: str,
    role_settings: dict[str, Any],
    *,
    apply: bool = False,
) -> dict[str, Any]:
    workspace = client.named(client.workspaces(), workspace_name)
    if not workspace:
        raise FabricApiError(f"Workspace {workspace_name!r} was not found")
    lakehouse = client.named(client.items(str(workspace["id"])), lakehouse_name, "Lakehouse")
    if not lakehouse:
        raise FabricApiError(f"Lakehouse {lakehouse_name!r} was not found")
    path = f"workspaces/{workspace['id']}/items/{lakehouse['id']}/dataAccessRoles"
    response = client.request("GET", path)
    etag = response.headers.get("ETag") or response.headers.get("Etag")
    if not etag:
        raise FabricApiError("OneLake role list returned no ETag; refusing full replacement")
    desired = role_from_policy(role_settings)
    payload = merged_roles(client.json(response).get("value", []), desired)
    headers = {"If-Match": etag}
    client.request("PUT", f"{path}?dryRun=true", json=payload, headers=headers)
    if apply:
        client.request("PUT", path, json=payload, headers=headers)
    return {
        "mode": "apply" if apply else "server-dry-run",
        "workspace": workspace_name,
        "lakehouse": lakehouse_name,
        "role": desired["name"],
        "role_count_preserved_or_merged": len(payload["value"]),
        "note": "Existing roles were preserved; principal and tenant IDs are not emitted.",
    }


def remove_named_role(
    client: FabricClient,
    workspace_name: str,
    lakehouse_name: str,
    role_name: str,
    *,
    apply: bool = False,
) -> dict[str, Any]:
    """Server-dry-run and optionally remove one role while preserving all other roles."""
    workspace = client.named(client.workspaces(), workspace_name)
    if not workspace:
        raise FabricApiError(f"Workspace {workspace_name!r} was not found")
    lakehouse = client.named(client.items(str(workspace["id"])), lakehouse_name, "Lakehouse")
    if not lakehouse:
        raise FabricApiError(f"Lakehouse {lakehouse_name!r} was not found")
    path = f"workspaces/{workspace['id']}/items/{lakehouse['id']}/dataAccessRoles"
    response = client.request("GET", path)
    payload = roles_without(client.json(response).get("value", []), role_name)
    if payload is None:
        return {
            "mode": "no-op",
            "workspace": workspace_name,
            "lakehouse": lakehouse_name,
            "role": role_name,
            "note": "The named role is already absent; principal and tenant IDs are not emitted.",
        }
    etag = response.headers.get("ETag") or response.headers.get("Etag")
    if not etag:
        raise FabricApiError("OneLake role list returned no ETag; refusing full replacement")
    headers = {"If-Match": etag}
    client.request("PUT", f"{path}?dryRun=true", json=payload, headers=headers)
    if apply:
        client.request("PUT", path, json=payload, headers=headers)
    return {
        "mode": "apply" if apply else "server-dry-run",
        "workspace": workspace_name,
        "lakehouse": lakehouse_name,
        "role": role_name,
        "role_count_preserved": len(payload["value"]),
        "note": "All other roles were preserved; principal and tenant IDs are not emitted.",
    }
