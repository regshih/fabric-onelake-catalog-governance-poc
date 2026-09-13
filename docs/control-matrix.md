# Governance control matrix

| ID | Practice | Automated evidence | Automated change | Required human/tenant action |
|---|---|---|---|---|
| GOV-001 | Durable domain assignment | Workspace has a domain | Assign an existing visible domain | Architects approve taxonomy; Fabric admin creates domains |
| CAT-001 | Useful workspace description | Minimum length | Set approved policy description | Owner validates accuracy |
| CAT-002 | Useful item descriptions | Presence per nonmanaged item | Set manifest descriptions | Data steward owns meaning, grain, SLA, audience |
| CAT-003 | Naming convention | Regex by item type | None; renames can break dependencies | Impact analysis and exception decision |
| CAT-004 | Controlled tags | Required names vs applied tags | Apply existing tag definitions | Fabric/domain admin owns vocabulary |
| CAT-005 | Catalog discoverability | Catalog Search result count | Metadata improvements only | Verify as a consumer after propagation |
| PRO-001 | Sensitivity labels | Label presence for configured data types | None | Purview policy/label owner selects and publishes labels |
| SEC-001 | Group-first workspace access | Counts direct users in privileged roles | None | Access review, group/PIM design, break-glass exception |
| SEC-002 | OneLake least privilege | Role presence and broad DefaultReader signal | Policy role merge with ETag and server dry-run | Approve groups/rules; test as Viewer/item-Read |
| SRC-001 | Source/shortcut/mirror boundaries | Counts visible references | None | Validate source owner, credentials, exfiltration, target policy |
| TRU-001 | Promotion/certification/master data | Manual control | None | Authorized quality/governance review |
| LIN-001 | End-to-end lineage | Counts do not assert completeness | Demo pipeline creates a dependency | Inspect lineage and impact analysis |
| LCM-001 | Lifecycle/source control | Fabric Git connection state | None | Protected branch, deployment pipeline, backup/recovery design |
| OPS-001 | Audit, OneLake diagnostics, DLP, retention | Manual control | None | Tenant/compliance administrator configuration and test |

## Severity and disposition

- `FAIL`: release-blocking policy requirement.
- `WARN`: material gap, limitation, or risky default that needs an owner and due date.
- `MANUAL`: cannot be proven safely from workspace REST metadata; retain review evidence elsewhere.
- `PASS`: the automated assertion passed. It is not proof of end-to-end compliance.
- `NOT_APPLICABLE`: disabled or excluded by policy.
