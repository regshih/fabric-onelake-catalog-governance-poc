"""Evaluate a Fabric workspace against governance policy as code."""

from __future__ import annotations

import re
from typing import Any

from .inventory import ONELAKE_SECURITY_TYPES
from .models import AssessmentReport, ControlResult, WorkspaceSnapshot
from .policy import item_settings

PRIVILEGED_ROLES = frozenset({"Admin", "Member", "Contributor"})
MANAGED_ITEM_TYPES = frozenset({"SQLEndpoint"})


def result(
    control: str,
    status: str,
    severity: str,
    resource: str,
    evidence: str,
    recommendation: str = "",
) -> ControlResult:
    return ControlResult(control, status, severity, resource, evidence, recommendation)  # type: ignore[arg-type]


def assess(snapshot: WorkspaceSnapshot, policy: dict[str, Any]) -> AssessmentReport:
    controls: list[ControlResult] = []
    workspace = snapshot.workspace
    workspace_policy = policy.get("workspace", {})

    domain_required = bool(workspace_policy.get("require_domain", True))
    has_domain = bool(workspace.get("domainId"))
    controls.append(
        result(
            "GOV-001",
            "PASS" if has_domain else ("FAIL" if domain_required else "NOT_APPLICABLE"),
            "high",
            "workspace",
            "Workspace is assigned to a domain."
            if has_domain
            else "No domain assignment is visible.",
            "Assign the workspace to an approved business domain; do not create domains per project.",
        )
    )

    description = str(workspace.get("description", "")).strip()
    min_length = int(workspace_policy.get("description_min_length", 30))
    controls.append(
        result(
            "CAT-001",
            "PASS" if len(description) >= min_length else "FAIL",
            "medium",
            "workspace",
            f"Workspace description length is {len(description)} characters.",
            "Describe the business purpose, owner/team, environment, and data scope.",
        )
    )

    connected = snapshot.git_state == "ConnectedAndInitialized"
    controls.append(
        result(
            "LCM-001",
            "PASS" if connected else "WARN",
            "medium",
            "workspace",
            f"Fabric Git state is {snapshot.git_state}.",
            "Connect supported item definitions to a protected branch and review sync diffs.",
        )
    )

    if "workspace_roles" in snapshot.unavailable:
        controls.append(
            result(
                "SEC-001",
                "MANUAL",
                "high",
                "workspace",
                "Workspace role assignments could not be inventoried with the current permissions.",
                "Review workspace roles manually and prefer Entra security groups over individuals.",
            )
        )
    else:
        privileged_users = sum(
            counts.get("User", 0)
            for role, counts in snapshot.role_counts.items()
            if role in PRIVILEGED_ROLES
        )
        controls.append(
            result(
                "SEC-001",
                "PASS" if privileged_users == 0 else "WARN",
                "high",
                "workspace",
                f"Privileged workspace roles contain {privileged_users} direct user assignment(s).",
                "Use Entra security groups for durable, reviewable access; keep emergency access separate.",
            )
        )

    managed_types = MANAGED_ITEM_TYPES | frozenset(policy.get("managed_item_types", []))
    naming_patterns = policy.get("naming_patterns", {})
    sensitivity_types = frozenset(policy.get("sensitivity_label_item_types", []))
    item_identities = {
        (str(item.get("displayName", "")), str(item.get("type", "Unknown")))
        for item in snapshot.items
    }

    for required_name, required_settings in policy.get("items", {}).items():
        required_type = str(required_settings.get("type", ""))
        found = any(
            name == required_name and (not required_type or item_type == required_type)
            for name, item_type in item_identities
        )
        if required_settings.get("required", True) and not found:
            controls.append(
                result(
                    "EST-001",
                    "FAIL",
                    "medium",
                    required_name,
                    "Required policy item was not found.",
                    "Create the item or record an approved exception in the policy.",
                )
            )

    for item in snapshot.items:
        name = str(item.get("displayName", "Unnamed"))
        item_type = str(item.get("type", "Unknown"))
        resource = f"{item_type}/{name}"
        settings = item_settings(policy, name, item_type)

        if item_type not in managed_types:
            item_description = str(item.get("description", "")).strip()
            required = bool(settings.get("description_required", True))
            controls.append(
                result(
                    "CAT-002",
                    "PASS" if item_description else ("FAIL" if required else "NOT_APPLICABLE"),
                    "medium",
                    resource,
                    "Business description is present."
                    if item_description
                    else "Description is empty.",
                    "Add a concise purpose, source, grain, refresh expectation, and intended audience.",
                )
            )

            pattern = settings.get("name_pattern") or naming_patterns.get(item_type)
            if pattern:
                valid_name = bool(re.fullmatch(str(pattern), name))
                controls.append(
                    result(
                        "CAT-003",
                        "PASS" if valid_name else "WARN",
                        "low",
                        resource,
                        "Name matches policy."
                        if valid_name
                        else "Name does not match the configured pattern.",
                        "Rename only after impact analysis; document an exception for stable public contracts.",
                    )
                )

            required_tags = set(settings.get("tags", []))
            applied_tags = {
                str(tag.get("displayName", ""))
                for tag in item.get("tags", [])
                if isinstance(tag, dict)
            }
            if required_tags:
                missing = sorted(required_tags - applied_tags)
                controls.append(
                    result(
                        "CAT-004",
                        "PASS" if not missing else "WARN",
                        "medium",
                        resource,
                        "All policy tags are applied."
                        if not missing
                        else f"Missing {len(missing)} policy tag(s).",
                        "Have a Fabric/domain admin define the controlled tag vocabulary, then apply it.",
                    )
                )

        if item_type in sensitivity_types:
            labeled = bool(item.get("sensitivityLabel", {}).get("id"))
            controls.append(
                result(
                    "PRO-001",
                    "PASS" if labeled else "WARN",
                    "high",
                    resource,
                    "A sensitivity label is present."
                    if labeled
                    else "No sensitivity label is visible.",
                    "Apply the organizationally approved sensitivity label and validate "
                    "downstream/export behavior.",
                )
            )

        key = f"{item_type}:{name}"
        if item_type in ONELAKE_SECURITY_TYPES:
            access = snapshot.data_access.get(key)
            if access is None:
                controls.append(
                    result(
                        "SEC-002",
                        "MANUAL",
                        "high",
                        resource,
                        "OneLake security roles were unavailable or unsupported for this item.",
                        "Review data-plane access and the current item-type support matrix manually.",
                    )
                )
            elif access["broad_default_reader"]:
                controls.append(
                    result(
                        "SEC-002",
                        "WARN",
                        "high",
                        resource,
                        "DefaultReader contains a broad ReadAll grant.",
                        "Review all effective grants before narrowing DefaultReader; test with a Viewer identity.",
                    )
                )
            else:
                controls.append(
                    result(
                        "SEC-002",
                        "PASS",
                        "high",
                        resource,
                        f"{access['role_count']} OneLake role(s) found without broad DefaultReader ReadAll.",
                    )
                )

    if snapshot.catalog_matches is None:
        controls.append(
            result(
                "CAT-005",
                "MANUAL",
                "medium",
                "workspace",
                "Catalog Search API could not be evaluated.",
                "Verify discoverability in OneLake catalog with a least-privileged consumer identity.",
            )
        )
    else:
        controls.append(
            result(
                "CAT-005",
                "PASS" if snapshot.catalog_matches else "WARN",
                "medium",
                "workspace",
                f"Catalog search returned {snapshot.catalog_matches} item(s) from this workspace.",
                "Allow metadata propagation time, then verify descriptions, domain, tags, and permissions.",
            )
        )

    external_count = sum(snapshot.connection_counts.values()) + sum(
        snapshot.shortcut_counts.values()
    )
    mirror_count = sum(1 for item in snapshot.items if "Mirrored" in str(item.get("type", "")))
    controls.extend(
        [
            result(
                "SRC-001",
                "MANUAL",
                "high",
                "workspace",
                f"Inventory found {external_count} connection/shortcut reference(s) and {mirror_count} mirrored item(s).",
                "Review source-owner permissions, credential ownership, exfiltration risk, and target-side controls.",
            ),
            result(
                "TRU-001",
                "MANUAL",
                "medium",
                "workspace",
                "Certification and master-data status require an authorized governance review.",
                "Promote only useful content; certify/master data only after documented quality approval.",
            ),
            result(
                "LIN-001",
                "MANUAL",
                "medium",
                "workspace",
                "Automated counts do not prove end-to-end lineage completeness.",
                "Inspect lineage and impact analysis from each governed data product to its consumers.",
            ),
            result(
                "OPS-001",
                "MANUAL",
                "high",
                "workspace",
                "Tenant audit, OneLake diagnostics, DLP, and alerting are outside workspace REST scope.",
                "Enable and test audit/diagnostic collection, DLP, retention, and operational ownership.",
            ),
        ]
    )
    return AssessmentReport(snapshot.workspace_name, controls)
