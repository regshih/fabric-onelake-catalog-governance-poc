"""Privacy-safe inventory and assessment models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal

Status = Literal["PASS", "FAIL", "WARN", "MANUAL", "NOT_APPLICABLE"]


@dataclass(frozen=True)
class ControlResult:
    control: str
    status: Status
    severity: str
    resource: str
    evidence: str
    recommendation: str = ""


@dataclass
class WorkspaceSnapshot:
    workspace_name: str
    workspace: dict[str, Any]
    items: list[dict[str, Any]]
    role_counts: dict[str, dict[str, int]] = field(default_factory=dict)
    git_state: str = "Unavailable"
    data_access: dict[str, dict[str, Any]] = field(default_factory=dict)
    connection_counts: dict[str, int] = field(default_factory=dict)
    shortcut_counts: dict[str, int] = field(default_factory=dict)
    catalog_matches: int | None = None
    unavailable: dict[str, str] = field(default_factory=dict)


@dataclass
class AssessmentReport:
    workspace_name: str
    controls: list[ControlResult]
    generated_at_utc: str = field(
        default_factory=lambda: datetime.now(UTC).replace(microsecond=0).isoformat()
    )
    schema_version: int = 1

    @property
    def summary(self) -> dict[str, int]:
        result = {key: 0 for key in ("PASS", "FAIL", "WARN", "MANUAL", "NOT_APPLICABLE")}
        for control in self.controls:
            result[control.status] += 1
        return result

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "generated_at_utc": self.generated_at_utc,
            "workspace": self.workspace_name,
            "summary": self.summary,
            "controls": [asdict(control) for control in self.controls],
            "privacy": "No tenant, subscription, workspace, item, principal, or connection IDs included.",
        }
