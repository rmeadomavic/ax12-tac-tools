#!/data/data/com.termux/files/usr/bin/python3
"""AX12 Tactical Tools — TUI launcher and CLI dispatcher.

Touch-friendly curses interface for running tactical tools on the
RadioMaster AX12 (720x1280 touchscreen, Termux).

Usage:
    python3 launcher.py              # TUI menu
    python3 launcher.py <shortcut>   # Direct run
    python3 launcher.py --help       # List shortcuts
"""

import curses
import subprocess
import os
import sys
import time

PYTHON3 = "/data/data/com.termux/files/usr/bin/python3"
REPO_DIR = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.join(REPO_DIR, "tools")
LUA_SRC = os.path.join(REPO_DIR, "lua")
LUA_DEST = "/storage/emulated/0/AX12LUA/SCRIPTS/TOOLS"

# Tool registry: (label, description, cmd, timeout_sec, needs_root)
# timeout_sec=0 means no timeout (None passed to subprocess)
CATEGORIES = [
    ("TAK INTEGRATION", [
        ("ATAK CoT Bridge",  "Stream drone position to ATAK map",
         f"su 0 {PYTHON3} {TOOLS}/cot_bridge.py",        0,  True),
        ("MAVLink Bridge",   "Connect QGC/Mission Planner via ELRS",
         f"{PYTHON3} {TOOLS}/mavlink_bridge.py bridge",   0,  False),
        ("CoT Test Send",    "Send one test blip to verify ATAK",
         f"{PYTHON3} {TOOLS}/test_cot.py",                15, False),
    ]),
    ("FLIGHT OPS", [
        ("Airspace Brief",   "Pre-flight airspace restriction check",
         f"su 0 {PYTHON3} {TOOLS}/airspace_check.py brief", 30, True),
        ("Payload Drop Calc","Aerial drop point calculator",
         f"su 0 {PYTHON3} {TOOLS}/payload_drop.py calc",    30, True),
        ("Rover Navigation", "ArduRover GPS nav and geofencing",
         f"{PYTHON3} {TOOLS}/rover_nav.py --demo",          30, False),
        ("GPS Position",     "Current GPS fix from MT6631",
         f"su 0 {PYTHON3} {TOOLS}/gps_tool.py position",    15, True),
    ]),
    ("SENSORS", [
        ("IMU Tracker",      "ICM-42607 head tracking",
         f"su 0 {PYTHON3} {TOOLS}/imu_tracker.py",          0,  True),
        ("GPS Monitor",      "Continuous GPS with NMEA/satellite info",
         f"su 0 {PYTHON3} {TOOLS}/gps_position.py",         0,  True),
        ("Hydra AI Display", "Object detection telemetry client",
         f"{PYTHON3} {TOOLS}/hydra_display.py demo",         30, False),
    ]),
    ("SYSTEM", [
        ("Update Tools",     "git pull + re-copy Lua scripts",
         "__update__",  60, False),
        ("Reinstall Lua",    "Re-copy Lua scripts to Flyshark",
         "__lua__",     30, False),
        ("About",            "Version, repo URL, credits",
         "__about__",   0,  False),
    ]),
]

# Build flat list for index-based selection
ITEMS = []
for _cat_name, _tools in CATEGORIES:
    for _entry in _tools:
        ITEMS.append((_cat_name,) + _entry)
# Each item: (category, label, description, cmd, timeout_sec, needs_root)

