import json

from onelake_governance.models import AssessmentReport, ControlResult
from onelake_governance.reporting import write_report


def test_report_writes_both_formats_and_escapes_tables(tmp_path):
    report = AssessmentReport(
        "Demo",
        [ControlResult("X", "WARN", "low", "item", "a|b", "review")],
        generated_at_utc="2026-01-01T00:00:00+00:00",
    )
    json_path, markdown_path = write_report(report, tmp_path / "assessment.out")
    body = json.loads(json_path.read_text(encoding="utf-8"))
    assert body["summary"]["WARN"] == 1
    assert "a\\|b" in markdown_path.read_text(encoding="utf-8")
    assert body["privacy"].startswith("No tenant")
