from onelake_governance.remediation import plan_remediation


class Client:
    def __init__(self):
        self.writes = []

    def workspaces(self):
        return [{"id": "workspace-id", "displayName": "Demo", "description": "old"}]

    def items(self, _workspace_id):
        return [
            {
                "id": "item-id",
                "displayName": "governed_curated_lh",
                "type": "Lakehouse",
                "description": "old",
                "tags": [],
            }
        ]

    def list_all(self, path):
        if path == "domains":
            return [{"id": "domain-id", "displayName": "Approved"}]
        if path == "tags":
            return [{"id": "tag-id", "displayName": "available"}]
        raise AssertionError(path)

    @staticmethod
    def named(objects, name, object_type=None):
        return next(
            (
                obj
                for obj in objects
                if obj.get("displayName", "").casefold() == name.casefold()
                and (object_type is None or obj.get("type") == object_type)
            ),
            None,
        )

    def request(self, method, path, **kwargs):
        self.writes.append((method, path, kwargs))
        return object()


POLICY = {
    "workspace": {"description": "approved workspace description"},
    "item_defaults": {},
    "items": {
        "governed_curated_lh": {
            "description": "approved item description",
            "tags": ["available", "admin-missing"],
        }
    },
}


def test_remediation_is_dry_run_by_default_and_reports_admin_block():
    client = Client()
    changes = plan_remediation(client, "Demo", POLICY, domain_name="Approved")
    assert client.writes == []
    assert any(
        change.action == "assign-domain" and change.status == "planned" for change in changes
    )
    assert any(change.action == "apply-tags" and change.status == "blocked" for change in changes)


def test_apply_writes_only_descriptions_domain_and_existing_tags():
    client = Client()
    plan_remediation(client, "Demo", POLICY, domain_name="Approved", apply=True)
    paths = [path for _method, path, _kwargs in client.writes]
    assert "workspaces/workspace-id" in paths
    assert "workspaces/workspace-id/assignToDomain" in paths
    assert "workspaces/workspace-id/items/item-id" in paths
    assert "workspaces/workspace-id/items/item-id/applyTags" in paths
    assert all("delete" not in method.casefold() for method, _path, _kwargs in client.writes)


def test_remediation_reassigns_workspace_from_wrong_domain():
    client = Client()
    original = client.workspaces
    client.workspaces = lambda: [
        {
            **original()[0],
            "domainId": "different-domain-id",
        }
    ]

    changes = plan_remediation(client, "Demo", POLICY, domain_name="Approved")

    assert any(
        change.action == "assign-domain" and change.status == "planned" for change in changes
    )


def test_remediation_skips_workspace_already_in_approved_domain():
    client = Client()
    original = client.workspaces
    client.workspaces = lambda: [
        {
            **original()[0],
            "domainId": "domain-id",
        }
    ]

    changes = plan_remediation(client, "Demo", POLICY, domain_name="Approved")

    assert not any(change.action == "assign-domain" for change in changes)
