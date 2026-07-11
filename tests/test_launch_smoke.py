#!/usr/bin/env python3
"""Launch smoke test for every Python tool registered in tools.json.

The syntax-only CI (py_compile / luac / shellcheck) cannot catch a launcher
entry that points at the wrong subcommand or flag: the file compiles fine, it
just exits 2 (argparse usage error) or bails with "unknown command" the moment
an operator taps the button. Two such crash-on-launch bugs shipped this way
(PAYLOAD DROP -> `calc` with unmet required args; ROVER NAV -> `--demo` instead
of the `demo` dispatch key). This test reproduces the launch and asserts the
tool actually accepted its command line.

Strategy (no hardware, no root, pure stdlib):
  * Read tools.json, and for each tool whose `cmd` invokes a `tools/*.py`
    script, rebuild the invocation locally: drop the `su 0` prefix and the
    hard-coded Termux python path, run `sys.executable tools/<name>.py <args>`
    from the repo root with stdin redirected from os.devnull and a timeout.
  * A launch is BROKEN if the process exits 2 (argparse usage error), prints a
    Python traceback, or emits a dispatch-rejection phrase ("unknown command",
    "invalid choice", "the following arguments are required", ...). Everything
    else is a healthy launch: exit 0, a legitimate runtime failure that got
    past argument parsing (e.g. gps_tool.py exiting 1 with "No GPS position"),
    or a long-running tool still alive when the timeout kills it.

Run: `python3 tests/test_launch_smoke.py`  (exit 0 = all launched, 1 = a crash)
"""

import json
import os
import re
import shlex
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_JSON = os.path.join(REPO_ROOT, "tools.json")

# Seconds to let each tool run. Argparse/dispatch failures surface in well
# under a second; long-running tools (bridges) are killed at the timeout and
# counted as a healthy launch. Override for slow CI via AX12_SMOKE_TIMEOUT.
TIMEOUT = float(os.environ.get("AX12_SMOKE_TIMEOUT", "6"))

# Output that proves the tool rejected its command line rather than running.
# Exit code 2 is handled separately; these catch non-argparse dispatchers
# (rover_nav prints "Unknown command: ..." and exits 1) and any tool that
# swallows SystemExit but still prints an argparse usage error.
LAUNCH_REJECT_RE = re.compile(
    r"unknown command"
    r"|unknown subcommand"
    r"|no such command"
    r"|invalid choice"
    r"|unrecognized arguments"
    r"|the following arguments are required",
    re.IGNORECASE,
)

TRACEBACK_MARKER = "Traceback (most recent call last)"

# Tools that must always be probed. If a refactor renames or unregisters one of
# these, this guard trips so the regression net is never silently emptied.
REQUIRED_TOOLS = {"payload_drop.py", "rover_nav.py"}


def load_registered_tools():
    """Yield (label, tool_path, args) for each registered Python tool.

    Non-Python cmds (bash scripts) and internal `__specials__` are skipped.
    """
    with open(TOOLS_JSON, encoding="utf-8") as f:
        data = json.load(f)

    for cat in data.get("categories", []):
        for tool in cat.get("tools", []):
            label = tool.get("label", "?")
            cmd = tool.get("cmd", "")
            if not cmd or cmd.startswith("__"):
                continue

            tokens = shlex.split(cmd)
            py_index = next(
                (i for i, t in enumerate(tokens) if t.endswith(".py")), None
            )
            if py_index is None:
                continue  # not a Python tool (e.g. a bash launcher script)

            tool_path = os.path.join(
                REPO_ROOT, "tools", os.path.basename(tokens[py_index])
            )
            args = tokens[py_index + 1 :]
            yield label, tool_path, args


def probe(tool_path, args):
    """Launch one tool. Return (ok, detail) — ok=False means crash-on-launch."""
    if not os.path.exists(tool_path):
        return False, f"missing file: {tool_path}"

    argv = [sys.executable, tool_path, *args]
    try:
        with open(os.devnull) as devnull:
            proc = subprocess.run(
                argv,
                cwd=REPO_ROOT,
                stdin=devnull,
                capture_output=True,
                text=True,
                timeout=TIMEOUT,
            )
    except subprocess.TimeoutExpired:
        return True, f"still running at {TIMEOUT:g}s (launched OK)"

    combined = (proc.stdout or "") + (proc.stderr or "")

    if proc.returncode == 2:
        return False, "exit 2 (argparse usage error)"
    if TRACEBACK_MARKER in combined:
        return False, "uncaught traceback on launch"
    match = LAUNCH_REJECT_RE.search(combined)
    if match:
        return False, f"command rejected: {match.group(0)!r} (exit {proc.returncode})"

    return True, f"exit {proc.returncode}"


def main():
    tools = list(load_registered_tools())
    probed_names = {os.path.basename(p) for _, p, _ in tools}

    missing_required = REQUIRED_TOOLS - probed_names
    if missing_required:
        print(
            "SMOKE TEST BROKEN: expected tools not registered/parsed: "
            + ", ".join(sorted(missing_required))
        )
        return 1
    if not tools:
        print("SMOKE TEST BROKEN: no Python tools parsed from tools.json")
        return 1

    failures = []
    print(f"Launch smoke test - {len(tools)} Python tools (timeout {TIMEOUT:g}s)\n")
    for label, tool_path, args in tools:
        ok, detail = probe(tool_path, args)
        invocation = f"{os.path.basename(tool_path)} {' '.join(args)}".strip()
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {label:<16} {invocation:<28} {detail}")
        if not ok:
            failures.append((label, invocation, detail))

    print()
    if failures:
        print(f"{len(failures)} tool(s) crash on launch:")
        for label, invocation, detail in failures:
            print(f"  - {label} ({invocation}): {detail}")
        return 1

    print(f"All {len(tools)} registered tools launch cleanly.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
