from onelake_governance.assessment import assess
from onelake_governance.models import WorkspaceSnapshot
from onelake_governance.policy import load_policy
from onelake_governance.reporting import render_markdown


def _snapshot() -> WorkspaceSnapshot:
    items = [
        {
            "id": "private-item-id",
            "displayName": "governed_curated_lh",
            "description": "Governed synthetic data product.",
            "type": "Lakehouse",
            "tags": [{"id": "private-tag-id", "displayName": "classification-confidential"}],
            "sensitivityLabel": {"id": "private-label-id"},
        },
        {
            "id": "private-item-id-2",
            "displayName": "unmanaged notebook",
            "description": "",
            "type": "Notebook",
        },
    ]
    return WorkspaceSnapshot(
        workspace_name="demo",
        workspace={
            "id": "private-workspace-id",
            "displayName": "demo",
            "description": "A sufficiently descriptive synthetic workspace.",
            "domainId": "private-domain-id",
        },
        items=items,
        role_counts={"Admin": {"Group": 1}, "Viewer": {"User": 2}},
        git_state="ConnectedAndInitialized",
        data_access={
            "Lakehouse:governed_curated_lh": {
                "role_count": 1,
                "role_names": ["Readers"],
                "broad_default_reader": False,
                "member_count": 1,
            }
        },
        catalog_matches=2,
    )


def test_assessment_covers_expected_gaps_and_does_not_emit_ids():
    report = assess(_snapshot(), load_policy("policy/governance-policy.yaml"))
    statuses = {(control.control, control.resource): control.status for control in report.controls}
    assert statuses[("GOV-001", "workspace")] == "PASS"
    assert statuses[("SEC-001", "workspace")] == "PASS"
    assert statuses[("CAT-002", "Notebook/unmanaged notebook")] == "FAIL"
    assert statuses[("SEC-002", "Lakehouse/governed_curated_lh")] == "PASS"
    rendered = render_markdown(report)
    assert "private-workspace-id" not in rendered
    assert "private-item-id" not in rendered
    assert "private-tag-id" not in rendered
    assert "private-label-id" not in rendered


def test_missing_capabilities_become_manual_controls():
    snapshot = _snapshot()
    snapshot.workspace.pop("domainId")
    snapshot.role_counts = {}
    snapshot.unavailable = {
        "workspace_roles": "HTTP 403",
        "catalog_search": "HTTP 403",
        "onelake_security:Lakehouse:governed_curated_lh": "HTTP 400",
    }
    snapshot.data_access = {}
    snapshot.catalog_matches = None
    report = assess(snapshot, load_policy("policy/governance-policy.yaml"))
    assert any(c.control == "GOV-001" and c.status == "FAIL" for c in report.controls)
    assert any(c.control == "SEC-001" and c.status == "MANUAL" for c in report.controls)
    assert any(c.control == "SEC-002" and c.status == "MANUAL" for c in report.controls)
    assert any(c.control == "CAT-005" and c.status == "MANUAL" for c in report.controls)


def test_broad_default_reader_is_warned():
    snapshot = _snapshot()
    snapshot.data_access["Lakehouse:governed_curated_lh"]["broad_default_reader"] = True
    report = assess(snapshot, load_policy("policy/governance-policy.yaml"))
    assert any(c.control == "SEC-002" and c.status == "WARN" for c in report.controls)
