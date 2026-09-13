"""Build Fabric Git-format definitions and resolve deployment placeholders."""

from __future__ import annotations

import base64
import copy
import json
import re
import uuid
from typing import Any

PLACEHOLDER = re.compile(r"^\{\{([A-Z_]+)(?::([^{}]+))?\}\}$")


def _b64(value: str | dict[str, Any]) -> str:
    text = value if isinstance(value, str) else json.dumps(value, separators=(",", ":"))
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


def logical_id(item_type: str, display_name: str) -> str:
    seed = f"fabric-onelake-catalog-governance-poc/{item_type}/{display_name}"
    return str(uuid.uuid5(uuid.NAMESPACE_URL, seed))


def item_definition(
    item_type: str, display_name: str, part_path: str, content: str | dict[str, Any]
) -> dict[str, Any]:
    platform = {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": item_type, "displayName": display_name},
        "config": {"version": "2.0", "logicalId": logical_id(item_type, display_name)},
    }
    return {
        "format": "fabricGitSource",
        "parts": [
            {"path": part_path, "payload": _b64(content), "payloadType": "InlineBase64"},
            {"path": ".platform", "payload": _b64(platform), "payloadType": "InlineBase64"},
        ],
    }


def notebook_definition(display_name: str, content: str) -> dict[str, Any]:
    return item_definition("Notebook", display_name, "notebook-content.py", content)


def pipeline_definition(display_name: str, content: dict[str, Any]) -> dict[str, Any]:
    definition = item_definition("DataPipeline", display_name, "pipeline-content.json", content)
    # Unlike notebooks, the Data Pipeline API currently rejects fabricGitSource here.
    definition.pop("format")
    return definition


def bind_placeholders(template: dict[str, Any], values: dict[str, str]) -> dict[str, Any]:
    bound = copy.deepcopy(template)

    def visit(value: Any) -> Any:
        if isinstance(value, dict):
            return {key: visit(child) for key, child in value.items()}
        if isinstance(value, list):
            return [visit(child) for child in value]
        if isinstance(value, str):
            match = PLACEHOLDER.fullmatch(value)
            if not match:
                return value
            kind, name = match.groups()
            key = kind if name is None else f"{kind}:{name}"
            if key not in values:
                raise KeyError(f"Unresolved Fabric definition placeholder: {value}")
            return values[key]
        return value

    return visit(bound)
