# AX12 Tactical Tools — Installer & Guide Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a one-command installer, TUI launcher, and getting-started guide so community AX12 owners can go from zero to "drone on ATAK map" with one paste.

**Architecture:** Four new files in the repo root and docs/. `install.sh` bootstraps the device and clones the repo. `launcher.py` is a curses TUI with direct CLI shortcuts. Two markdown guides cover onboarding and TAK integration. No changes to existing files.

**Tech Stack:** Bash (installer), Python 3 stdlib + curses (launcher), Markdown (guides)

**Spec:** `docs/superpowers/specs/2026-04-15-installer-and-guide-design.md`

**Existing reference:** `ax12-research/tools/launcher_tui.py` — proven curses TUI pattern for the AX12 touchscreen. The new launcher follows its structure (color pairs, run_tool pattern, mouse support) but is scoped to tac-tools.

**Parallelism:** Tasks 1-4 are independent and can be dispatched to parallel agents. Task 5 (AX12 device test) depends on all four completing. Task 5 should run on the AX12 via SSH agent.

---

### Task 1: install.sh — Bootstrap Installer

**Files:**
- Create: `install.sh` (repo root)

This is a Bash script that runs in Termux on Android. It handles two phases: device setup (packages, SSH) and tool install (clone repo, copy Lua, create alias). It must be idempotent and work when piped from curl.

- [ ] **Step 1: Create install.sh with environment detection and phase 1**

Create `install.sh` at the repo root with the shebang, environment check, colorized output helpers, and phase 1 (package installation + SSH setup):

```bash
#!/data/data/com.termux/files/usr/bin/bash
# AX12 Tactical Tools — One-Command Installer
# Usage: pkg install -y curl && curl -sL https://raw.githubusercontent.com/rmeadomavic/ax12-tac-tools/main/install.sh | bash
set -euo pipefail

# --- Colors and output helpers ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'
BOLD='\033[1m'

ok()   { echo -e "  ${GREEN}[OK]${NC}   $1"; }
skip() { echo -e "  ${YELLOW}[SKIP]${NC} $1"; }
fail() { echo -e "  ${RED}[FAIL]${NC} $1"; }
info() { echo -e "  ${CYAN}[INFO]${NC} $1"; }
header() { echo -e "\n${BOLD}${CYAN}=== $1 ===${NC}\n"; }

# --- Environment check ---
if [ ! -d "/data/data/com.termux" ]; then
    fail "This script must be run inside Termux on an Android device."
    echo "  Install Termux from F-Droid: https://f-droid.org/en/packages/com.termux/"
    exit 1
fi

PYTHON3="/data/data/com.termux/files/usr/bin/python3"
REPO_DIR="$HOME/ax12-tac-tools"
REPO_URL="https://github.com/rmeadomavic/ax12-tac-tools.git"
LUA_SRC="$REPO_DIR/lua"
LUA_DEST="/storage/emulated/0/AX12LUA/SCRIPTS/TOOLS"

echo ""
echo -e "${BOLD}${CYAN}╔══════════════════════════════════════╗${NC}"
echo -e "${BOLD}${CYAN}║   AX12 TACTICAL TOOLS — INSTALLER   ║${NC}"
echo -e "${BOLD}${CYAN}╚══════════════════════════════════════╝${NC}"
echo ""

# ============================================================
# PHASE 1: Device Setup
# ============================================================
header "PHASE 1: Device Setup"

# --- Package update ---
info "Updating package repos..."
pkg update -y 2>&1 | tail -1
pkg upgrade -y 2>&1 | tail -1
ok "Packages updated"

# --- Required packages ---
REQUIRED_PKGS="python openssh git curl wget"
for pkg_name in $REQUIRED_PKGS; do
    if dpkg -s "$pkg_name" >/dev/null 2>&1; then
        skip "$pkg_name (already installed)"
    else
        info "Installing $pkg_name..."
        pkg install -y "$pkg_name" 2>&1 | tail -1
        ok "$pkg_name installed"
    fi
done

# --- Optional advanced packages ---
echo ""
read -p "  Install advanced tools (strace, binutils, dtc)? [y/N] " -n 1 -r ADV
echo ""
if [[ "$ADV" =~ ^[Yy]$ ]]; then
    for pkg_name in binutils dtc strace; do
        if dpkg -s "$pkg_name" >/dev/null 2>&1; then
            skip "$pkg_name (already installed)"
        else
            info "Installing $pkg_name..."
            pkg install -y "$pkg_name" 2>&1 | tail -1
            ok "$pkg_name installed"
        fi
    done
fi

# --- SSH setup ---
if [ -f "$HOME/.ssh/authorized_keys" ] || [ -f "/data/data/com.termux/files/usr/etc/ssh/sshd_config" ]; then
    skip "SSH already configured"
else
    info "Setting up SSH..."
    echo "  You'll need to set a password for SSH login."
    passwd
    ok "SSH password set"
fi

# Start sshd if not running
if pgrep sshd >/dev/null 2>&1; then
    skip "sshd already running"
else
    sshd
    ok "sshd started on port 8022"
fi

# Auto-start sshd on boot (if Termux:Boot is installed)
BOOT_DIR="$HOME/.termux/boot"
BOOT_SCRIPT="$BOOT_DIR/start-sshd.sh"
if [ -d "$BOOT_DIR" ]; then
    if [ -f "$BOOT_SCRIPT" ]; then
        skip "sshd boot script already exists"
    else
        echo '#!/data/data/com.termux/files/usr/bin/bash
sshd' > "$BOOT_SCRIPT"
        chmod +x "$BOOT_SCRIPT"
        ok "sshd auto-start configured (Termux:Boot)"
    fi
else
    info "Termux:Boot not detected — sshd won't auto-start on reboot"
    info "Install Termux:Boot from F-Droid for persistent SSH"
fi

# Print connection info
IP=$(ip -4 addr show wlan0 2>/dev/null | grep -oP 'inet \K[\d.]+' || echo "unknown")
echo ""
info "SSH connection: ssh -p 8022 $IP"

# --- Tailscale (optional) ---
echo ""
read -p "  Set up Tailscale for remote access? [y/N] " -n 1 -r TS
echo ""
if [[ "$TS" =~ ^[Yy]$ ]]; then
    echo ""
    info "Tailscale requires a manual APK install:"
    info "  1. Open browser on the AX12 → tailscale.com/download/android"
    info "  2. Download and install the APK"
    info "  3. Open Tailscale, sign in with your account"
    info "  4. Your AX12 will get a stable 100.x.x.x IP"
    echo ""
fi
```

