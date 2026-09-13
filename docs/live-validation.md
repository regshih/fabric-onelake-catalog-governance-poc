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
| Unit tests and lint | Pass | 41 tests, 91% coverage, Ruff clean |
| Public-tree secret/privacy scan | Pass | No configured finding; values never printed |
| Git history secret/privacy scan | Pass | Full reachable history scanned after the initial commit and immediately before public push |
| Workspace and four demo items created | Pass | Lakehouse, warehouse, notebook, and pipeline; lakehouse also produced its managed SQL endpoint |
| Pipeline definition read-back | Pass | One bound notebook activity present |
| Synthetic notebook run | Pass | Completed; no row output retained |
| Synthetic Delta tables | Pass | `public_metrics` and `restricted_customer_metrics` listed by the OneLake table API |
| Domain assignment | Pass | Assigned to an existing approved demonstration domain |
| Catalog search | Pass | Five workspace items returned after metadata propagation |
| OneLake security role read | Pass with warning | Role API available; broad `DefaultReader`/`ReadAll` behavior detected |
| Live policy assessment | Pass with open actions | 11 pass, 0 fail, 9 warn, 4 manual; report remains ignored/unpublished |
| Least-privileged access tests | Not run | Requires approved Entra test groups/users |
| Purview labels, DLP, audit, certification | Not run | Requires tenant/compliance administrators |

The signed-in identity is not a Fabric administrator: release-version admin domain/tag reads returned `403`. No new tenant domain or tag definition was created. The workspace uses the pre-existing demonstration domain. No OneLake role was changed because approved Entra consumer groups and least-privileged test identities were not supplied. The Fabric workspace is not connected to Git because a supported, separately managed Git credential was not available; the public GitHub repository remains the source for the toolkit and demo definitions.

Do not interpret an automated `PASS` as a compliance certification. Customer deployments must repeat the tests in their own tenant with least-privileged identities and retain detailed evidence in an approved private location.
