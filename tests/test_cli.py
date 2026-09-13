import json
import sys
from pathlib import Path

import pytest

from onelake_governance import cli
from onelake_governance.models import AssessmentReport, ControlResult


@pytest.fixture
def cli_client(monkeypatch):
    value = object()
    monkeypatch.setattr(cli, "FabricClient", lambda: value)
    return value


def test_cli_assess(monkeypatch, capsys, tmp_path, cli_client):
    report = AssessmentReport("Demo", [ControlResult("X", "PASS", "low", "workspace", "ok")])
    monkeypatch.setattr(cli, "collect_snapshot", lambda client, name: (client, name))
    monkeypatch.setattr(cli, "assess", lambda snapshot, policy: report)
    monkeypatch.setattr(
        cli, "write_report", lambda value, output: (Path(f"{output}.json"), Path(f"{output}.md"))
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["onelake-governance", "assess", "--workspace", "Demo", "--output", str(tmp_path / "x")],
    )
    cli.main()
    output = json.loads(capsys.readouterr().out)
    assert output["summary"]["PASS"] == 1


def test_cli_remediate(monkeypatch, capsys, cli_client):
    monkeypatch.setattr(cli, "plan_remediation", lambda *args, **kwargs: [])
    monkeypatch.setattr(sys, "argv", ["tool", "remediate", "--workspace", "Demo", "--apply"])
    cli.main()
    assert json.loads(capsys.readouterr().out)["mode"] == "apply"


def test_cli_bootstrap(monkeypatch, capsys, cli_client):
    monkeypatch.setattr(cli, "bootstrap_demo", lambda *args, **kwargs: {"mode": "dry-run"})
    monkeypatch.setattr(
        sys,
        "argv",
        ["tool", "bootstrap-demo", "--workspace", "Demo", "--capacity", "Capacity"],
    )
    cli.main()
    assert json.loads(capsys.readouterr().out) == {"mode": "dry-run"}


def test_cli_admin(monkeypatch, capsys, cli_client):
    monkeypatch.setattr(cli, "bootstrap_admin_objects", lambda *args, **kwargs: [])
    monkeypatch.setattr(sys, "argv", ["tool", "admin-bootstrap"])
    cli.main()
    assert json.loads(capsys.readouterr().out)["mode"] == "dry-run"


def test_cli_onelake_role(monkeypatch, capsys, cli_client):
    monkeypatch.setattr(
        cli,
        "apply_policy_role",
        lambda *args, **kwargs: {"mode": "server-dry-run", "role": "PublicMetricsReader"},
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "tool",
            "apply-onelake-role",
            "--workspace",
            "Demo",
            "--lakehouse",
            "governed_curated_lh",
            "--role",
            "PublicMetricsReader",
        ],
    )
    cli.main()
    assert json.loads(capsys.readouterr().out)["role"] == "PublicMetricsReader"


def test_cli_requires_workspace_and_capacity(monkeypatch, cli_client):
    monkeypatch.delenv("FABRIC_WORKSPACE_NAME", raising=False)
    monkeypatch.setattr(sys, "argv", ["tool", "assess"])
    with pytest.raises(SystemExit, match="workspace"):
        cli.main()