- [ ] **Step 2: Add phase 2 (tool install) and self-test to install.sh**

Append phase 2 to `install.sh` — clone/update repo, copy Lua scripts, set up the `tac` alias, run self-test, print summary:

```bash
# ============================================================
# PHASE 2: Tool Install
# ============================================================
header "PHASE 2: Tool Install"

# --- Clone or update repo ---
if [ -d "$REPO_DIR/.git" ]; then
    info "Updating existing install..."
    git -C "$REPO_DIR" pull --ff-only 2>&1 | tail -1
    ok "Repository updated"
else
    info "Cloning ax12-tac-tools..."
    git clone "$REPO_URL" "$REPO_DIR" 2>&1 | tail -1
    ok "Repository cloned to $REPO_DIR"
fi

# --- Copy Lua scripts ---
info "Installing Lua scripts to Flyshark..."
if [ -d "$LUA_SRC" ]; then
    su 0 mkdir -p "$LUA_DEST" 2>/dev/null || true
    LUA_COUNT=0
    for f in "$LUA_SRC"/*.lua; do
        [ -f "$f" ] || continue
        su 0 cp "$f" "$LUA_DEST/" 2>/dev/null
        LUA_COUNT=$((LUA_COUNT + 1))
    done
    if [ "$LUA_COUNT" -gt 0 ]; then
        ok "$LUA_COUNT Lua scripts installed to Flyshark"
    else
        fail "No .lua files found in $LUA_SRC"
    fi
else
    fail "Lua directory not found: $LUA_SRC"
fi

# --- Create tac alias ---
TAC_ALIAS="alias tac='$PYTHON3 $REPO_DIR/launcher.py'"
if grep -q "alias tac=" "$HOME/.bashrc" 2>/dev/null; then
    # Update existing alias
    sed -i "s|alias tac=.*|$TAC_ALIAS|" "$HOME/.bashrc"
    skip "tac alias updated in .bashrc"
else
    echo "" >> "$HOME/.bashrc"
    echo "# AX12 Tactical Tools launcher" >> "$HOME/.bashrc"
    echo "$TAC_ALIAS" >> "$HOME/.bashrc"
    ok "tac alias added to .bashrc"
fi

# Source bashrc for current session
eval "$TAC_ALIAS"

# ============================================================
# SELF-TEST
# ============================================================
header "Self-Test"

PASS=0
TOTAL=0

# Python version
TOTAL=$((TOTAL + 1))
PY_VER=$($PYTHON3 --version 2>&1)
if [ $? -eq 0 ]; then
    ok "Python: $PY_VER"
    PASS=$((PASS + 1))
else
    fail "Python not working"
fi

# Repo present
TOTAL=$((TOTAL + 1))
if [ -f "$REPO_DIR/launcher.py" ]; then
    ok "Launcher: present"
    PASS=$((PASS + 1))
else
    fail "Launcher: missing ($REPO_DIR/launcher.py)"
fi

# Lua scripts installed
TOTAL=$((TOTAL + 1))
LUA_INSTALLED=$(su 0 ls "$LUA_DEST"/*.lua 2>/dev/null | wc -l)
if [ "$LUA_INSTALLED" -gt 0 ]; then
    ok "Lua scripts: $LUA_INSTALLED files in Flyshark"
    PASS=$((PASS + 1))
else
    fail "Lua scripts: none found in $LUA_DEST"
fi

# Serial port
TOTAL=$((TOTAL + 1))
if [ -c /dev/ttyS0 ]; then
    ok "Serial: /dev/ttyS0 exists"
    PASS=$((PASS + 1))
else
    skip "Serial: /dev/ttyS0 not found (normal if not on AX12)"
    PASS=$((PASS + 1))
fi

# Root access
TOTAL=$((TOTAL + 1))
ROOT_CHECK=$(su 0 id 2>/dev/null | grep "uid=0" || true)
if [ -n "$ROOT_CHECK" ]; then
    ok "Root: available (su 0)"
    PASS=$((PASS + 1))
else
    fail "Root: su 0 not working"
fi

# ============================================================
# SUMMARY
# ============================================================
header "Installation Complete"

echo -e "  ${BOLD}Results: $PASS/$TOTAL checks passed${NC}"
echo ""
echo -e "  ${BOLD}${GREEN}Type 'tac' to open the launcher menu${NC}"
echo -e "  ${BOLD}${GREEN}Type 'tac atak' to start the ATAK bridge${NC}"
echo ""
echo -e "  Lua scripts are in Flyshark: System Menu > Lua Scripts > Tools"
echo ""
echo -e "  For the full guide: ${CYAN}$REPO_DIR/GETTING_STARTED.md${NC}"
echo -e "  For TAK integration: ${CYAN}$REPO_DIR/docs/tak-setup.md${NC}"
echo ""
```

- [ ] **Step 3: Make install.sh executable and commit**

```bash
cd ~/ax12-tac-tools
chmod +x install.sh
git add install.sh
git commit -m "Add one-command bootstrap installer

Idempotent install.sh for curl-pipe deployment. Phase 1 handles
Termux packages, SSH, and optional Tailscale. Phase 2 clones the
repo, deploys Lua scripts to Flyshark, and creates the tac alias.
Includes colorized output and self-test verification."
```

---

### Task 2: launcher.py — TUI Menu Launcher

**Files:**
- Create: `launcher.py` (repo root)

Curses-based TUI following the pattern from `ax12-research/tools/launcher_tui.py`. Adds CLI subcommand shortcuts (`tac atak`, `tac gps`, etc.). Stdlib only.

- [ ] **Step 1: Create launcher.py with tool registry and CLI shortcut dispatch**

Create `launcher.py` at the repo root. This includes the tool definitions, shortcut mapping, and the `main()` entry point that dispatches to either the TUI or a direct shortcut:

