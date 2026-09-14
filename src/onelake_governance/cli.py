"""Command-line interface for assessment, remediation, and the demo estate."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from dotenv import load_dotenv

from .admin import admin_changes_to_dict, bootstrap_admin_objects
from .assessment import assess
from .bootstrap import bootstrap_demo
from .client import FabricClient
from .inventory import collect_snapshot
from .onelake_security import apply_policy_role, remove_named_role
from .policy import load_policy
from .remediation import changes_to_dict, plan_remediation
from .reporting import write_report

ROOT = Path(__file__).resolve().parents[2]


def _workspace(args: argparse.Namespace) -> str:
    value = (args.workspace or os.getenv("FABRIC_WORKSPACE_NAME", "")).strip()
    if not value:
        raise SystemExit("Set --workspace or FABRIC_WORKSPACE_NAME")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="onelake-governance",
        description="Policy-as-code governance for Microsoft Fabric OneLake catalog.",
    )
    parser.add_argument("--policy", default=str(ROOT / "policy" / "governance-policy.yaml"))
    subparsers = parser.add_subparsers(dest="command", required=True)

    assess_parser = subparsers.add_parser("assess", help="inventory and assess a workspace")
    assess_parser.add_argument("--workspace", default="")
    assess_parser.add_argument("--output", default="reports/governance-assessment")

    remediate = subparsers.add_parser("remediate", help="plan/apply safe metadata remediation")
    remediate.add_argument("--workspace", default="")
    remediate.add_argument("--domain", default=os.getenv("FABRIC_DOMAIN_NAME", ""))
    remediate.add_argument("--apply", action="store_true")

    demo = subparsers.add_parser("bootstrap-demo", help="create the synthetic reference estate")
    demo.add_argument("--workspace", default="")
    demo.add_argument("--capacity", default=os.getenv("FABRIC_CAPACITY_NAME", ""))
    demo.add_argument("--domain", default=os.getenv("FABRIC_DOMAIN_NAME", ""))
    demo.add_argument("--apply", action="store_true")
    demo.add_argument("--run-seed", action="store_true")

    admin = subparsers.add_parser("admin-bootstrap", help="plan/create domain and tenant tags")
    admin.add_argument("--apply", action="store_true")

    security = subparsers.add_parser(
        "apply-onelake-role", help="server-dry-run/apply one policy-defined role"
    )
    security.add_argument("--workspace", default="")
    security.add_argument("--lakehouse", required=True)
    security.add_argument("--role", required=True)
    security.add_argument("--apply", action="store_true")

    remove_security = subparsers.add_parser(
        "remove-onelake-role", help="server-dry-run/remove one explicitly named role"
    )
    remove_security.add_argument("--workspace", default="")
    remove_security.add_argument("--lakehouse", required=True)
    remove_security.add_argument("--role", required=True)
    remove_security.add_argument("--apply", action="store_true")
    return parser


def main() -> None:
    load_dotenv(ROOT / ".env")
    args = build_parser().parse_args()
    policy = load_policy(args.policy)
    client = FabricClient()
    if args.command == "assess":
        report = assess(collect_snapshot(client, _workspace(args)), policy)
        json_path, markdown_path = write_report(report, args.output)
        print(
            json.dumps(
                {
                    "summary": report.summary,
                    "json_report": str(json_path),
                    "markdown_report": str(markdown_path),
                },
                indent=2,
            )
        )
    elif args.command == "remediate":
        changes = plan_remediation(
            client, _workspace(args), policy, domain_name=args.domain, apply=args.apply
        )
        print(json.dumps(changes_to_dict(changes, applied=args.apply), indent=2))
    elif args.command == "bootstrap-demo":
        if not args.capacity:
            raise SystemExit("Set --capacity or FABRIC_CAPACITY_NAME")
        value = bootstrap_demo(
            client,
            workspace_name=_workspace(args),
            capacity_name=args.capacity,
            domain_name=args.domain,
            root=ROOT,
            apply=args.apply,
            run_seed=args.run_seed,
        )
        print(json.dumps(value, indent=2))
    elif args.command == "admin-bootstrap":
        changes = bootstrap_admin_objects(client, policy, apply=args.apply)
        print(json.dumps(admin_changes_to_dict(changes, applied=args.apply), indent=2))
    elif args.command == "apply-onelake-role":
        roles = policy.get("onelake_roles", {}).get(args.lakehouse, [])
        matches = [role for role in roles if role.get("name") == args.role]
        if len(matches) != 1:
            raise SystemExit("Policy must contain exactly one matching lakehouse role")
        value = apply_policy_role(
            client,
            _workspace(args),
            args.lakehouse,
            matches[0],
            apply=args.apply,
        )
        print(json.dumps(value, indent=2))
    elif args.command == "remove-onelake-role":
        value = remove_named_role(
            client,
            _workspace(args),
            args.lakehouse,
            args.role,
            apply=args.apply,
        )
        print(json.dumps(value, indent=2))


if __name__ == "__main__":
    main()
