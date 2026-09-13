"""Conservative governance remediation; dry-run unless explicitly applied."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .client import FabricApiError, FabricClient
from .policy import item_settings


@dataclass(frozen=True)
class Change:
    action: str
    resource: str
    status: str
    detail: str


def _domains(client: FabricClient) -> list[dict[str, Any]]:
    # Core domains lists only domains visible to the caller and does not need tenant admin rights.
    return client.list_all("domains")


def plan_remediation(
    client: FabricClient,
    workspace_name: str,
    policy: dict[str, Any],
    *,
    domain_name: str = "",
    apply: bool = False,
) -> list[Change]:
    workspace = client.named(client.workspaces(), workspace_name)
    if not workspace:
        raise FabricApiError(f"Fabric workspace {workspace_name!r} was not found")
    workspace_id = str(workspace["id"])
    changes: list[Change] = []
    desired_workspace_description = str(policy.get("workspace", {}).get("description", "")).strip()
    if (
        desired_workspace_description
        and workspace.get("description") != desired_workspace_description
    ):
        if apply:
            client.request(
                "PATCH",
                f"workspaces/{workspace_id}",
                json={"description": desired_workspace_description},
            )
        changes.append(
            Change(
                "update-description",
                "workspace",
                "applied" if apply else "planned",
                "Set the policy-approved workspace description.",
            )
        )

    desired_domain = (
        domain_name.strip() or str(policy.get("workspace", {}).get("domain_name", "")).strip()
    )
    if desired_domain and not workspace.get("domainId"):
        domain = client.named(_domains(client), desired_domain)
        if not domain:
            changes.append(
                Change(
                    "assign-domain",
                    "workspace",
                    "blocked",
                    "The approved domain is not visible; ask a Fabric/domain admin to create or grant it.",
                )
            )
        else:
            if apply:
                client.request(
                    "POST",
                    f"workspaces/{workspace_id}/assignToDomain",
                    json={"domainId": domain["id"]},
                )
            changes.append(
                Change(
                    "assign-domain",
                    "workspace",
                    "applied" if apply else "planned",
                    f"Assign to the approved {desired_domain!r} domain.",
                )
            )

    tags = client.list_all("tags")
    tags_by_name = {str(tag.get("displayName", "")).casefold(): tag for tag in tags}
    managed_types = set(policy.get("managed_item_types", []))
    for item in client.items(workspace_id):
        name = str(item.get("displayName", "Unnamed"))
        item_type = str(item.get("type", "Unknown"))
        if item_type in managed_types:
            continue
        resource = f"{item_type}/{name}"
        settings = item_settings(policy, name, item_type)
        desired_description = str(settings.get("description", "")).strip()
        if desired_description and item.get("description") != desired_description:
            if apply:
                client.request(
                    "PATCH",
                    f"workspaces/{workspace_id}/items/{item['id']}",
                    json={"description": desired_description},
                )
            changes.append(
                Change(
                    "update-description",
                    resource,
                    "applied" if apply else "planned",
                    "Set the policy-approved item description.",
                )
            )

        applied_names = {
            str(tag.get("displayName", "")).casefold()
            for tag in item.get("tags", [])
            if isinstance(tag, dict)
        }
        desired_names = [str(value) for value in settings.get("tags", [])]
        missing_names = [name for name in desired_names if name.casefold() not in applied_names]
        missing_definitions = [
            name for name in missing_names if name.casefold() not in tags_by_name
        ]
        available_ids = [
            tags_by_name[name.casefold()]["id"]
            for name in missing_names
            if name.casefold() in tags_by_name
        ]
        if missing_definitions:
            changes.append(
                Change(
                    "apply-tags",
                    resource,
                    "blocked",
                    f"{len(missing_definitions)} tag definition(s) require a Fabric/domain admin.",
                )
            )
        if available_ids:
            if apply:
                client.request(
                    "POST",
                    f"workspaces/{workspace_id}/items/{item['id']}/applyTags",
                    json={"tags": available_ids},
                )
            changes.append(
                Change(
                    "apply-tags",
                    resource,
                    "applied" if apply else "planned",
                    f"Apply {len(available_ids)} existing policy tag(s).",
                )
            )
    return changes


def changes_to_dict(changes: list[Change], *, applied: bool) -> dict[str, Any]:
    return {
        "mode": "apply" if applied else "dry-run",
        "changes": [asdict(change) for change in changes],
        "note": "No delete, rename, role-membership, or credential operation is automated.",
    }
