"""Optional Fabric-admin bootstrap for domain and controlled tag definitions."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .client import FabricClient


@dataclass(frozen=True)
class AdminChange:
    action: str
    name: str
    status: str


def bootstrap_admin_objects(
    client: FabricClient, policy: dict[str, Any], *, apply: bool = False
) -> list[AdminChange]:
    """Create only missing tenant tags and an optional domain; never update/delete existing objects."""
    changes: list[AdminChange] = []
    admin_domains = client.list_all("admin/domains?preview=false", key="domains")
    domain_name = str(policy.get("workspace", {}).get("domain_name", "")).strip()
    domain = client.named(admin_domains, domain_name) if domain_name else None
    if domain_name and not domain:
        if apply:
            response = client.request(
                "POST",
                "admin/domains?preview=false",
                json={
                    "displayName": domain_name,
                    "description": str(policy.get("workspace", {}).get("domain_description", ""))[
                        :256
                    ],
                },
            )
            domain = client.json(response)
        changes.append(AdminChange("create-domain", domain_name, "applied" if apply else "planned"))

    existing_tags = client.list_all("admin/tags")
    existing_names = {str(tag.get("displayName", "")).casefold() for tag in existing_tags}
    requested = [
        str(tag)
        for tag in policy.get("admin", {}).get("tenant_tags", [])
        if str(tag).casefold() not in existing_names
    ]
    if requested:
        if apply:
            client.request(
                "POST",
                "admin/tags/bulkCreateTags",
                json={
                    "scope": {"type": "Tenant"},
                    "createTagsRequest": [{"displayName": name} for name in requested],
                },
            )
        changes.extend(
            AdminChange("create-tenant-tag", name, "applied" if apply else "planned")
            for name in requested
        )
    return changes


def admin_changes_to_dict(changes: list[AdminChange], *, applied: bool) -> dict[str, Any]:
    return {
        "mode": "apply" if applied else "dry-run",
        "changes": [asdict(change) for change in changes],
        "warning": "Admin APIs require Fabric administrator rights and Tenant.ReadWrite.All.",
    }
