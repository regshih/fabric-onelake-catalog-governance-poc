# Live validation record

This file records only public-safe facts. It deliberately excludes tenant, subscription, capacity, workspace, domain, item, operation, principal, and connection IDs.

## Validation environment

- Validation date: 2026-09-13
- Authentication: passwordless Microsoft Entra user via Azure CLI / `DefaultAzureCredential`
- Capacity: existing active Fabric capacity; no capacity was provisioned or resized
- Data: deterministic synthetic records only

## Results

| Check | Status | Evidence retained here |
|---|---|---|
| Unit tests and lint | Pass | 43 tests, 92% coverage, Ruff clean |
| Public-tree secret/privacy scan | Pass | No configured finding; values never printed |
| Git history secret/privacy scan | Pass | Full reachable history scanned after the initial commit and immediately before public push |
| GitHub release state | Pass | Repository is private pending owner review; public-release security controls remain enabled |
| Workspace and four demo items created | Pass | Lakehouse, warehouse, notebook, and pipeline; lakehouse also produced its managed SQL endpoint |
| Pipeline definition read-back | Pass | One bound notebook activity present |
| Synthetic notebook run | Pass | Completed; no row output retained |
| Synthetic Delta tables | Pass | `public_metrics` and `restricted_customer_metrics` listed by the OneLake table API |
| Domain assignment | Pass | Assigned to an existing approved demonstration domain |
| Catalog search | Pass | Five workspace items returned after metadata propagation |
| Entra test identity baseline | Pass | Four security groups and two single-tenant service principals; test principals have no API permissions or retained credentials |
| Group-based workspace roles | Pass with exception | Admin group and two Viewer groups assigned; direct owner remains temporarily as a break-glass path |
| OneLake security roles | Pass with warning | Public table role and US RLS/CLS role applied after server dry-runs; broad `DefaultReader` remains but does not apply to the Viewer-only test groups |
| Live policy assessment | Pending refresh | Prior result was 11 pass, 0 fail, 9 warn, 4 manual; report remains ignored/unpublished |
| Least-privileged access tests | In progress | Interactive token refresh required after the administrator policy change; ephemeral test credentials are revoked after each attempt |
| Purview labels, DLP, audit, certification | Not run | Requires tenant/compliance administrators |

The Fabric Administrator directory role is now present on the signed-in identity. The installed Azure CLI client obtains only Fabric's `user_impersonation` delegated scope, so admin domain/tag calls that require `Tenant.ReadWrite.All` still return `403 InsufficientScopes`; no tenant domain or tag definition has been created yet. The workspace remains assigned to the pre-existing demonstration domain. The Fabric workspace is not connected to Git because Fabric requires a separately configured GitHub credential connection; the private GitHub repository remains the source for the toolkit and demo definitions pending review.

Do not interpret an automated `PASS` as a compliance certification. Customer deployments must repeat the tests in their own tenant with least-privileged identities and retain detailed evidence in an approved private location.
