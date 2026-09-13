"""Idempotently create the small, synthetic Fabric demonstration estate."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .client import FabricApiError, FabricClient
from .definitions import bind_placeholders, notebook_definition, pipeline_definition

DEMO_ITEMS = {
    "governed_curated_lh": (
        "Lakehouse",
        "Governed synthetic data product with public metrics and sensitive-like customer examples.",
    ),
    "governed_serving_wh": (
        "Warehouse",
        "Governed SQL serving surface for approved synthetic analytical products and consumers.",
    ),
    "nb_seed_governance_demo": (
        "Notebook",
        "Creates synthetic public and restricted-like Delta tables for OneLake security demonstrations.",
    ),
    "pl_governance_demo_refresh": (
        "DataPipeline",
        "Orchestrates the synthetic governance demo refresh and establishes catalog lineage.",
    ),
}


def _ensure_workspace(
    client: FabricClient, name: str, capacity_name: str, description: str, *, apply: bool
) -> tuple[dict[str, Any] | None, str]:
    existing = client.named(client.workspaces(), name)
    if existing:
        return existing, "existing"
    capacity = client.named(client.capacities(), capacity_name)
    if not capacity:
        raise FabricApiError(f"Fabric capacity {capacity_name!r} was not found")
    if str(capacity.get("state", "")).casefold() != "active":
        raise FabricApiError(f"Fabric capacity {capacity_name!r} is not active")
    if not apply:
        return None, "planned"
    response = client.request(
        "POST",
        "workspaces",
        json={"displayName": name, "description": description, "capacityId": capacity["id"]},
    )
    result = client.wait_for_operation(response)
    workspace = result if result.get("id") else client.named(client.workspaces(), name)
    if not workspace:
        raise FabricApiError("Workspace provisioning completed without a discoverable workspace")
    return workspace, "created"


def _ensure_item(
    client: FabricClient,
    workspace_id: str,
    name: str,
    item_type: str,
    description: str,
    *,
    definition: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], str]:
    existing = client.named(client.items(workspace_id), name, item_type)
    if existing:
        if existing.get("description") != description:
            client.request(
                "PATCH",
                f"workspaces/{workspace_id}/items/{existing['id']}",
                json={"description": description},
            )
        if definition:
            definition_path = f"workspaces/{workspace_id}/items/{existing['id']}/updateDefinition"
            if item_type == "DataPipeline":
                definition_path = (
                    f"workspaces/{workspace_id}/dataPipelines/{existing['id']}/updateDefinition"
                )
            response = client.request(
                "POST",
                definition_path,
                json={"definition": definition},
            )
            client.wait_for_operation(response)
        return existing, "updated"
    payload: dict[str, Any] = {
        "displayName": name,
        "description": description,
        "type": item_type,
    }
    if definition:
        payload["definition"] = definition
    path = f"workspaces/{workspace_id}/items"
    if item_type == "DataPipeline":
        # The workload endpoint validates pipeline definitions more consistently.
        path = f"workspaces/{workspace_id}/dataPipelines"
        payload.pop("type")
    response = client.request("POST", path, json=payload)
    result = client.wait_for_operation(response)
    item = result if result.get("id") else client.named(client.items(workspace_id), name, item_type)
    if not item:
        raise FabricApiError(f"{item_type} provisioning completed without a discoverable item")
    return item, "created"


def bootstrap_demo(
    client: FabricClient,
    *,
    workspace_name: str,
    capacity_name: str,
    root: Path,
    domain_name: str = "",
    apply: bool = False,
    run_seed: bool = False,
) -> dict[str, Any]:
    workspace_description = (
        "Public-safe OneLake catalog governance reference estate using only synthetic data."
    )
    workspace, workspace_status = _ensure_workspace(
        client, workspace_name, capacity_name, workspace_description, apply=apply
    )
    result: dict[str, Any] = {
        "mode": "apply" if apply else "dry-run",
        "workspace": workspace_name,
        "workspace_status": workspace_status,
        "items": [],
    }
    if not apply:
        result["items"] = [
            {"name": name, "type": item_type, "status": "planned"}
            for name, (item_type, _description) in DEMO_ITEMS.items()
        ]
        return result
    assert workspace is not None
    workspace_id = str(workspace["id"])

    lakehouse, status = _ensure_item(
        client, workspace_id, "governed_curated_lh", *DEMO_ITEMS["governed_curated_lh"]
    )
    result["items"].append({"name": "governed_curated_lh", "type": "Lakehouse", "status": status})
    warehouse, status = _ensure_item(
        client, workspace_id, "governed_serving_wh", *DEMO_ITEMS["governed_serving_wh"]
    )
    result["items"].append({"name": "governed_serving_wh", "type": "Warehouse", "status": status})

    notebook_name = "nb_seed_governance_demo"
    notebook_source = (root / "demo" / "notebooks" / f"{notebook_name}.py").read_text(
        encoding="utf-8"
    )
    notebook, status = _ensure_item(
        client,
        workspace_id,
        notebook_name,
        *DEMO_ITEMS[notebook_name],
        definition=notebook_definition(notebook_name, notebook_source),
    )
    result["items"].append({"name": notebook_name, "type": "Notebook", "status": status})

    pipeline_name = "pl_governance_demo_refresh"
    template = json.loads(
        (root / "demo" / "pipelines" / f"{pipeline_name}.json").read_text(encoding="utf-8")
    )
    bound = bind_placeholders(
        template,
        {
            "WORKSPACE_ID": workspace_id,
            "ITEM_ID:lakehouse": str(lakehouse["id"]),
            "ITEM_ID:notebook": str(notebook["id"]),
        },
    )
    _pipeline, status = _ensure_item(
        client,
        workspace_id,
        pipeline_name,
        *DEMO_ITEMS[pipeline_name],
        definition=pipeline_definition(pipeline_name, bound),
    )
    result["items"].append({"name": pipeline_name, "type": "DataPipeline", "status": status})

    if domain_name and not workspace.get("domainId"):
        domain = client.named(client.list_all("domains"), domain_name)
        if domain:
            client.request(
                "POST",
                f"workspaces/{workspace_id}/assignToDomain",
                json={"domainId": domain["id"]},
            )
            result["domain_status"] = "assigned"
        else:
            result["domain_status"] = "blocked: approved domain not visible"

    if run_seed:
        response = client.request(
            "POST",
            f"workspaces/{workspace_id}/notebooks/{notebook['id']}/jobs/execute/instances?beta=false",
            json={
                "parameters": [
                    {"name": "workspace_id", "value": workspace_id, "type": "Text"},
                    {
                        "name": "lakehouse_id",
                        "value": str(lakehouse["id"]),
                        "type": "Text",
                    },
                ],
                "executionData": {"compute": "Spark"},
            },
        )
        client.wait_for_operation(response, timeout=3600)
        result["seed_status"] = "completed"
    result["privacy"] = "Environment IDs were used in memory and are not emitted."
    _ = warehouse
    return result
