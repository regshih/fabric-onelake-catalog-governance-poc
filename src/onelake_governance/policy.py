"""Load and validate the repository's human-readable governance policy."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


class PolicyError(ValueError):
    """The governance policy is missing or unsafe."""


def load_policy(path: str | Path) -> dict[str, Any]:
    policy_path = Path(path)
    body = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
    if not isinstance(body, dict):
        raise PolicyError("Policy root must be a mapping")
    if body.get("schema_version") != 1:
        raise PolicyError("Only governance policy schema_version 1 is supported")
    workspace = body.get("workspace")
    if not isinstance(workspace, dict):
        raise PolicyError("Policy must include a workspace mapping")
    items = body.get("items", {})
    if not isinstance(items, dict):
        raise PolicyError("Policy items must be a mapping keyed by item display name")
    for name, settings in items.items():
        if not isinstance(name, str) or not isinstance(settings, dict):
            raise PolicyError("Every policy item must have a string name and mapping value")
        description = settings.get("description", "")
        if description and len(description) > 256:
            raise PolicyError(f"Description for {name!r} exceeds Fabric's 256-character limit")
        tags = settings.get("tags", [])
        if (
            not isinstance(tags, list)
            or len(tags) > 10
            or not all(isinstance(tag, str) for tag in tags)
        ):
            raise PolicyError(f"Tags for {name!r} must be a list of at most 10 names")
    return body


def item_settings(
    policy: dict[str, Any], item_name: str, item_type: str | None = None
) -> dict[str, Any]:
    defaults = dict(policy.get("item_defaults", {}))
    specific = policy.get("items", {}).get(item_name, {})
    if not item_type or not specific.get("type") or specific.get("type") == item_type:
        defaults.update(specific)
    return defaults