```python
#!/data/data/com.termux/files/usr/bin/python3
"""AX12 Tactical Tools — Launcher

Touch-friendly TUI menu for the RadioMaster AX12 touchscreen.
Also supports direct CLI shortcuts: tac atak, tac gps, etc.

Usage:
    python3 launcher.py          # open TUI menu
    python3 launcher.py atak     # launch ATAK CoT bridge directly
    python3 launcher.py --help   # list all shortcuts
"""

import curses
import os
import subprocess
import sys
import time

PYTHON3 = "/data/data/com.termux/files/usr/bin/python3"
REPO_DIR = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.join(REPO_DIR, "tools")
LUA_SRC = os.path.join(REPO_DIR, "lua")
LUA_DEST = "/storage/emulated/0/AX12LUA/SCRIPTS/TOOLS"

# --- Tool definitions ---
# (label, description, command, timeout_seconds, needs_root)
CATEGORIES = [
    ("TAK INTEGRATION", [
        ("ATAK CoT Bridge",  "Stream drone position to ATAK map",
         f"{PYTHON3} {TOOLS}/cot_bridge.py", 0, True),
        ("MAVLink Bridge",   "Connect QGC/Mission Planner via ELRS",
         f"{PYTHON3} {TOOLS}/mavlink_bridge.py bridge", 0, False),
        ("CoT Test Send",    "Send one test blip to verify ATAK",
         f"{PYTHON3} {TOOLS}/test_cot.py", 15, False),
    ]),
    ("FLIGHT OPS", [
        ("Airspace Brief",   "Pre-flight airspace restriction check",
         f"{PYTHON3} {TOOLS}/airspace_check.py brief", 30, True),
        ("Payload Drop Calc","Aerial drop point calculator",
         f"{PYTHON3} {TOOLS}/payload_drop.py calc", 30, True),
        ("Rover Navigation", "ArduRover GPS nav and geofencing",
         f"{PYTHON3} {TOOLS}/rover_nav.py --demo", 30, False),
        ("GPS Position",     "Current GPS fix from MT6631",
         f"{PYTHON3} {TOOLS}/gps_tool.py position", 15, True),
    ]),
    ("SENSORS", [
        ("IMU Tracker",      "ICM-42607 head tracking",
         f"{PYTHON3} {TOOLS}/imu_tracker.py", 0, True),
        ("GPS Monitor",      "Continuous GPS with NMEA/satellite info",
         f"{PYTHON3} {TOOLS}/gps_position.py", 0, True),
        ("Hydra AI Display", "Object detection telemetry client",
         f"{PYTHON3} {TOOLS}/hydra_display.py demo", 30, False),
    ]),
    ("SYSTEM", [
        ("Update Tools",     "git pull + re-copy Lua scripts",
         "__update__", 60, False),
        ("Reinstall Lua",    "Re-copy Lua scripts to Flyshark",
         "__lua__", 30, False),
        ("About",            "Version, repo URL, credits",
         "__about__", 0, False),
    ]),
]

# CLI shortcut name -> (label_to_find, extra_args)
SHORTCUTS = {
    "atak":     "ATAK CoT Bridge",
    "mavlink":  "MAVLink Bridge",
    "cot-test": "CoT Test Send",
    "airspace": "Airspace Brief",
    "drop":     "Payload Drop Calc",
    "rover":    "Rover Navigation",
    "gps":      "GPS Position",
    "imu":      "IMU Tracker",
    "gps-mon":  "GPS Monitor",
    "hydra":    "Hydra AI Display",
    "update":   "Update Tools",
    "lua":      "Reinstall Lua",
}

# Build flat item list: (category, label, description, command, timeout, needs_root)
ITEMS = []
for cat_name, tools in CATEGORIES:
    for label, desc, cmd, timeout, root in tools:
        ITEMS.append((cat_name, label, desc, cmd, timeout, root))


def find_item(label):
    """Find a tool item by its label."""
    for item in ITEMS:
        if item[1] == label:
            return item
    return None


def build_command(cmd, needs_root):
    """Prepend su 0 if the tool needs root."""
    if needs_root:
        return f"su 0 {cmd}"
    return cmd


def do_update():
    """Pull latest code and re-copy Lua scripts."""
    print(f"\n  Updating from git...")
    subprocess.run(["git", "-C", REPO_DIR, "pull", "--ff-only"])
    do_lua_copy()


def do_lua_copy():
    """Copy Lua scripts to Flyshark install path."""
    print(f"\n  Copying Lua scripts to Flyshark...")
    subprocess.run(["su", "0", "mkdir", "-p", LUA_DEST],
                   capture_output=True)
    count = 0
    for f in sorted(os.listdir(LUA_SRC)):
        if f.endswith(".lua"):
            src = os.path.join(LUA_SRC, f)
            subprocess.run(["su", "0", "cp", src, LUA_DEST + "/"],
                           capture_output=True)
            count += 1
    print(f"  {count} Lua scripts installed to {LUA_DEST}")


def do_about():
    """Print version and repo info."""
    print("\n  AX12 Tactical Tools")
    print(f"  Repo: https://github.com/rmeadomavic/ax12-tac-tools")
    print(f"  Path: {REPO_DIR}")
    # Show git version if available
    r = subprocess.run(["git", "-C", REPO_DIR, "log", "--oneline", "-1"],
                       capture_output=True, text=True)
    if r.returncode == 0:
        print(f"  Version: {r.stdout.strip()}")
    print(f"  Python: {sys.version.split()[0]}")
    lua_count = len([f for f in os.listdir(LUA_SRC) if f.endswith(".lua")])
    tool_count = len([f for f in os.listdir(TOOLS) if f.endswith(".py")])
    print(f"  Tools: {tool_count} Python, {lua_count} Lua")
    print()


def run_direct(label):
    """Run a tool directly (no TUI) by its label. Returns exit code."""
    item = find_item(label)
    if item is None:
        print(f"  Unknown tool: {label}")
        return 1

    _, _, desc, cmd, timeout, needs_root = item

    # Handle special commands
    if cmd == "__update__":
        do_update()
        return 0
    if cmd == "__lua__":
        do_lua_copy()
        return 0
    if cmd == "__about__":
        do_about()
        return 0

    full_cmd = build_command(cmd, needs_root)
    print(f"\n  {desc}")
    print(f"  Running: {full_cmd}\n")

    env = os.environ.copy()
    env["PATH"] = "/data/data/com.termux/files/usr/bin:" + env.get("PATH", "")
    env["HOME"] = os.path.expanduser("~")

    try:
        if timeout > 0:
            result = subprocess.run(full_cmd, shell=True, env=env,
                                    cwd=TOOLS, timeout=timeout)
        else:
            # timeout=0 means no limit (long-running tools like bridges)
            result = subprocess.run(full_cmd, shell=True, env=env, cwd=TOOLS)
        return result.returncode
    except subprocess.TimeoutExpired:
        print(f"\n  Timed out after {timeout}s")
        return 1
    except KeyboardInterrupt:
        print("\n  Stopped.")
        return 0


def print_help():
    """Print available shortcuts."""
    print("\n  AX12 Tactical Tools — Shortcuts\n")
    print("  Usage: tac [command]\n")
    for shortcut, label in sorted(SHORTCUTS.items()):
        item = find_item(label)
        if item:
            desc = item[2]
            print(f"    {shortcut:<12} {desc}")
    print()
    print("  Run 'tac' with no arguments to open the menu.")
    print()
```

