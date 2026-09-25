import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "security_scan.py"
SPEC = importlib.util.spec_from_file_location("security_scan", MODULE_PATH)
assert SPEC and SPEC.loader
SECURITY_SCAN = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SECURITY_SCAN)
scan_text = SECURITY_SCAN.scan_text


def finding_types(text: str) -> set[str]:
    return {finding_type for _label, finding_type in scan_text("fixture", text)}


def test_flags_private_environment_endpoints_and_credentials():
    tenant_address = "reader@" + "customer." + "onmicrosoft.com"
    sql_endpoint = "abcdefghijklmnop." + "tenant.datawarehouse.fabric.microsoft.com"
    onelake_endpoint = (
        "abfss://workspace@" + "onelake.dfs.fabric.microsoft.com/lakehouse/Tables/table"
    )
    private_key = "-----BEGIN " + "PRIVATE KEY-----"

    assert "entra-tenant-address" in finding_types(tenant_address)
    assert "fabric-sql-endpoint" in finding_types(sql_endpoint)
    assert "onelake-abfss-endpoint" in finding_types(onelake_endpoint)
    assert "private-key" in finding_types(private_key)


def test_allows_public_placeholders_and_generic_hosts():
    text = "\n".join(
        [
            "FABRIC_TENANT_ID=<tenant-id>",
            "reader@<tenant-domain>.onmicrosoft.com",
            "https://onelake.dfs.fabric.microsoft.com",
            "<sql-endpoint>.datawarehouse.fabric.microsoft.com",
        ]
    )

    assert scan_text("fixture", text) == []
