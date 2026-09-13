from onelake_governance.admin import bootstrap_admin_objects


class Client:
    def __init__(self):
        self.writes = []

    def list_all(self, path, key="value"):
        assert key in {"value", "domains"}
        if path.startswith("admin/domains"):
            return []
        if path == "admin/tags":
            return [{"displayName": "existing"}]
        raise AssertionError(path)

    @staticmethod
    def named(objects, name, object_type=None):
        return None

    def request(self, method, path, **kwargs):
        self.writes.append((method, path, kwargs))
        return Response()

    @staticmethod
    def json(_response):
        return {"id": "domain-id", "displayName": "Approved"}


class Response:
    content = b"x"


POLICY = {
    "workspace": {"domain_name": "Approved", "domain_description": "Description"},
    "admin": {"tenant_tags": ["existing", "missing"]},
}


def test_admin_bootstrap_dry_run_has_no_writes():
    client = Client()
    changes = bootstrap_admin_objects(client, POLICY)
    assert client.writes == []
    assert [(change.action, change.name) for change in changes] == [
        ("create-domain", "Approved"),
        ("create-tenant-tag", "missing"),
    ]


def test_admin_bootstrap_apply_creates_only_missing():
    client = Client()
    changes = bootstrap_admin_objects(client, POLICY, apply=True)
    assert len(client.writes) == 2
    assert all(change.status == "applied" for change in changes)
