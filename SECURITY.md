# Security policy

## Public-repository rules

This repository may contain only synthetic data and environment-neutral configuration. Never commit passwords, client secrets, certificates/private keys, storage keys, SAS tokens, PATs, bearer tokens, connection strings, cookies, notebook outputs, customer data, Fabric connection definitions, or generated reports.

Also keep tenant/subscription/workspace/item/capacity/domain/principal/operation IDs, source endpoints, private repository URLs, and screenshots of customer context out of the public tree. These identifiers are not all credentials, but this project treats them as private environment inventory.

Use Azure CLI, managed identity, workload identity, or another `DefaultAzureCredential` provider. Entra group and tenant IDs for role deployment belong in the process environment or an approved secret/variable store; `.env` is ignored.

## Release gate

Before every public release:

```powershell
python -m pytest
ruff check .
python tools/security_scan.py --working-tree --git-history
```

Review notebook sources for output, pipeline definitions for bound IDs, and reports/logs/screenshots manually. GitHub Actions also runs Gitleaks and the repository scanner.

If a real secret was ever committed, revoke or rotate it before rewriting history. Do not open a public issue containing the value. If customer data or private identifiers were published, follow the customer's incident process.

## OneLake role change safety

Role updates can unintentionally broaden or remove access. The role-change helpers read all roles, preserve every unrelated writable field, use the returned ETag, perform Fabric's server-side dry-run, and require `--apply`. Named-role removal is a separate explicit command and becomes a no-op when the target is absent. Peer review is still mandatory. Retain the pre-change role document in protected storage and test allowed/denied behavior with Viewer or item-Read identities.

## Reporting vulnerabilities

Use GitHub's private vulnerability reporting for this repository. Include affected file paths and impact, but never include active credentials or customer data.