# CLI shortcut table: shortcut -> label
SHORTCUTS = {
    "atak":      "ATAK CoT Bridge",
    "mavlink":   "MAVLink Bridge",
    "cot-test":  "CoT Test Send",
    "airspace":  "Airspace Brief",
    "drop":      "Payload Drop Calc",
    "rover":     "Rover Navigation",
    "gps":       "GPS Position",
    "imu":       "IMU Tracker",
    "gps-mon":   "GPS Monitor",
    "hydra":     "Hydra AI Display",
    "update":    "Update Tools",
    "lua":       "Reinstall Lua",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_battery():
    try:
        r = subprocess.run(
            ["su", "0", "cat", "/sys/class/power_supply/battery/capacity"],
            capture_output=True, text=True, timeout=2,
        )
        return r.stdout.strip() + "%" if r.returncode == 0 else "?"
    except Exception:
        return "?"


def get_uptime():
    try:
        with open("/proc/uptime") as f:
            secs = int(float(f.read().split()[0]))
        h, m = secs // 3600, (secs % 3600) // 60
        return f"{h}h{m:02d}m"
    except Exception:
        return "?"


def find_item_by_label(label):
    """Return the ITEMS entry whose label matches, or None."""
    for item in ITEMS:
        if item[1] == label:
            return item
    return None


def tool_counts():
    """Return (python_tool_count, lua_script_count)."""
    try:
        py_count = len([f for f in os.listdir(TOOLS) if f.endswith(".py")])
    except Exception:
        py_count = 0
    try:
        lua_count = len([f for f in os.listdir(LUA_SRC) if f.endswith(".lua")])
    except Exception:
        lua_count = 0
    return py_count, lua_count


# ---------------------------------------------------------------------------
# Special command handlers
# ---------------------------------------------------------------------------

def run_special_interactive(cmd, label):
    """Run a special __cmd__ outside curses, then wait for Enter."""
    print()
    if cmd == "__about__":
        _about()
    elif cmd == "__update__":
        _update()
    elif cmd == "__lua__":
        _install_lua()
    print()
    input("Press Enter to return to menu...")


def run_special_direct(cmd):
    """Run a special command in direct (non-TUI) mode."""
    if cmd == "__about__":
        _about()
    elif cmd == "__update__":
        _update()
    elif cmd == "__lua__":
        _install_lua()


def _about():
    print("=" * 50)
    print("  AX12 TACTICAL TOOLS")
    print("=" * 50)
    try:
        r = subprocess.run(
            ["git", "-C", REPO_DIR, "log", "--oneline", "-1"],
            capture_output=True, text=True, timeout=5,
        )
        print(f"  Version : {r.stdout.strip()}")
    except Exception as e:
        print(f"  Version : (git error: {e})")
    print(f"  Repo    : https://github.com/rmeadomavic/ax12-tac-tools")
    print(f"  Python  : {sys.version.split()[0]}")
    py_n, lua_n = tool_counts()
    print(f"  Tools   : {py_n} Python tools | {lua_n} Lua scripts")
    print("=" * 50)


def _update():
    print(">>> git pull --ff-only ...")
    r = subprocess.run(
        ["git", "-C", REPO_DIR, "pull", "--ff-only"],
        timeout=60,
    )
    if r.returncode == 0:
        print(">>> Repo updated. Re-installing Lua scripts...")
        _install_lua()
    else:
        print(">>> git pull failed (exit {})".format(r.returncode))


def _install_lua():
    print(f">>> Copying lua/*.lua -> {LUA_DEST} ...")
    try:
        lua_files = [f for f in os.listdir(LUA_SRC) if f.endswith(".lua")]
    except Exception as e:
        print(f">>> Error listing lua dir: {e}")
        return
    if not lua_files:
        print(">>> No .lua files found in lua/")
        return
    ok = 0
    fail = 0
    for fname in lua_files:
        src = os.path.join(LUA_SRC, fname)
        dst = os.path.join(LUA_DEST, fname)
        r = subprocess.run(["su", "0", "cp", src, dst], timeout=10)
        if r.returncode == 0:
            ok += 1
        else:
            print(f">>> Failed: {fname}")
            fail += 1
    print(f">>> Done: {ok} copied, {fail} failed.")


# ---------------------------------------------------------------------------
# TUI: tool output viewer
# ---------------------------------------------------------------------------

def tui_run_tool(stdscr, label, description, cmd, timeout_sec):
    """Run a tool and show its output in a scrollable curses view."""
    curses.curs_set(0)
    stdscr.clear()
    h, w = stdscr.getmaxyx()

    # Header bar
    stdscr.attron(curses.color_pair(2))
    header = f" RUNNING: {label} "
    stdscr.addstr(0, 0, header.ljust(w)[:w - 1])
    stdscr.attroff(curses.color_pair(2))

    # Subheader
    timeout_str = f"{timeout_sec}s" if timeout_sec else "no limit"
    stdscr.attron(curses.color_pair(3))
    stdscr.addstr(1, 0, f" {description} | Timeout: {timeout_str}"[:w - 1])
    stdscr.attroff(curses.color_pair(3))

    stdscr.attron(curses.color_pair(4))
    stdscr.addstr(3, 1, ">>> EXECUTING..."[:w - 2])
    stdscr.attroff(curses.color_pair(4))
    stdscr.refresh()

    # Handle special commands by exiting curses
    if cmd in ("__update__", "__lua__", "__about__"):
        curses.endwin()
        run_special_interactive(cmd, label)
        # Re-init curses state (wrapper handles the outer setup)
        stdscr.refresh()
        return

    # Run subprocess
    env = os.environ.copy()
    env["PATH"] = "/data/data/com.termux/files/usr/bin:" + env.get("PATH", "")
    env["HOME"] = os.path.expanduser("~")
    env["TERM"] = "dumb"

    timeout_arg = timeout_sec if timeout_sec else None
    start = time.time()
    try:
        proc = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            timeout=timeout_arg, env=env, cwd=REPO_DIR,
        )
        elapsed = round(time.time() - start, 1)
        output = proc.stdout
        if proc.stderr:
            output += ("\n--- stderr ---\n" + proc.stderr) if output else proc.stderr
        rc = proc.returncode
    except subprocess.TimeoutExpired:
        elapsed = round(time.time() - start, 1)
        output = f"TIMEOUT after {timeout_sec}s"
        rc = -1
    except Exception as e:
        elapsed = round(time.time() - start, 1)
        output = f"Error: {e}"
        rc = -2

    # Render results
    stdscr.clear()
    if rc == 0:
        stdscr.attron(curses.color_pair(5))
        status = f" COMPLETE ({elapsed}s) "
    elif rc == -1:
        stdscr.attron(curses.color_pair(6))
        status = f" TIMEOUT ({elapsed}s) "
    else:
        stdscr.attron(curses.color_pair(6))
        status = f" EXIT {rc} ({elapsed}s) "

    stdscr.addstr(0, 0, f" {label}: {status}"[:w - 1].ljust(w)[:w - 1])
    if rc == 0:
        stdscr.attroff(curses.color_pair(5))
    else:
        stdscr.attroff(curses.color_pair(6))

    lines = output.strip().split("\n") if output.strip() else ["(no output)"]
    scroll = 0
    view_h = h - 3  # header row + subheader row + footer row

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
                if rc == 0:
                    stdscr.attron(curses.color_pair(4))
                    stdscr.addstr(y, 1, line)
                    stdscr.attroff(curses.color_pair(4))
                else:
                    stdscr.attron(curses.color_pair(6))
                    stdscr.addstr(y, 1, line)
                    stdscr.attroff(curses.color_pair(6))

        stdscr.attron(curses.color_pair(3))
        footer = (
            f" [{scroll + 1}-{min(scroll + view_h, len(lines))}/{len(lines)}]"
            f"  UP/DOWN/PgUp/PgDn scroll  |  any other key to return "
        )
        if h > 1:
            stdscr.addstr(h - 1, 0, footer[:w - 1].ljust(w)[:w - 1])
        stdscr.attroff(curses.color_pair(3))
        stdscr.refresh()

    draw_output()

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


