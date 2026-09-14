# Least-privileged test identities

Use disposable, nonhuman identities to prove OneLake access boundaries without granting a tester broad workspace permissions. Keep all tenant and principal IDs outside Git.

## Recommended group model

| Security group | Fabric use | Membership |
|---|---|---|
| `fabric-olcg-workspace-admins-poc` | Workspace `Admin` | POC owners only |
| `fabric-olcg-api-service-principals-poc` | Allowlist for the tenant setting that permits service principals to call Fabric public APIs | Test service principals only |
| `fabric-olcg-public-readers-poc` | Workspace `Viewer` and `PublicMetricsReader` OneLake role | Public-reader test identity |
| `fabric-olcg-us-restricted-readers-poc` | Workspace `Viewer` and `UsRestrictedMetricsReader` OneLake role | Restricted-reader test identity |

Use separate groups for API eligibility and data authorization. Enabling a principal to call Fabric APIs must not grant it access to a workspace or data.

## Identity baseline

Create single-tenant app registrations and their service principals without redirect URIs, Microsoft Graph/Fabric API permissions, directory roles, client secrets, or certificates. Add each service principal to the API allowlist group and exactly its intended data-reader group. Assign ownership of the app registrations to an approved lifecycle owner.

Scope **Service principals can call Fabric public APIs** to the API allowlist group. Do not enable it for the entire tenant solely for a POC. Grant the two reader groups workspace `Viewer`; do not use `Contributor`, `Member`, or `Admin`, because those roles bypass OneLake security.

Keep a direct workspace administrator only as a documented break-glass path while validating that group-based administration works. Remove or formally accept that exception after a second administrator has confirmed access through the admin group.

## Validation matrix

| Test principal | Workspace metadata | `public_metrics` | `restricted_customer_metrics` |
|---|---|---|---|
| Public reader | Allow | Allow | Deny |
| US restricted reader | Allow | Deny unless separately granted | Allow US rows and approved columns through a supported Fabric engine |

ADLS/OneLake API reads of a table protected by row- or column-level rules should be blocked because that access path cannot apply the filters. Validate the restricted table through Spark, Lakehouse, Direct Lake on OneLake, or a SQL analytics endpoint configured for user-identity mode. Test both approved and prohibited columns and confirm that only `US` rows are returned.

OneLake RLS values must be complete statements, for example:

```sql
SELECT * FROM [restricted_customer_metrics] WHERE [region] = 'US'
```

## Credential handling for tests

Prefer workload identity federation, managed identity, or a certificate held in an approved secret store. If an ephemeral client secret is unavoidable for a one-time test:

1. Create it only after access roles are configured.
2. Keep it in process memory; never print or write it to disk.
3. Use it only to obtain the required Fabric and Storage audience tokens.
4. Revoke it in a `finally`/cleanup step and verify that the app registration has no credentials afterward.
5. Retain only pass/fail status and HTTP status categories in the protected evidence location.

Service principals do not replace human Viewer tests. Before production adoption, repeat Spark, SQL, shortcut, report, export, and catalog-discovery scenarios with representative least-privileged users whose access arrives through the same groups.
