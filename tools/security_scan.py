#!/usr/bin/env python3
"""Scan public content/history for secret patterns and private environment identifiers."""

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IGNORED_PARTS = {".git", ".venv", "venv", "reports", "__pycache__", ".pytest_cache"}
TEXT_SUFFIXES = {
    "",
    ".bicep",
    ".cfg",
    ".csv",
    ".example",
    ".ini",
    ".ipynb",
    ".json",
    ".kql",
    ".md",
    ".py",
    ".ps1",
    ".sh",
    ".sql",
    ".tf",
    ".tfvars",
    ".toml",
    ".tsv",
    ".txt",
    ".xml",
    ".yaml",
    ".yml",
}
PATTERNS = {
    "azure-resource-id": re.compile(r"/subscriptions/[0-9a-f-]{36}/", re.I),
    "uuid": re.compile(
        r"(?<![0-9a-f])[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}(?![0-9a-f])",
        re.I,
    ),
    "github-token": re.compile(r"\bgh(?:p|o|u|s|r)_[A-Za-z0-9]{20,}\b"),
    "bearer-token": re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{20,}", re.I),
    "sas-signature": re.compile(r"(?:[?&]|\b)sig=[A-Za-z0-9%+/=-]{12,}", re.I),
    "credential-assignment": re.compile(
        r"\b(?:password|passwd|pwd|client_secret|accountkey|access_token)\s*[:=]\s*['\"]?[^<\s'\"]{8,}",
        re.I,
    ),
    "entra-tenant-address": re.compile(
        r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.onmicrosoft\.com\b", re.I
    ),
    "fabric-sql-endpoint": re.compile(
        r"\b[A-Z0-9-]{12,}(?:\.[A-Z0-9-]+)*\.datawarehouse\.fabric\.microsoft\.com\b",
        re.I,
    ),
    "onelake-abfss-endpoint": re.compile(
        r"\babfss://[A-Z0-9._-]+@onelake\.dfs\.fabric\.microsoft\.com/[A-Z0-9._/-]+",
        re.I,
    ),
    "private-key": re.compile(
        r"-----BEGIN (?:RSA |EC |OPENSSH )?" + r"PRIVATE KEY-----", re.I
    ),
}
ALLOW_UUIDS = {"00000000-0000-0000-0000-000000000000"}


def scan_text(label: str, text: str) -> list[tuple[str, str]]:
    findings: list[tuple[str, str]] = []
    for pattern_name, pattern in PATTERNS.items():
        for match in pattern.finditer(text):
            if pattern_name == "uuid" and match.group(0).lower() in ALLOW_UUIDS:
                continue
            findings.append((label, pattern_name))
            break
    return findings


def working_tree_files() -> list[Path]:
    return [
        path
        for path in ROOT.rglob("*")
        if path.is_file()
        and not any(part in IGNORED_PARTS for part in path.relative_to(ROOT).parts)
        and path.suffix.lower() in TEXT_SUFFIXES
    ]


def scan_working_tree() -> list[tuple[str, str]]:
    findings: list[tuple[str, str]] = []
    for path in working_tree_files():
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        findings.extend(scan_text(path.relative_to(ROOT).as_posix(), text))
    return findings


def scan_history() -> list[tuple[str, str]]:
    revisions = subprocess.run(
        ["git", "rev-list", "--all"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    findings: list[tuple[str, str]] = []
    for revision in revisions:
        listing = subprocess.run(
            ["git", "ls-tree", "-r", "--name-only", revision],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
        for name in listing:
            if Path(name).suffix.lower() not in TEXT_SUFFIXES:
                continue
            blob = subprocess.run(
                ["git", "show", f"{revision}:{name}"],
                cwd=ROOT,
                check=False,
                capture_output=True,
            )
            if blob.returncode or b"\x00" in blob.stdout:
                continue
            findings.extend(scan_text(name, blob.stdout.decode("utf-8", errors="replace")))
    return sorted(set(findings))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--working-tree", action="store_true")
    parser.add_argument("--git-history", action="store_true")
    args = parser.parse_args()
    if not args.working_tree and not args.git_history:
        parser.error("select --working-tree and/or --git-history")
    findings: list[tuple[str, str]] = []
    if args.working_tree:
        findings.extend(scan_working_tree())
    if args.git_history:
        findings.extend(scan_history())
    for path, pattern_name in sorted(set(findings)):
        print(f"BLOCKED {path}: matched {pattern_name}")
    if findings:
        raise SystemExit(1)
    print("PASS: no configured secret or environment-identifier patterns found")


if __name__ == "__main__":
    main()
