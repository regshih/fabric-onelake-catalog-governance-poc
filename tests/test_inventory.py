from onelake_governance.inventory import collect_snapshot


class Client:
    def workspaces(self):
        return [{"id": "workspace-id", "displayName": "Demo", "description": "description"}]

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

    def items(self, _workspace_id):
        return [
            {"id": "lakehouse-id", "displayName": "lh_demo", "type": "Lakehouse"},
            {"id": "notebook-id", "displayName": "nb_demo", "type": "Notebook"},
        ]

    def optional_json(self, path):
        if path.endswith("roleAssignments"):
            return {
                "value": [
                    {"role": "Admin", "principal": {"type": "Group", "displayName": "private"}}
                ]
            }, None
        if path.endswith("git/connection"):
            return {
                "gitConnectionState": "ConnectedAndInitialized",
                "gitProviderDetails": "private",
            }, None
        if path.endswith("dataAccessRoles"):
            return {
                "value": [
                    {
                        "name": "DefaultReader",
                        "members": {
                            "fabricItemMembers": [
                                {"sourcePath": "private", "itemAccess": ["ReadAll"]}
                            ]
                        },
                        "decisionRules": [
                            {
                                "permission": [
                                    {
                                        "attributeName": "Action",
                                        "attributeValueIncludedIn": ["Read"],
                                    }
                                ]
                            }
                        ],
                    }
                ]
            }, None
        if path.endswith("connections"):
            return {"value": [{"id": "private"}]}, None
        if path.endswith("shortcuts"):
            return {"value": [{"id": "private"}, {"id": "private2"}]}, None
        return None, "HTTP 404"

    def request(self, method, path, json):
        assert method == "POST"
        assert path == "catalog/search"
        assert json["search"] == "Demo"
        self.catalog_payload = json
        return object()

    @staticmethod
    def json(_response):
        return {
            "value": [
                {"workspaceId": "workspace-id"},
                {"id": "lakehouse-id"},
            ]
        }


def test_inventory_retains_counts_but_not_principal_or_connection_details():
    snapshot = collect_snapshot(Client(), "Demo")
    assert snapshot.role_counts == {"Admin": {"Group": 1}}
    assert snapshot.git_state == "ConnectedAndInitialized"
    assert snapshot.catalog_matches == 1
    assert snapshot.connection_counts["Lakehouse:lh_demo"] == 1
    assert snapshot.shortcut_counts["Lakehouse:lh_demo"] == 2
    assert snapshot.data_access["Lakehouse:lh_demo"]["broad_default_reader"] is True
    assert "private" not in repr(snapshot.role_counts)
    assert "private" not in repr(snapshot.connection_counts)
