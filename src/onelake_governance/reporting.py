"""Render assessment reports without Fabric identifiers or principal details."""

from __future__ import annotations

import json
from pathlib import Path

from .models import AssessmentReport


def render_markdown(report: AssessmentReport) -> str:
    summary = report.summary
    lines = [
        f"# OneLake governance assessment: {report.workspace_name}",
        "",
        f"Generated: `{report.generated_at_utc}`",
        "",
        "> Privacy: IDs, principal names, connection details, and credentials are deliberately omitted.",
        "",
        "## Summary",
        "",
        "| PASS | FAIL | WARN | MANUAL | N/A |",
        "|---:|---:|---:|---:|---:|",
        f"| {summary['PASS']} | {summary['FAIL']} | {summary['WARN']} | {summary['MANUAL']} | {summary['NOT_APPLICABLE']} |",
        "",
        "## Controls",
        "",
        "| Control | Status | Severity | Resource | Evidence | Recommendation |",
        "|---|---|---|---|---|---|",
    ]
    for control in report.controls:
        values = (
            control.control,
            control.status,
            control.severity,
            control.resource,
            control.evidence,
            control.recommendation,
        )
        escaped = [value.replace("|", "\\|").replace("\n", " ") for value in values]
        lines.append("| " + " | ".join(escaped) + " |")
    lines.extend(
        [
            "",
            "## Decision rule",
            "",
            "Treat every `FAIL` as release-blocking. Assign an owner and due date to every `WARN` and `MANUAL` item. A report with zero failures is not proof of regulatory compliance.",
            "",
        ]
    )
    return "\n".join(lines)


def write_report(report: AssessmentReport, output: str | Path) -> tuple[Path, Path]:
    output_path = Path(output)
    stem = output_path.with_suffix("")
    json_path = stem.with_suffix(".json")
    markdown_path = stem.with_suffix(".md")
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report.to_dict(), indent=2) + "\n", encoding="utf-8")
    markdown_path.write_text(render_markdown(report), encoding="utf-8")
    return json_path, markdown_path
