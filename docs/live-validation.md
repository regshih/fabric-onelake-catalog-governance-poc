# Live validation record

This file records only public-safe facts. It deliberately excludes tenant, subscription, capacity, workspace, domain, item, operation, principal, and connection IDs.

## Validation environment

- Validation date: 2026-09-14
- Authentication: passwordless Microsoft Entra user via Azure CLI / `DefaultAzureCredential`
- Capacity: existing active Fabric capacity; no capacity was provisioned or resized
- Data: deterministic synthetic records only

## Results

| Check | Status | Evidence retained here |
|---|---|---|
| Unit tests and lint | Pass | 51 tests, 92% coverage, Ruff clean |
| Public-tree secret/privacy scan | Pass | No configured finding; values never printed |
| Git history secret/privacy scan | Pass | Full reachable history scanned after the initial commit and before the private review handoff |
| GitHub release state | Pass | Repository is private pending owner review; public-release security controls remain enabled |
| Workspace and four demo items created | Pass | Lakehouse, warehouse, notebook, and pipeline; lakehouse also produced its managed SQL endpoint |
| Pipeline definition read-back | Pass | One bound notebook activity present |
| Synthetic notebook run | Pass | Completed; no row output retained |
| Synthetic Delta tables | Pass | `public_metrics` and `restricted_customer_metrics` listed by the OneLake table API |
| Tenant governance vocabulary | Pass | `Customer Analytics` domain and six controlled tenant tags created through the Fabric admin APIs |
| Domain assignment | Pass | Workspace assigned to the policy-approved `Customer Analytics` domain |
| Catalog tagging | Pass | Required classification, lifecycle, quality, and medallion-layer tags applied to all four governed items |
| Catalog search | Pass | Five workspace items returned after metadata propagation |
| Entra test identity baseline | Pass | Four security groups and two single-tenant service principals; every object has a lifecycle owner, and test principals have no API permissions or retained credentials |
| Group-based workspace roles | Pass with accepted POC exception | Admin group and two Viewer groups assigned; direct owner remains for POC recovery and is documented for customer review |
| `DefaultReader` impact review | Pass | Only the direct Admin and Admin group hold effective `ReadAll`; neither Viewer group was included |
| OneLake security roles | Pass | Broad `DefaultReader` removed after an ETag-protected server dry-run; public and US RLS/CLS roles preserved; repeated removal is a no-op |
| Live policy assessment | Pass with follow-up | 16 pass, 0 fail, 2 warn, 4 manual; detailed report remains ignored/unpublished |
| Public-reader isolation | Pass | Revalidated after `DefaultReader` removal: public table returned `200`; restricted table returned `403` |
| Restricted-reader isolation | Pass | Revalidated after `DefaultReader` removal: public table returned `403`; restricted-table directory returned `200`; raw restricted Parquet access remains blocked because that path cannot enforce RLS/CLS |
| Ephemeral identity credentials | Pass | Credentials were created only for the tests, revoked immediately afterward, and both applications were verified to retain zero credentials |
| Fabric service-principal tenant setting | Pass | The dedicated API allow-list group was added while preserving the existing scoped group configuration |
| SQL endpoint mode-change precheck | Pass | Endpoint is healthy and contains no custom SQL security policies, predicates, explicit database permissions, views, procedures, or functions |
| Supported-engine RLS/CLS positive test | Awaiting one Fabric UI setting | The SQL endpoint is healthy but remains in delegated-identity mode with zero synchronized `OLS_` roles; switch it to User's identity access mode, wait for sync, then run the documented allowed-row/hidden-column test |
| Native Fabric classification tags | Pass | Classification tags are defined, applied, discoverable, and managed in Fabric/OneLake Catalog without an external catalog deployment |
| Organizational sensitivity labels, DLP, certification | Not in POC scope | Optional customer controls; OneLake Catalog surfaces governance insights, while sensitivity labels remain backed by the organization's Microsoft Purview Information Protection label policy |

After a fresh interactive sign-in, the Fabric administrator APIs accepted the scoped governance changes. Repeated dry-runs for tenant bootstrap and workspace remediation return zero changes, and repeated `DefaultReader` removal is a no-op, demonstrating idempotency. The Fabric workspace is not connected to Git: the repository stays private for review, and the project intentionally does not persist the broad GitHub CLI credential as a Fabric connection. Create a separate fine-grained GitHub token with only the required repository contents permission when Git integration is approved.

Do not interpret an automated `PASS` as a compliance certification. Customer deployments must repeat the tests in their own tenant with least-privileged identities and retain detailed evidence in an approved private location.