- [ ] **Step 2: Add the curses TUI to launcher.py**

Append the curses TUI functions to `launcher.py`. These follow the proven pattern from `ax12-research/tools/launcher_tui.py` — same color scheme, same run_tool with scrollable output, same mouse support:

```python
# ============================================================
# Curses TUI
# ============================================================

def get_battery():
    """Read TX battery percentage."""
    try:
        r = subprocess.run(
            ["su", "0", "cat", "/sys/class/power_supply/battery/capacity"],
            capture_output=True, text=True, timeout=2)
        return r.stdout.strip() + "%" if r.returncode == 0 else "?"
    except Exception:
        return "?"


def get_uptime():
    """Read device uptime."""
    try:
        with open("/proc/uptime") as f:
            secs = int(float(f.read().split()[0]))
        h, m = secs // 3600, (secs % 3600) // 60
        return f"{h}h{m:02d}m"
    except Exception:
        return "?"


def tui_run_tool(stdscr, item):
    """Run a tool and show output in a scrollable view."""
    _, label, desc, cmd, timeout, needs_root = item
    curses.curs_set(0)
    stdscr.clear()
    h, w = stdscr.getmaxyx()

    # Handle special commands outside curses
    if cmd in ("__update__", "__lua__", "__about__"):
        curses.endwin()
        if cmd == "__update__":
            do_update()
        elif cmd == "__lua__":
            do_lua_copy()
        elif cmd == "__about__":
            do_about()
        print("\n  Press Enter to return to menu...")
        input()
        return

    full_cmd = build_command(cmd, needs_root)

    # Header
    stdscr.attron(curses.color_pair(2))
    header = f" RUNNING: {label} "
    stdscr.addstr(0, 0, header.ljust(w)[:w - 1])
    stdscr.attroff(curses.color_pair(2))

    timeout_str = f"{timeout}s" if timeout > 0 else "no limit"
    stdscr.attron(curses.color_pair(3))
    stdscr.addstr(1, 0, f" {desc} | Timeout: {timeout_str}"[:w - 1])
    stdscr.attroff(curses.color_pair(3))

    stdscr.attron(curses.color_pair(4))
    stdscr.addstr(3, 1, ">>> EXECUTING..."[:w - 2])
    stdscr.attroff(curses.color_pair(4))
    stdscr.refresh()

    # Run command
    env = os.environ.copy()
    env["PATH"] = "/data/data/com.termux/files/usr/bin:" + env.get("PATH", "")
    env["HOME"] = os.path.expanduser("~")
    env["TERM"] = "dumb"

    start = time.time()
    try:
        t = timeout if timeout > 0 else None
        proc = subprocess.run(full_cmd, shell=True, capture_output=True,
                              text=True, timeout=t, env=env, cwd=TOOLS)
        elapsed = round(time.time() - start, 1)
        output = proc.stdout
        if proc.stderr:
            output += ("\n--- stderr ---\n" + proc.stderr) if output else proc.stderr
        rc = proc.returncode
    except subprocess.TimeoutExpired:
        elapsed = round(time.time() - start, 1)
        output = f"TIMEOUT after {timeout}s"
        rc = -1
    except Exception as e:
        elapsed = round(time.time() - start, 1)
        output = f"Error: {e}"
        rc = -2

    # Display results
    stdscr.clear()
    if rc == 0:
        stdscr.attron(curses.color_pair(5))
        status = f"COMPLETE ({elapsed}s)"
    elif rc == -1:
        stdscr.attron(curses.color_pair(6))
        status = f"TIMEOUT ({elapsed}s)"
    else:
        stdscr.attron(curses.color_pair(6))
        status = f"EXIT {rc} ({elapsed}s)"

    stdscr.addstr(0, 0, f" {label}: {status}"[:w - 1].ljust(w)[:w - 1])
    if rc == 0:
        stdscr.attroff(curses.color_pair(5))
    else:
        stdscr.attroff(curses.color_pair(6))

    # Output lines with scrolling
    lines = output.strip().split("\n") if output.strip() else ["(no output)"]
    scroll = 0
    view_h = h - 3

    def draw_output():
        for i in range(view_h):
            li = scroll + i
            y = 2 + i
            if y >= h - 1:
                break
            stdscr.move(y, 0)
            stdscr.clrtoeol()
            if li < len(lines):
                line = lines[li][:w - 2]
                color = curses.color_pair(4) if rc == 0 else curses.color_pair(6)
                stdscr.attron(color)
                stdscr.addstr(y, 1, line)
                stdscr.attroff(color)

        stdscr.attron(curses.color_pair(3))
        footer = f" [{scroll + 1}-{min(scroll + view_h, len(lines))}/{len(lines)}] PRESS ANY KEY TO RETURN "
        if h > 1:
            stdscr.addstr(h - 1, 0, footer[:w - 1].ljust(w)[:w - 1])
        stdscr.attroff(curses.color_pair(3))
        stdscr.refresh()

    draw_output()

    # Scroll and wait for dismiss
    stdscr.timeout(-1)
    while True:
        key = stdscr.getch()
        if key == curses.KEY_DOWN and scroll < max(0, len(lines) - view_h):
            scroll += 1
            draw_output()
        elif key == curses.KEY_UP and scroll > 0:
            scroll -= 1
            draw_output()
        elif key == curses.KEY_NPAGE:
            scroll = min(scroll + view_h, max(0, len(lines) - view_h))
            draw_output()
        elif key == curses.KEY_PPAGE:
            scroll = max(0, scroll - view_h)
            draw_output()
        else:
            break


def tui_main(stdscr):
    """Main TUI loop."""
    curses.curs_set(0)
    curses.start_color()
    curses.use_default_colors()

    # Color pairs (same as ax12-research launcher)
    curses.init_pair(1, curses.COLOR_CYAN, -1)       # category header
    curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_CYAN)  # title bar
    curses.init_pair(3, curses.COLOR_WHITE,
                     235 if curses.COLORS >= 256 else curses.COLOR_BLACK)  # dim
    curses.init_pair(4, curses.COLOR_CYAN, -1)       # output / description
    curses.init_pair(5, curses.COLOR_GREEN, -1)      # success
    curses.init_pair(6, curses.COLOR_RED, -1)        # error
    curses.init_pair(7, curses.COLOR_YELLOW, -1)     # selected
    curses.init_pair(8, curses.COLOR_WHITE, -1)      # normal item

    selected = 0
    batt = get_battery()
    uptime = get_uptime()

    while True:
        stdscr.clear()
        h, w = stdscr.getmaxyx()

        # Title bar
        stdscr.attron(curses.color_pair(2))
        title = " AX12 TACTICAL TOOLS "
        status_str = f" BATT {batt} | UP {uptime} "
        pad = max(0, w - len(title) - len(status_str))
        header_line = title + " " * pad + status_str
        stdscr.addstr(0, 0, header_line[:w - 1].ljust(w)[:w - 1])
        stdscr.attroff(curses.color_pair(2))

        # Items
        y = 2
        item_idx = 0
        last_cat = ""

        for cat_name, label, desc, cmd, timeout, root in ITEMS:
            if y >= h - 2:
                break

            # Category header
            if cat_name != last_cat:
                if y < h - 1:
                    stdscr.attron(curses.color_pair(1))
                    stdscr.addstr(y, 0, f"  {cat_name}"[:w - 1])
                    stdscr.attroff(curses.color_pair(1))
                    y += 1
                last_cat = cat_name

            if y >= h - 2:
                break

            # Menu item
            prefix = " >> " if item_idx == selected else "    "
            line = f"{prefix}{label}"

            if item_idx == selected:
                stdscr.attron(curses.color_pair(7) | curses.A_BOLD)
                stdscr.addstr(y, 0, line[:w - 1].ljust(w - 1))
                stdscr.attroff(curses.color_pair(7) | curses.A_BOLD)
                # Show description on the line below
                if y + 1 < h - 1:
                    stdscr.attron(curses.color_pair(4))
                    stdscr.addstr(y, len(line) + 1, f"  {desc}"[:w - len(line) - 2])
                    stdscr.attroff(curses.color_pair(4))
            else:
                stdscr.attron(curses.color_pair(8))
                stdscr.addstr(y, 0, line[:w - 1])
                stdscr.attroff(curses.color_pair(8))

            y += 1
            item_idx += 1

        # Footer
        stdscr.attron(curses.color_pair(3))
        footer = " [UP/DOWN] Select  [ENTER] Run  [Q] Quit "
        if h > 1:
            stdscr.addstr(h - 1, 0, footer[:w - 1].ljust(w)[:w - 1])
        stdscr.attroff(curses.color_pair(3))

        stdscr.refresh()

        # Input
        key = stdscr.getch()

        if key == curses.KEY_UP or key == ord('k'):
            selected = max(0, selected - 1)
        elif key == curses.KEY_DOWN or key == ord('j'):
            selected = min(len(ITEMS) - 1, selected + 1)
        elif key == curses.KEY_HOME:
            selected = 0
        elif key == curses.KEY_END:
            selected = len(ITEMS) - 1
        elif key in (10, curses.KEY_ENTER):
            tui_run_tool(stdscr, ITEMS[selected])
            batt = get_battery()
            uptime = get_uptime()
        elif key in (ord('q'), ord('Q'), 27):
            break
        elif key == curses.KEY_MOUSE:
            try:
                _, mx, my, _, bstate = curses.getmouse()
                ty = 2
                last_c = ""
                for ci, item in enumerate(ITEMS):
                    cn = item[0]
                    if cn != last_c:
                        ty += 1
                        last_c = cn
                    if my == ty:
                        selected = ci
                        if bstate & (curses.BUTTON1_CLICKED | curses.BUTTON1_RELEASED):
                            tui_run_tool(stdscr, ITEMS[ci])
                            batt = get_battery()
                            uptime = get_uptime()
                        break
                    ty += 1
            except Exception:
                pass


# ============================================================
# Entry point
# ============================================================

if __name__ == "__main__":
    if len(sys.argv) > 1:
        arg = sys.argv[1]

        if arg in ("--help", "-h", "help"):
            print_help()
            sys.exit(0)

        label = SHORTCUTS.get(arg)
        if label is None:
            print(f"\n  Unknown command: {arg}")
            print_help()
            sys.exit(1)

        sys.exit(run_direct(label))
    else:
        # TUI mode
        os.environ.setdefault("TERM", "xterm-256color")
        try:
            curses.wrapper(tui_main)
        except KeyboardInterrupt:
            pass
```

