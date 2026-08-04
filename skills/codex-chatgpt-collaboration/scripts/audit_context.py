#!/usr/bin/env python3
"""Fail-closed, read-only audit for files proposed as ChatGPT context."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path


EXCLUDED_PARTS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    "__pycache__",
    ".pytest_cache",
    ".next",
}
FORBIDDEN_SUFFIXES = {
    ".db",
    ".sqlite",
    ".sqlite3",
    ".pem",
    ".key",
    ".p12",
    ".pfx",
    ".jks",
    ".keystore",
}
SECRET_PATTERNS = {
    "private-key": re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----"),
    "aws-access-key": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "github-token": re.compile(r"\bgh(?:p|o|u|s|r)_[A-Za-z0-9]{20,}\b"),
    "openai-key": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    "credential-assignment": re.compile(
        r"(?i)\b(?:api[_-]?key|access[_-]?token|secret|password)\b\s*[:=]\s*[\"']?[^\s\"']{8,}"
    ),
}


def inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def audit_file(path_arg: str, root: Path, max_bytes: int) -> dict[str, object]:
    requested = Path(path_arg)
    path = (requested if requested.is_absolute() else root / requested).resolve()
    result: dict[str, object] = {"requested": path_arg, "path": None, "status": "REJECT", "findings": []}
    findings: list[str] = result["findings"]  # type: ignore[assignment]

    if not inside(path, root):
        findings.append("outside-repository")
        return result

    result["path"] = path.relative_to(root).as_posix()
    relative_parts = {part.lower() for part in path.relative_to(root).parts}
    name_lower = path.name.lower()
    if relative_parts & EXCLUDED_PARTS:
        findings.append("excluded-directory")
    if name_lower == ".env" or name_lower.startswith(".env."):
        findings.append("environment-file")
    if path.suffix.lower() in FORBIDDEN_SUFFIXES:
        findings.append("forbidden-file-type")
    if not path.is_file():
        findings.append("not-a-regular-file")
        return result

    data = path.read_bytes()
    result["bytes"] = len(data)
    result["sha256"] = hashlib.sha256(data).hexdigest()
    if len(data) > max_bytes:
        findings.append("file-too-large")
    if b"\x00" in data:
        findings.append("binary-content")

    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        findings.append("non-utf8-content")
        text = ""

    for label, pattern in SECRET_PATTERNS.items():
        if pattern.search(text):
            findings.append(f"possible-{label}")

    if not findings:
        result["status"] = "PASS"
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+", help="Explicit repository-relative files to audit")
    parser.add_argument("--repo", required=True, help="Repository root")
    parser.add_argument("--max-bytes", type=int, default=1_000_000)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.repo).resolve()
    if not root.is_dir():
        print(json.dumps({"status": "ERROR", "error": "repository root is not a directory"}, indent=2))
        return 2
    if args.max_bytes < 1:
        print(json.dumps({"status": "ERROR", "error": "max-bytes must be positive"}, indent=2))
        return 2

    files = [audit_file(item, root, args.max_bytes) for item in args.files]
    status = "PASS" if all(item["status"] == "PASS" for item in files) else "REJECT"
    print(json.dumps({"status": status, "scanner": "lightweight-pattern-gate", "files": files}, indent=2))
    return 0 if status == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())

