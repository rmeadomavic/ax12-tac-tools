#!/usr/bin/env python3
"""Verify launcher.py and tools.json reference only files that exist.

Exits non-zero with a list of missing references if anything is broken. Run
from the repo root or from anywhere — paths resolve relative to this file's
grandparent (the repo root).
"""

import ast
import json
import os
import re
import sys


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT_RE = re.compile(r"(?:^|[\s/])(tools/[A-Za-z0-9_.-]+\.py)\b")


def tools_refs_from_launcher(path):
    """Yield every tools/*.py reference in the CATEGORIES list literal."""
    with open(path) as f:
        tree = ast.parse(f.read(), filename=path)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "CATEGORIES" for t in node.targets
        ):
            # Walk the literal, pulling f-string and plain-string pieces
            for sub in ast.walk(node.value):
                if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                    for m in SCRIPT_RE.findall(sub.value):
                        yield m
                elif isinstance(sub, ast.JoinedStr):
                    text = "".join(
                        p.value if isinstance(p, ast.Constant) else "{}"
                        for p in sub.values
                        if isinstance(p, (ast.Constant, ast.FormattedValue))
                    )
                    for m in SCRIPT_RE.findall(text):
                        yield m


def tools_refs_from_config(path):
    with open(path) as f:
        data = json.load(f)
    for cat in data.get("categories", []):
        for tool in cat.get("tools", []):
            cmd = tool.get("cmd", "")
            if cmd.startswith("__"):
                continue
            for m in SCRIPT_RE.findall(cmd):
                yield (cat.get("name"), tool.get("label"), m)


def main():
    missing = []

    launcher = os.path.join(REPO_ROOT, "launcher.py")
    for rel in tools_refs_from_launcher(launcher):
        if not os.path.exists(os.path.join(REPO_ROOT, rel)):
            missing.append(f"launcher.py -> {rel}")

    config = os.path.join(REPO_ROOT, "tools.json")
    for cat, label, rel in tools_refs_from_config(config):
        if not os.path.exists(os.path.join(REPO_ROOT, rel)):
            missing.append(f"tools.json[{cat}/{label}] -> {rel}")

    if missing:
        print("Broken launcher references:")
        for m in missing:
            print(f"  {m}")
        return 1

    print("Launcher consistency: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