- [ ] **Step 3: Commit launcher.py**

```bash
cd ~/ax12-tac-tools
git add launcher.py
git commit -m "Add TUI launcher with CLI shortcuts

Curses-based menu for touchscreen use in Termux. Organized into
TAK Integration, Flight Ops, Sensors, and System categories.
Direct shortcuts via 'tac atak', 'tac gps', etc. Built-in update
and Lua reinstall commands. Follows ax12-research launcher pattern."
```

---

### Task 3: GETTING_STARTED.md — User Guide

**Files:**
- Create: `GETTING_STARTED.md` (repo root)

Written for someone who just bought an AX12 and has never used a terminal. Friendly, direct, no jargon without explanation.

- [ ] **Step 1: Create GETTING_STARTED.md**

Create `GETTING_STARTED.md` at the repo root with the full guide content. This is a single-step task — write the entire document:

```markdown
# Getting Started with AX12 Tactical Tools

Your RadioMaster AX12 isn't just a remote control — it's a tactical computer running Android with GPS, WiFi, and a touchscreen. These tools unlock drone tracking on ATAK, mission planning, airspace awareness, and 20+ Lua scripts for the touchscreen. One install command, then you're operational.

## What You Need

- A RadioMaster AX12 (stock firmware, no modifications needed)
- A WiFi network
- About 30 minutes

## Step 1: Install Termux

Termux is a terminal app that gives your AX12 a proper Linux environment. **Do NOT install the Google Play version** — it's outdated and broken.

**Option A — From the AX12 (easiest):**
1. Open the browser on the AX12
2. Go to [github.com/termux/termux-app/releases](https://github.com/termux/termux-app/releases)
3. Download the latest `termux-app_*.apk` (pick the `universal` build)
4. Open the downloaded file and install it (you may need to allow "Install from unknown sources")

**Option B — From a computer via ADB:**
1. Download the Termux APK on your computer from the link above
2. Enable USB debugging on the AX12: Settings > About phone > tap Build Number 7 times > back to Settings > Developer Options > USB Debugging
3. Connect via USB and run: `adb install termux-app_*.apk`

## Step 2: Run the Installer

Open Termux on the AX12 and paste this single command:

```
pkg install -y curl && curl -sL https://raw.githubusercontent.com/rmeadomavic/ax12-tac-tools/main/install.sh | bash
```

The installer will:
- Install Python, Git, SSH, and other essentials
- Clone this repository to your device
- Copy all Lua scripts to the Flyshark app
- Set up the `tac` command for quick access
- Run a self-test to verify everything works

You'll see `[OK]`, `[SKIP]`, or `[FAIL]` for each step. If something fails, the error message will tell you what went wrong.

**This is safe to re-run.** If you ever want to update or something breaks, just paste the same command again.

## Step 3: Try It Out

Type `tac` to open the launcher menu:

```
╔══════════════════════════════════════╗
║ AX12 TACTICAL TOOLS    BATT 87% | UP 2h30m ║
╠══════════════════════════════════════╣
║  TAK INTEGRATION                     ║
║   >> ATAK CoT Bridge                 ║
║      MAVLink Bridge                  ║
║      CoT Test Send                   ║
║  FLIGHT OPS                          ║
║      Airspace Brief                  ║
║      ...                             ║
╚══════════════════════════════════════╝
```

Use arrow keys (or tap) to navigate, Enter to launch, Q to quit.

Or use shortcuts directly:
- `tac atak` — start the ATAK drone bridge
- `tac gps` — show your GPS position
- `tac airspace` — pre-flight airspace check
- `tac --help` — list all shortcuts

## TAK Integration (The Main Event)

### What is ATAK?

ATAK (Android Team Awareness Kit) is a military-grade mapping app that shows real-time positions of people, vehicles, and drones on a shared map. The AX12's CoT bridge streams your drone's GPS position to ATAK, so you (and your team) can see exactly where the drone is on the map.

### Install ATAK

Download ATAK-CIV (the civilian version) on the AX12:
- Official source: [tak.gov](https://tak.gov) (requires free registration)
- Alternative: search "ATAK-CIV" on the Play Store

### Configure ATAK

1. Open ATAK
2. Go to **Settings** (hamburger menu > Settings)
3. Select **Network Preferences**
4. Under **Network Connections**, add a new input:
   - **Protocol:** UDP
   - **Port:** 4242
   - **Address:** 0.0.0.0 (listen on all interfaces)
5. Save and go back to the map

### Test It

Run the CoT test to make sure ATAK is receiving:

```
tac cot-test
```

You should see a blue drone icon labeled "ELRS-Drone-1" appear on the ATAK map at coordinates 0,0 (Null Island, off the coast of Africa). If you see it, ATAK is working.

### Run the Live Bridge

To stream your actual drone's position to ATAK:

```
tac atak
```

This reads MAVLink telemetry from the ELRS receiver and converts it to CoT (Cursor-on-Target) format that ATAK understands. The drone will appear as a moving icon on the map with its callsign, altitude, speed, and flight mode.

**Requirements for live telemetry:**
- ELRS firmware 3.5+ on both TX and RX modules
- ELRS set to MAVLink link mode (not CRSF)
- ArduPilot flight controller configured for MAVLink on the RX UART

For the full MAVLink setup, see [docs/mavlink-setup.md](docs/mavlink-setup.md).

### Troubleshooting TAK

**No icon appears on the map:**
- Make sure ATAK's UDP input is on port 4242
- Run `tac cot-test` first — if that doesn't show up, ATAK isn't listening

**Icon appears but doesn't move (live bridge):**
- Check ELRS is in MAVLink mode (ELRS Lua > Link Mode > MAVLink)
- Check the FC's UART is configured: `SERIALn_PROTOCOL = 2`, `SERIALn_BAUD = 460`
- The RX must be ESP-based (RP1/RP2/RP3, EP1/EP2) — STM receivers don't support MAVLink

**"Serial port busy" error:**
- Another app has the serial port open. Close Flyshark first, or check for other tools using the port

## Lua Scripts

The installer automatically copies 20+ Lua scripts to Flyshark. Access them from:

**RadioMaster App > System Menu > Lua Scripts > Tools**

Highlights:

| Script | What It Does |
|--------|-------------|
| **TAK OSD** | Military HUD overlay — GPS, MGRS grid, compass, RSSI, mission timer |
| **CCIP** | Impact point targeting — physics model, range rings, RELEASE cue |
| **9-Line CAS** | Close air support brief template — auto-fills from GPS |
| **MGRS Tool** | Coordinate converter — WGS84 to MGRS, waypoint save, distance/bearing |
| **Preflight** | 12-item checklist with telemetry auto-check and GO/NO-GO |
| **Mission Timer** | 6-phase timer: STARTUP / LAUNCH / TRANSIT / ON STATION / RTB / RECOVERY |
| **Wind Calc** | Headwind/crosswind, Beaufort scale, GO/NO-GO for fixed-wing ops |

See the full list in [lua/README.md](lua/README.md).

## Updating

From the launcher menu: **System > Update Tools**

Or from the command line:

```
tac update
```

This pulls the latest code from GitHub and re-copies Lua scripts to Flyshark.

## Troubleshooting

**`su 0` gives "permission denied":**
The AX12 ships with root pre-installed (factory userdebug build). Run `su 0 id` — if it says `uid=0(root)`, root is working. If not, check `/system/xbin/su` exists.

**GPS shows "NO FIX":**
GPS needs a clear view of the sky. Go outside and wait 60 seconds for the first fix. The MT6631 chip can take a minute to acquire satellites from cold start.

**Serial port busy:**
The Flyshark app holds `/dev/ttyS0` while running. Tools that need direct serial access (IMU tracker, GPS monitor) require Flyshark to be closed first. The ATAK bridge uses `/dev/ttyS1` (a separate port) and works alongside Flyshark.

**Termux crashes or packages fail:**
Run `pkg update && pkg upgrade -y` to update everything. If that doesn't help, reinstall Termux from F-Droid.

**"Command not found: tac":**
The alias is set in `~/.bashrc`. Run `source ~/.bashrc` or close and reopen Termux.

## Deep Dive

For advanced topics — rooting, hardware teardown, UMBUS protocol, and research tooling — see the companion repository:

[github.com/rmeadomavic/ax12-research](https://github.com/rmeadomavic/ax12-research)

Key docs in that repo:
- **Root Guide** — Full device setup from scratch (Termux, SSH, Tailscale, Claude Code)
- **Hardware Teardown** — PCB photos, component IDs, debug pads, mod opportunities
- **UMBUS Protocol** — The proprietary serial protocol between Android and the MCU
- **Tool Usage Guide** — Reference for every research tool
```