# ---------------------------------------------------------------------------
# TUI: main menu
# ---------------------------------------------------------------------------

def tui_main(stdscr):
    curses.curs_set(0)
    curses.start_color()
    curses.use_default_colors()

    # Color pairs (same IDs as reference launcher)
    curses.init_pair(1, curses.COLOR_CYAN, -1)   # category headers
    curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_CYAN)  # title bar
    curses.init_pair(3, curses.COLOR_WHITE,
                     235 if curses.COLORS >= 256 else curses.COLOR_BLACK)  # dim/footer
    curses.init_pair(4, curses.COLOR_CYAN, -1)   # output text
    curses.init_pair(5, curses.COLOR_GREEN, -1)  # success
    curses.init_pair(6, curses.COLOR_RED, -1)    # error
    curses.init_pair(7, curses.COLOR_YELLOW, -1) # selected item
    curses.init_pair(8, curses.COLOR_WHITE, -1)  # normal items

    try:
        curses.mousemask(curses.ALL_MOUSE_EVENTS | curses.REPORT_MOUSE_POSITION)
    except Exception:
        pass

    selected = 0
    batt = get_battery()
    uptime_str = get_uptime()

    while True:
        stdscr.clear()
        h, w = stdscr.getmaxyx()

        # Title bar
        stdscr.attron(curses.color_pair(2))
        title = " AX12 TACTICAL TOOLS "
        status_bar = f" BATT {batt} | UP {uptime_str} "
        pad = max(0, w - len(title) - len(status_bar))
        header_line = title + " " * pad + status_bar
        stdscr.addstr(0, 0, header_line[:w - 1].ljust(w)[:w - 1])
        stdscr.attroff(curses.color_pair(2))

        # Build item positions for mouse hit-testing
        item_rows = {}   # row_y -> item_index
        y = 2
        item_idx = 0
        last_cat = ""

        for cat_name, label, desc, cmd, timeout_sec, needs_root in ITEMS:
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
            if item_idx == selected:
                prefix = " >> "
                display = f"{prefix}{label}  —  {desc}"
                stdscr.attron(curses.color_pair(7) | curses.A_BOLD)
                stdscr.addstr(y, 0, display[:w - 1].ljust(w - 1))
                stdscr.attroff(curses.color_pair(7) | curses.A_BOLD)
            else:
                prefix = "    "
                display = f"{prefix}{label}"
                stdscr.attron(curses.color_pair(8))
                stdscr.addstr(y, 0, display[:w - 1])
                stdscr.attroff(curses.color_pair(8))

            item_rows[y] = item_idx
            y += 1
            item_idx += 1

        # Footer
        stdscr.attron(curses.color_pair(3))
        footer = " [UP/DOWN] Select  [ENTER] Run  [Q] Quit "
        if h > 1:
            stdscr.addstr(h - 1, 0, footer[:w - 1].ljust(w)[:w - 1])
        stdscr.attroff(curses.color_pair(3))

        stdscr.refresh()

        # Input handling
        key = stdscr.getch()

        if key in (curses.KEY_UP, ord('k')):
            selected = max(0, selected - 1)
        elif key in (curses.KEY_DOWN, ord('j')):
            selected = min(len(ITEMS) - 1, selected + 1)
        elif key == curses.KEY_HOME:
            selected = 0
        elif key == curses.KEY_END:
            selected = len(ITEMS) - 1
        elif key in (10, curses.KEY_ENTER):
            _, label, desc, cmd, timeout_sec, _ = ITEMS[selected]
            tui_run_tool(stdscr, label, desc, cmd, timeout_sec)
            batt = get_battery()
            uptime_str = get_uptime()
        elif key in (ord('q'), ord('Q'), 27):
            break
        elif ord('1') <= key <= ord('9'):
            idx = key - ord('1')
            if idx < len(ITEMS):
                selected = idx
                _, label, desc, cmd, timeout_sec, _ = ITEMS[selected]
                tui_run_tool(stdscr, label, desc, cmd, timeout_sec)
                batt = get_battery()
                uptime_str = get_uptime()
        elif key == curses.KEY_MOUSE:
            try:
                _, mx, my, _, bstate = curses.getmouse()
                if my in item_rows:
                    clicked_idx = item_rows[my]
                    selected = clicked_idx
                    if bstate & (curses.BUTTON1_CLICKED | curses.BUTTON1_RELEASED):
                        _, label, desc, cmd, timeout_sec, _ = ITEMS[clicked_idx]
                        tui_run_tool(stdscr, label, desc, cmd, timeout_sec)
                        batt = get_battery()
                        uptime_str = get_uptime()
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Direct mode (CLI shortcut)
# ---------------------------------------------------------------------------

