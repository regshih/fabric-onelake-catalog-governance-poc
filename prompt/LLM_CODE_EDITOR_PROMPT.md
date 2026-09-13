# LLM code-editor prompt: adapt this OneLake governance POC

Copy everything below into an LLM-enabled code editor while the repository root is open. Replace only bracketed inputs. Do not paste secrets or tenant/resource IDs into the prompt.

---

You are adapting this public Microsoft Fabric OneLake catalog governance repository for a customer proof of concept.

Customer context:

- Business domains: `[approved domain/subdomain names or “not yet approved”]`
- Environments: `[development/test/production arrangement]`
- Workspace naming convention: `[convention]`
- In-scope Fabric item types: `[lakehouses, warehouses, notebooks, pipelines, semantic models, mirrored items, shortcuts, etc.]`
- Data classifications: `[approved classification names]`
- Approved Fabric tag vocabulary: `[tag display names or “not yet defined”]`
- Sensitivity-label requirements: `[policy intent; never include label IDs]`
- OneLake consumer personas: `[group purposes, never object IDs or user emails]`
- Quality/certification process: `[reviewers and criteria]`
- Audit/DLP/retention requirements: `[policy intent]`
- Source systems and shortcut/mirror patterns: `[generic names and trust boundaries only]`

Your task:

1. Read the entire repository, especially `README.md`, `SECURITY.md`, `docs/control-matrix.md`, `docs/adoption-runbook.md`, `docs/known-limitations.md`, and `policy/governance-policy.yaml`.
2. Inspect the working tree before editing. Preserve unrelated user changes. Do not create or change Azure, Fabric, Entra, Purview, or GitHub resources unless I separately authorize deployment.
3. Verify current Microsoft documentation before changing any Fabric API path, payload, permission, item support list, preview status, or security recommendation. Use only Microsoft primary documentation for technical claims.
4. Customize the versioned policy with durable domain intent, approved tag names, item descriptions, naming rules, sensitivity-label coverage, and OneLake role templates. Keep IDs out of tracked files; role templates must reference environment-variable names.
5. Keep the tool generic for existing workspaces. Unknown item types must remain visible and result in meaningful or manual controls, never silently disappear.
6. Preserve these safety invariants:
   - passwordless `DefaultAzureCredential`; no secret/token CLI parameters;
   - dry-run by default and explicit `--apply` for writes;
   - no delete, rename, capacity start/stop/resize, sharing, or role-removal automation;
   - no report fields containing tenant, subscription, capacity, workspace, item, domain, operation, principal, or connection IDs;
   - OneLake full-role updates preserve every existing role/field, use the GET ETag, call `dryRun=true`, and only then apply the identical payload;
   - no claim that Admin/Member/Contributor identities are restricted by OneLake roles;
   - no automatic certification, master-data endorsement, label selection, DLP, or compliance claim.
7. Add or update tests for every behavior change. Tests must prove reports are redacted, dry-runs do not write, policy validation fails closed, definition placeholders do not remain, and role merges preserve unrelated content.
8. Update customer documentation with prerequisites, responsibility split, exact dry-run/apply commands, validation using Viewer/item-Read identities across Spark/SQL/OneLake APIs/shortcuts/reports/exports, rollback, limitations, and evidence-retention guidance.
9. Run unit tests, lint, the working-tree/history security scan, and inspect `git diff`. Do not weaken a scanner or test just to make it pass.
10. Report the files changed, verification performed, remaining administrator/manual steps, and any assumption. Never claim a live control was applied unless you observed it in the target tenant.

If information is missing, make only reversible repository changes and write the missing decision as a clearly owned prerequisite. Stop before a tenant-wide, access-changing, destructive, costly, or public-publishing action that was not explicitly authorized.

---