- [ ] **Step 2: Commit GETTING_STARTED.md**

```bash
cd ~/ax12-tac-tools
git add GETTING_STARTED.md
git commit -m "Add getting-started guide for new AX12 owners

Plain-language guide covering Termux install, one-command setup,
TAK/ATAK integration walkthrough, Lua script access, updating,
and troubleshooting. Written for community users with no assumed
terminal experience."
```

---

### Task 4: docs/tak-setup.md — Dedicated TAK Integration Guide

**Files:**
- Create: `docs/tak-setup.md`

Deep-dive TAK guide for users who want the full picture beyond the getting-started overview.

- [ ] **Step 1: Create docs/tak-setup.md**

```markdown
# TAK Integration Guide

Complete guide to integrating the RadioMaster AX12 with ATAK (Android Team Awareness Kit) for real-time drone tracking and situational awareness.

## Architecture

```
                                           ┌─────────────┐
    ┌────────┐        ┌──────────┐         │    ATAK     │
    │ Vehicle │──RF──▶│ ELRS TX  │         │  (map app)  │
    │ (drone) │       │ module   │         └──────▲──────┘
    └────────┘        └────┬─────┘                │
                           │                      │ UDP :4242
                      ┌────▼──────────────────────┴───────┐
                      │        RadioMaster AX12            │
                      │                                    │
                      │  /dev/ttyS1 ──▶ cot_bridge.py     │
                      │  (MAVLink)      (MAVLink → CoT)   │
                      │                                    │
                      │  ELRS Backpack WiFi ──▶ mavlink_   │
                      │  (UDP :14550)     bridge.py        │
                      │                   (MAVLink → TCP)  │
                      │                         │          │
                      │                    ┌────▼────┐     │
                      │                    │   QGC   │     │
                      │                    │ (GCS)   │     │
                      │                    └─────────┘     │
                      └────────────────────────────────────┘
