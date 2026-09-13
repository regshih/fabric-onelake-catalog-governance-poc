from pathlib import Path

import pytest

from onelake_governance.policy import PolicyError, item_settings, load_policy


def test_repository_policy_loads_and_merges_defaults():
    policy = load_policy("policy/governance-policy.yaml")
    settings = item_settings(policy, "governed_curated_lh")
    assert settings["description_required"] is True
    assert settings["required"] is True
    assert len(settings["tags"]) <= 10
    sql_endpoint = item_settings(policy, "governed_curated_lh", "SQLEndpoint")
    assert "tags" not in sql_endpoint


@pytest.mark.parametrize(
    "text, message",
    [
        ("[]", "root"),
        ("schema_version: 2\nworkspace: {}", "schema_version"),
        ("schema_version: 1", "workspace"),
        ("schema_version: 1\nworkspace: {}\nitems: []", "items"),
    ],
)
def test_invalid_policy_fails_closed(tmp_path: Path, text: str, message: str):
    path = tmp_path / "policy.yaml"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(PolicyError, match=message):
        load_policy(path)


def test_description_and_tag_limits_are_validated(tmp_path: Path):
    path = tmp_path / "policy.yaml"
    path.write_text(
        "schema_version: 1\nworkspace: {}\nitems:\n  x:\n    description: '" + ("a" * 257) + "'\n",
        encoding="utf-8",
    )
    with pytest.raises(PolicyError, match="256"):
        load_policy(path)
