# Customer adoption runbook

## 1. Establish ownership before changing the tenant

Name the Fabric platform owner, domain owner, workspace/data-product owner, data steward, and security owner. Add compliance, sensitivity-label, and certification owners only when those optional organizational controls are in scope. Agree on escalation and evidence retention. A repository maintainer should not unilaterally create a new business domain, tag taxonomy, or certify data.

## 2. Define durable boundaries

Map workspaces to business ownership and regulatory/security boundaries. Prefer durable domains such as Finance or Customer Analytics over project names. Separate development, test, and production. Use capacities for compute isolation/chargeback, not as the only access boundary.

For OneLake security at scale, select a primary producer workspace, apply the data rules there, and expose governed shortcuts to consumer workspaces.

## 3. Customize policy as code

Fork the repository and edit `policy/governance-policy.yaml`:

- Replace the sample domain and domain description.
- Replace the tag vocabulary with approved tenant/domain tags.
- Add exact descriptions for known items.
- Adjust naming patterns without renaming existing contracts blindly.
- Optionally define which item types require organizational sensitivity labels; leave the list empty when native Fabric tags satisfy the POC scope.
- Define OneLake paths, RLS/CLS predicates, and environment-variable names for Entra groups.
- Record exceptions in the customer's change/evidence system; do not hide them by weakening global defaults.

Keep IDs and environment output outside Git. Use `.governance.local.yaml` or a protected pipeline variable store when a local overlay is necessary.

## 4. Baseline the current estate

Run `onelake-governance assess`. Review every item, including mirrored items, shortcuts, notebooks, pipelines, semantic models, warehouses, lakehouses, and system-generated companions. Confirm that unknown item types are still described, owned, classified, and assessed manually where APIs do not expose sufficient evidence.

For each connection, mirror, or shortcut, document the source owner, authentication method, credential owner/rotation, network boundary, data classification, source-side access, target-side access, and incident path. Mirroring does not carry every source permission into Fabric.

## 5. Apply catalog metadata

Have an authorized admin create the approved domain/tag vocabulary. Run remediation without `--apply`, review the change set, then run with `--apply`. Wait for catalog/search propagation and verify as a normal consumer—not only as a workspace administrator.

Promote content when it is useful. Certify or mark master data only after the organization’s quality gate, owner approval, freshness/SLA checks, documentation, and security review.

## 6. Apply protection and access

Use native tenant/domain tags for OneLake Catalog classification and discovery. They are defined and applied entirely in Fabric. If the customer also uses sensitivity labels, monitor coverage in the OneLake Catalog Govern experience, then confirm that the underlying Microsoft Purview Information Protection labels are published to the data owners before applying them. Sensitivity labels are optional in this POC and have licensing, inheritance, export, and API limitations.

Use Entra security groups, not individual users, for durable workspace and OneLake membership. Keep consumers as Viewer or item-Read wherever possible. Review `DefaultReader` and every overlapping role before restricting anything. For SQL analytics endpoints, switch deliberately to user identity mode when OneLake security should be evaluated per user.

Before each role application:

1. Export/retain the current role response and ETag in a protected evidence store.
2. Run the repository command without `--apply` and confirm the Fabric server dry-run succeeds.
3. Peer-review RLS/CLS expressions, explicit paths, and group membership.
4. Apply during an approved change window.
5. Test allowed and prohibited Spark, SQL, OneLake API, shortcut, report, and export scenarios using least-privileged test identities.

## 7. Validate lineage and operations

Use lineage and impact analysis from sources/mirrors through pipelines/notebooks and storage to semantic models/reports. Resolve orphaned items and undocumented cross-workspace dependencies.

Enable tenant audit logs and OneLake diagnostics where appropriate. Route them to a protected monitoring destination with alerting, retention, access review, and an operational owner. Configure DLP, sensitivity-label protection policies, and private networking only when required by organizational policy and licensing.

## 8. Operationalize

Run the assessment after releases and on a schedule. Keep reports in protected evidence storage, not this public repository. Fail promotion when `FAIL > 0`; require explicit dispositions for `WARN` and `MANUAL`. Revalidate after new item types, API changes, workspace moves, new shortcuts/mirrors, security-role edits, and sensitivity-policy changes.

## Rollback

Metadata descriptions can be restored from the prior approved policy. Tags can be unapplied using Fabric APIs after impact review. A workspace can be unassigned from a domain by an authorized administrator. OneLake roles are full-replacement resources: restore the protected pre-change response using its current ETag and server dry-run. Never use stale ETags or a report as a role backup.