```

There are two data paths from the vehicle to the AX12:

1. **Serial (ttyS1):** ELRS passes MAVLink telemetry through the radio link to a dedicated UART on the AX12. The `cot_bridge.py` reads this and converts to CoT for ATAK. This is the primary path for the ATAK integration.

2. **WiFi (Backpack):** The ELRS TX Backpack creates a WiFi AP and forwards MAVLink via UDP. The `mavlink_bridge.py` bridges this to a TCP port for QGroundControl. This path is for full GCS functionality (mission upload, parameter tuning).

## Installing ATAK

### Option 1: CivTAK from tak.gov (Recommended)

1. Register at [tak.gov](https://tak.gov) (free, instant approval)
2. Download ATAK-CIV for Android
3. Transfer the APK to the AX12 and install

### Option 2: ATAK-CIV from Play Store

Search "ATAK-CIV" in the Google Play Store. Note: the AX12 may not have Play Store installed — use Option 1 or sideload via ADB.

### Option 3: Sideload via ADB

```bash
adb connect <AX12_IP>:5555
adb install ATAK-CIV-*.apk
```

## Configuring ATAK

### Network Input (Required)

ATAK needs a UDP listener to receive CoT events from the bridge:

1. Open ATAK
2. Hamburger menu > **Settings**
3. **Network Preferences** > **Network Connections**
4. Tap **+** to add a new input
5. Configure:
   - **Name:** AX12 Bridge
   - **Protocol:** UDP
   - **Port:** 4242
   - **Address:** 0.0.0.0
6. Save

### Map Data (Optional)

For offline maps (no cell signal in the field):

1. Download map tiles before going out (ATAK has a built-in tile downloader)
2. Or use the `maps/` folder in ATAK's data directory with custom tile packages

## Running the CoT Bridge

### Test Mode (No Drone Needed)

Verify the full chain works before going to the field:

```bash
tac cot-test
```

This sends a single CoT event placing a drone icon at Null Island (0,0). Open ATAK and check if "ELRS-Drone-1" appears on the map.

For continuous test data (drone orbits Null Island):

```bash
tac atak
# The bridge auto-falls back to synthetic data if no serial connection
```

### Live Mode (With Drone)

Prerequisites:
- ELRS TX and RX firmware 3.5.0+
- RX is ESP-based (RP1/RP2/RP3, EP1/EP2, BetaFPV Nano)
- ELRS set to MAVLink link mode (ELRS Lua > Link Mode > MAVLink)
- ArduPilot FC configured (see [mavlink-setup.md](mavlink-setup.md))

Launch:

```bash
tac atak
```

The bridge reads from `/dev/ttyS1` at 460800 baud and sends CoT to `127.0.0.1:4242` every 2 seconds.

### Configuration Options

For custom setups, run the bridge directly:

```bash
su 0 python3 ~/ax12-tac-tools/tools/cot_bridge.py \
    --port /dev/ttyS1 \
    --baud 460800 \
    --atak-host 127.0.0.1 \
    --atak-port 4242 \
    --uid MyDrone \
    --interval 2.0
