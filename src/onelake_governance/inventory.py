"""Collect the minimum metadata needed for a governance assessment."""

from __future__ import annotations

from typing import Any

from .client import FabricApiError, FabricClient
from .models import WorkspaceSnapshot

ONELAKE_SECURITY_TYPES = frozenset(
    {
        "Lakehouse",
        "MirroredDatabase",
        "MirroredWarehouse",
        "MirroredAzureDatabricksCatalog",
        "MirroredSnowflake",
    }
)
CONNECTION_RELEVANT_TYPES = frozenset(
    {
        "DataPipeline",
        "Dataflow",
        "DataflowGen2",
        "Lakehouse",
        "MirroredDatabase",
        "MirroredWarehouse",
        "MirroredAzureDatabricksCatalog",
        "MirroredSnowflake",
        "Notebook",
        "Warehouse",
    }
)
SHORTCUT_CONTAINER_TYPES = frozenset({"Lakehouse", "KQLDatabase"})


def _privacy_safe_role_counts(assignments: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = {}
    for assignment in assignments:
        role = str(assignment.get("role", "Unknown"))
        principal_type = str(assignment.get("principal", {}).get("type", "Unknown"))
        counts.setdefault(role, {})[principal_type] = (
            counts.setdefault(role, {}).get(principal_type, 0) + 1
        )
    return counts


def _visible_role_summary(payload: dict[str, Any]) -> dict[str, Any]:
    roles = payload.get("value", [])

    def broad_default(role: dict[str, Any]) -> bool:
        if role.get("name") != "DefaultReader":
            return False
        members = role.get("members", {})
        inherited_read_all = any(
            "ReadAll" in member.get("itemAccess", [])
            for member in members.get("fabricItemMembers", [])
        )
        explicit_members = bool(members.get("microsoftEntraMembers", []))
        wildcard_read = any(
            any(
                scope.get("attributeName") == "Path"
                and "*" in scope.get("attributeValueIncludedIn", [])
                for scope in rule.get("permission", [])
            )
            for rule in role.get("decisionRules", [])
        )
        return inherited_read_all or (explicit_members and wildcard_read)

    return {
        "role_count": len(roles),
        "role_names": sorted(str(role.get("name", "Unnamed")) for role in roles),
        "broad_default_reader": any(broad_default(role) for role in roles),
        "member_count": sum(
            sum(len(values) for values in role.get("members", {}).values()) for role in roles
        ),
    }


def collect_snapshot(client: FabricClient, workspace_name: str) -> WorkspaceSnapshot:
    workspace = client.named(client.workspaces(), workspace_name)
    if not workspace:
        raise FabricApiError(f"Fabric workspace {workspace_name!r} was not found")
    workspace_id = str(workspace["id"])
    items = client.items(workspace_id)
    snapshot = WorkspaceSnapshot(workspace_name, workspace, items)

    roles, reason = client.optional_json(f"workspaces/{workspace_id}/roleAssignments")
    if roles is not None:
        snapshot.role_counts = _privacy_safe_role_counts(roles.get("value", []))
    else:
        snapshot.unavailable["workspace_roles"] = reason or "Unavailable"

    git, reason = client.optional_json(f"workspaces/{workspace_id}/git/connection")
    if git is not None:
        snapshot.git_state = str(git.get("gitConnectionState", "Unknown"))
    else:
        snapshot.unavailable["git"] = reason or "Unavailable"

    for item in items:
        item_id = str(item["id"])
        item_name = str(item.get("displayName", "Unnamed"))
        item_type = str(item.get("type", "Unknown"))
        key = f"{item_type}:{item_name}"
        if item_type in ONELAKE_SECURITY_TYPES:
            roles, reason = client.optional_json(
                f"workspaces/{workspace_id}/items/{item_id}/dataAccessRoles"
            )
            if roles is not None:
                snapshot.data_access[key] = _visible_role_summary(roles)
            else:
                snapshot.unavailable[f"onelake_security:{key}"] = reason or "Unavailable"
        if item_type in CONNECTION_RELEVANT_TYPES:
            connections, reason = client.optional_json(
                f"workspaces/{workspace_id}/items/{item_id}/connections"
            )
            if connections is not None:
                snapshot.connection_counts[key] = len(connections.get("value", []))
            elif reason and "HTTP 404" not in reason:
                snapshot.unavailable[f"connections:{key}"] = reason
        if item_type in SHORTCUT_CONTAINER_TYPES:
            shortcuts, reason = client.optional_json(
                f"workspaces/{workspace_id}/items/{item_id}/shortcuts"
            )
            if shortcuts is not None:
                snapshot.shortcut_counts[key] = len(shortcuts.get("value", []))
            elif reason and "HTTP 404" not in reason:
                snapshot.unavailable[f"shortcuts:{key}"] = reason

    try:
        item_ids = {str(item["id"]) for item in items}
        matched_ids: set[str] = set()
        continuation = ""
        while True:
            payload = {"search": workspace_name, "pageSize": 1000}
            if continuation:
                payload["continuationToken"] = continuation
            body = client.json(client.request("POST", "catalog/search", json=payload))
            matched_ids.update(
                str(entry.get("id"))
                for entry in body.get("value", [])
                if str(entry.get("id")) in item_ids
            )
            continuation = str(body.get("continuationToken", ""))
            if not continuation or matched_ids == item_ids:
                break
        snapshot.catalog_matches = len(matched_ids)
    except FabricApiError as exc:
        snapshot.unavailable["catalog_search"] = str(exc)
    return snapshot
