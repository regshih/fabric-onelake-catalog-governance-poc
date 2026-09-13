# Known limitations

- OneLake Catalog Search and OneLake data access role APIs can be preview capabilities. Pin tests to the behavior you validate and review API changes before production use.
- Catalog/search/tag propagation is not immediate. A zero-result search immediately after a change is not conclusive.
- Fabric REST metadata does not prove that displayed descriptions, owners, lineage, schemas, refresh status, endorsements, or security are correct.
- The CLI checks sensitivity-label presence, not policy appropriateness, encryption behavior, inheritance, DLP, or licensing. Default/mandatory labeling has limitations for non-Power BI items and API/service-principal flows.
- Certification and master-data endorsement are approval decisions and are not automated.
- Workspace role counts do not expand nested group membership, prove PIM controls, or identify stale accounts.
- OneLake security is a grant model. Another role, workspace role, item share, engine-specific permission, or source permission can grant broader access.
- Workspace Admins, Members, and Contributors are not constrained by OneLake roles. Validate with Viewer/item-Read identities.
- SQL analytics endpoint enforcement depends on access mode. Use user identity mode when OneLake policy should be evaluated per consumer.
- Item-type support varies for OneLake roles, connections, shortcuts, Git, labels, and APIs. Unknown/unsupported surfaces become manual controls.
- Mirroring and shortcuts have source-specific authentication and permission behavior. Inventory counts are only a prompt for a source-boundary review.
- Fabric Git does not include data, credentials, connections, every item type, or every tenant/workspace setting. It is not a complete backup.
- The demo does not create real source connections, mirrored databases, shortcuts, semantic models, reports, Entra groups, Purview policies, audit pipelines, or production monitoring.
- No automated tool can certify regulatory compliance. Apply organizational policy, legal/compliance review, threat modeling, and workload-specific testing.