def print_help():
    print("AX12 Tactical Tools — CLI shortcuts\n")
    print("Usage: launcher.py <shortcut>\n")
    print(f"  {'Shortcut':<12}  Tool")
    print(f"  {'-'*12}  {'-'*30}")
    for shortcut, label in SHORTCUTS.items():
        print(f"  {shortcut:<12}  {label}")
    print()


def run_direct(shortcut):
    """Dispatch a shortcut directly without TUI."""
    label = SHORTCUTS.get(shortcut)
    if label is None:
        print(f"Unknown shortcut: '{shortcut}'\n")
        print_help()
        sys.exit(1)

    item = find_item_by_label(label)
    if item is None:
        print(f"Internal error: label '{label}' not found in ITEMS")
        sys.exit(1)

    _, label, description, cmd, timeout_sec, needs_root = item
    print(f"[ {label} ]  {description}")

    if cmd in ("__update__", "__lua__", "__about__"):
        run_special_direct(cmd)
        return

    print(f"CMD: {cmd}")
    print()

    env = os.environ.copy()
    env["PATH"] = "/data/data/com.termux/files/usr/bin:" + env.get("PATH", "")
    env["HOME"] = os.path.expanduser("~")

    # exec replaces the process — clean hand-off
    os.execlpe("/data/data/com.termux/files/usr/bin/sh",
               "sh", "-c", cmd, env)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg in ("--help", "help", "-h"):
            print_help()
            sys.exit(0)
        run_direct(arg)
    else:
        os.environ.setdefault("TERM", "xterm-256color")
        curses.wrapper(tui_main)
