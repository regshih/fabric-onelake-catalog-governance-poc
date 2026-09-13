import base64
import json
import re

import pytest

from onelake_governance.definitions import bind_placeholders, notebook_definition


def test_notebook_definition_is_deterministic_and_decodable():
    first = notebook_definition("nb_test", "print('synthetic')")
    second = notebook_definition("nb_test", "print('synthetic')")
    assert first == second
    assert first["format"] == "fabricGitSource"
    parts = {part["path"]: part for part in first["parts"]}
    assert (
        base64.b64decode(parts["notebook-content.py"]["payload"]).decode() == "print('synthetic')"
    )
    platform = json.loads(base64.b64decode(parts[".platform"]["payload"]))
    assert platform["metadata"] == {"type": "Notebook", "displayName": "nb_test"}


def test_binding_is_complete_and_does_not_modify_template():
    template = {"workspace": "{{WORKSPACE_ID}}", "items": ["{{ITEM_ID:lakehouse}}"]}
    original = json.dumps(template)
    bound = bind_placeholders(
        template, {"WORKSPACE_ID": "workspace-value", "ITEM_ID:lakehouse": "lakehouse-value"}
    )
    assert bound == {"workspace": "workspace-value", "items": ["lakehouse-value"]}
    assert json.dumps(template) == original


def test_unknown_placeholder_fails_closed():
    with pytest.raises(KeyError, match="Unresolved"):
        bind_placeholders({"value": "{{ITEM_ID:missing}}"}, {})


def test_demo_pipeline_has_no_committed_environment_uuid():
    text = open("demo/pipelines/pl_governance_demo_refresh.json", encoding="utf-8").read()
    uuids = re.findall(
        r"\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b",
        text,
        re.I,
    )
    assert uuids == []