```

| Option | Default | Description |
|--------|---------|-------------|
| `--port` | `/dev/ttyS1` | Serial port for MAVLink data |
| `--baud` | `460800` | Serial baud rate |
| `--atak-host` | `127.0.0.1` | ATAK UDP target IP |
| `--atak-port` | `4242` | ATAK UDP target port |
| `--uid` | `ELRS-Drone-1` | Callsign shown on the map |
| `--interval` | `2.0` | CoT send rate in seconds |
| `--test` | off | Use synthetic data (no serial) |

## Multi-Device Setup

The AX12 can bridge to ATAK running on a separate device (phone, tablet, laptop):

### Same WiFi Network

1. Run the CoT bridge on the AX12 with the other device's IP:
   ```bash
   su 0 python3 ~/ax12-tac-tools/tools/cot_bridge.py --atak-host 192.168.1.50
   ```
2. On the other device, configure ATAK's UDP input on port 4242

### Multicast (Multiple ATAK Clients)

To broadcast to all ATAK clients on the network:

```bash
su 0 python3 ~/ax12-tac-tools/tools/cot_bridge.py --atak-host 239.2.3.1
```

All ATAK clients listening on the `239.2.3.1` multicast group will receive the CoT events.

## CoT Details

### Type Codes

The bridge uses MIL-STD-2525C type codes:

| CoT Type | Meaning |
|----------|---------|
| `a-f-A-M-F-Q` | Friendly Air Military Fixed-wing UAV (default) |
| `a-f-G-U-C` | Friendly Ground Unit (used by `atak-bridge.sh` for pilot position) |

### What ATAK Shows

Each CoT event places an icon on the map with:
- **Position:** Lat/lon from GPS
- **Altitude:** MSL in meters
- **Track:** Heading and ground speed
- **Callsign:** The `--uid` value
- **Remarks:** Flight mode, armed state, speed, altitude

Icons go stale (dim) after 10 seconds without an update.

## TAK OSD Lua Script

The `tak-osd.lua` script provides a TAK-style heads-up display directly on the AX12 touchscreen through Flyshark — no ATAK needed:

- GPS coordinates (decimal degrees and MGRS grid)
- Compass rose with heading
- RSSI and link quality bars
- TX battery gauge
- Flight mode indicator
- Mission elapsed timer
- Channel stick position bars

Access: **RadioMaster App > System Menu > Lua Scripts > Tools > TAK OSD**

This script displays data from the ELRS telemetry sensors (CRSF mode) — it does not require MAVLink mode. It works alongside normal flying.

## MAVLink Bridge for QGC

For full ground control station functionality (missions, parameters, logs), use the MAVLink bridge instead of / in addition to the CoT bridge:

```bash
tac mavlink
```

This bridges MAVLink from the ELRS Backpack WiFi (UDP 14550) to a local TCP server (port 5760). Open QGC on the AX12 and connect to `localhost:5760`.

For the full MAVLink setup guide, see [mavlink-setup.md](mavlink-setup.md).

## Troubleshooting

### No icon on ATAK map

1. Is ATAK's UDP input configured? (Settings > Network Preferences > port 4242)
2. Is the bridge running? (`tac cot-test` should print "Sent CoT to...")
3. Zoom out — the test sends to Null Island (0,0) which is off the coast of Africa

### Icon appears but position is wrong

- `--test` mode always sends to Null Island — use live mode with a real MAVLink connection
- Check that the FC is sending `GLOBAL_POSITION_INT` (message 33) — some FC setups omit GPS data

### Bridge says "Serial open failed"

- The bridge falls back to synthetic data automatically — this is normal without a serial connection
- For live data, ensure ELRS is in MAVLink mode and the RX is powered

### Multiple bridges conflict

Only one process can read `/dev/ttyS1` at a time. If QGC and the CoT bridge both need serial, use the WiFi path for QGC (`tac mavlink`) and serial for CoT (`tac atak`).
```

- [ ] **Step 2: Commit docs/tak-setup.md**

```bash
cd ~/ax12-tac-tools
git add docs/tak-setup.md
git commit -m "Add dedicated TAK/ATAK integration guide

Covers architecture, ATAK install, network config, CoT bridge
usage, multi-device setup, multicast, CoT type codes, TAK OSD
Lua script, MAVLink bridge for QGC, and troubleshooting."
```

---

### Task 5: Test on AX12

**Depends on:** Tasks 1-4

This task runs on the AX12 device via SSH. Push the new files to GitHub, then run the installer on the AX12 to verify it works end-to-end.

- [ ] **Step 1: Push changes to GitHub**

From the laptop:

```bash
cd ~/ax12-tac-tools
git push origin main
```

- [ ] **Step 2: Run the installer on the AX12**

Via SSH to the AX12, simulate a fresh install by removing the old clone (if it exists from prior work) and running the curl-pipe one-liner:

```bash
ssh ax12 "cd ~ && mv ax12-tac-tools ax12-tac-tools.bak 2>/dev/null; pkg install -y curl && curl -sL https://raw.githubusercontent.com/rmeadomavic/ax12-tac-tools/main/install.sh | bash"
```

Expected: All phase 1 packages show `[SKIP]` (already installed), phase 2 clones the repo, copies Lua files, creates the alias. Self-test should show all `[OK]`.

- [ ] **Step 3: Verify the launcher TUI**

```bash
ssh ax12 "source ~/.bashrc && python3 ~/ax12-tac-tools/launcher.py --help"
```

Expected: Prints the shortcut list with all 12 commands.

- [ ] **Step 4: Verify direct shortcuts work**

```bash
ssh ax12 "source ~/.bashrc && python3 ~/ax12-tac-tools/launcher.py cot-test"
```

Expected: Sends a CoT test event, prints confirmation.

- [ ] **Step 5: Verify Lua scripts are installed**

```bash
ssh ax12 "su 0 ls /storage/emulated/0/AX12LUA/SCRIPTS/TOOLS/*.lua | wc -l"
```

Expected: 20+ files listed.

- [ ] **Step 6: Test idempotent re-run**

```bash
ssh ax12 "curl -sL https://raw.githubusercontent.com/rmeadomavic/ax12-tac-tools/main/install.sh | bash"
```

Expected: Everything shows `[SKIP]` or `[OK]` (update instead of fresh install). No errors.

- [ ] **Step 7: Restore backup if testing with a moved directory**

```bash
ssh ax12 "rm -rf ~/ax12-tac-tools.bak 2>/dev/null"
```
