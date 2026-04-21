#!/data/data/com.termux/files/usr/bin/python3
"""AX12 Tactical Tools — Web Launcher

Touch-friendly web UI for the RadioMaster AX12. Serves on localhost:8080.
Bookmark to home screen for app-like access.

Usage:
    python3 web_launcher.py              # start server
    python3 web_launcher.py --port 9090  # custom port
"""

# ── Imports ──────────────────────────────────────────────────────────────────

import base64
import html as html_mod
import http.server
import json
import os
import re
import shlex
import signal
import socket
import socketserver
import subprocess
import sys
import threading
import time


# ══════════════════════════════════════════════════════════════════════════════
# 1. CONSTANTS AND CONFIG
# ══════════════════════════════════════════════════════════════════════════════

PORT = 8080
MAX_OUTPUT_LINES = 10000

# 192x192 tactical crosshair icon (base64 PNG)
ICON_B64 = "iVBORw0KGgoAAAANSUhEUgAAAMAAAADACAIAAADdvvtQAAAHQUlEQVR4nO3da24bRxAEYN+g76Gj6Kg5ZQRPQAgKNUtuv6p6qsKf1kw/Pq5Fw47+mKI48qe7AIU7AqS4IkCKKwJ0kc9/PrtLgI4A7fKlZ726C8GNAO0iQJcRoF0E6DICtIsAXUaAdhGgy1wA+vj8yHvVdOgJEaCuTV0DCm2TLESA8iJA9yNAJkCeCJAJkCcCZAK0ycOH/9XdSmIE6L8EcjmK1OmAit3Mk3QioHY0kzAdBCh8nTd+5TxJRwBKWpv/Cwcwmgwoe0mxh5BKmgmoZiVJp3ExmgaocgfZx1IwmgOofu41h4MzmgCoa9DFt2AyogfUONyWu9AMEQNqn2njjTiMWAEhzLH9XgRDfIBw3oUIV7cPgQwQyNR+FNNeQOM0mAC1D+u3ekDKaKmHAxDCW21TVXchnfMhAISpx5AAWd+U0AFh0llBLqmsNmhAyHoMEpCVDw0XELgeQwVktaMDBQROZ4WlvNQiEQFR6DF4QFYySThALHqMAZDlzxMLEJEeIwFkyVN1AYoNlx7jAWR9s60DRKfHqABZ04SLADHqMTZA1jHnCkCkeowQkJVPOx0Qrx7jBGS1MxegXdjLpgdErcdoAVnh5BMBsesxZkBWNf8sQAP0GDkgK9mCAO0ypn4yQDP0GD8gy99FPKAxemwEIEveSC6g8MOLM68RdECTHj/2t52Pr/9GNJK0l0hAvHoG/7yYR5K2czSgmp9nAxJ0QER6At1wScrYUQqgqDPDk0qHghEoIPzHz72V7ztiZBS+qXhAIQcGxrPg15siYgQHCPbx41/qu01RMIrdVzAg/2lRCVnkvb64DDmP8gLCfPxE7c/TF7KhwK1FAnIeFZLYtflbg2UkQE8Svq2Q1jANQQCC+v0rY0mBraEZitpdGCDPOf4krSe2O2RDtw+5Dwjn8ZO3mPDuoAyFbDAG0O1D/EldSUaDsIbunTANUOzhSQ0KEMrvX9mbyGsQxJB/jwGA7p3gT8EOUnsENHTjy1kB1Uw/u0cEQwIkQK40ADpEj5X8qwx2Q/SAWgqITXs7ZwFCeMvGpr2jUkDtH+CH6VnBAfTuTl2A3v1af9rfrElp7+tEQPW3p0aA0tP+Nk1Nb3fHASq+uiYClBsByksRIOnJDp0hAcKKAGVFgLIzGdDsz1/f09jpKYAq722JAMVHgAoiQEMiQPERoIIIUErO+bwpQMHp+osrAhSf+pn+0FPZMjegp4Nrf32f6Y0vd04z/JzUZgtevwJqr+xyoDWAao7K67fg9RwQhSFPt87FR52T2mzB63uD+h7oeaIA3Qj390AZd/ijT2EFEaCUFHdqApQR/Ul0QQRoSAQoPgJUEAEaEgGKz48/W6u8ujiNnU4GZMc8hHo/bwoQfQQoKwKUnQpAt68JyXhDdHpMgKAiQLmZ/Vmst7sjANnoh1BvaycCmmSova8eQO2G6m9PCo6edECmh1B02jvyLJQPkHW/X8PT3s7RgFKHXtBm++PH6gE5rwxJzdyze2TXYwK0jwBdhhWQ6eeFBaUf0GBDeQ0C6ikFZBgPIdPPTPXFv8RpgGL3kdFgasHvBgXQVEPh3cHqaQBkMA8hS1tMbHdQeixofWGARhoKbA1ZTxsgQ3oI2bMlOfcU0lp4VSGJWtwoQBa9LX9rmHoMExCIIYtbm6cvWDoWujUvIMN7CK083d+7K7zXV8jVqQlcWTAgCkOv7/Ldpvw3FiR2XwGADPUhtOJZ6utNUdBZiV1WPCBAQ7Zd8GbN+47undmb8E3FADLsh9AjlyuPenU3+mvC15QCCNmQJTPqbm6XjB2FATIqQyuHuFlJ2s7RgB4Z7OYRAkDGbOhpvlr4UjKjkaS9BAMyku+mX8y8RsJ7yQXEPvphXXAAskGGJrWQ1EgKIJtiaEz9eV0I0C5j6ucDZCMMzSg+tYVEQMZvaEDl2fXnAjJyQ+xlFxQvQLuwlz0BkDEboq65pvIKQEZriLfgsrKLABmnIdJqK2uuA2SEhhhLLS74AlD431jgMkRXZ0a1ewPVgIzKEFeRSaXCATIeQ0QV5tWJCMhIDLGUl1okKCD7X/+Ae8IvrKBCXEAGbwi8qpryoAEZtiHkkspqQwdkz4YCsjPMYoqnRADIUA0BVlI/Hw5AK2iG0MpoqYcJkIE9inAKaJwGGSD7ZWotW0S4un0IfIBWEMbXfi/CY5gVkAG8CxtvBNFj1IBWGmfachcOnRV6QPb7cLPnW3wLoB6bAWhlM+ikWdccDktnZQ6glcq5Zx8LTmdlGqCV/Q6i1pB0GgudlZmAVi5X4txK7CF0dFYmA3rklSXd2JP/C3ndPHIEoJUX1/b6/m78ykl0Vg4C9Mi76yx7dQ/mTk4E9D1C48zpgB6Rm3sRoF8jLq9EgO7nBB+XEaD7ESATIE8EyATIEwEyP6C8V2ibKSEC1LWp0v8/EF2IAHVFgHYRoMsI0C4CdBkB2kWALiNAuwjQZQToItKzjwAprgiQ4ooAKa78C4joLbtVThscAAAAAElFTkSuQmCC"
ICON_PNG = base64.b64decode(ICON_B64)
REPO_DIR = os.path.dirname(os.path.abspath(__file__))
PYTHON3 = "/data/data/com.termux/files/usr/bin/python3"
LUA_SRC = os.path.join(REPO_DIR, "lua")
LUA_DEST = "/storage/emulated/0/AX12LUA/SCRIPTS/TOOLS"

# User config overrides the default
USER_CONFIG = os.path.expanduser("~/.config/ax12-tac-tools/tools.json")
DEFAULT_CONFIG = os.path.join(REPO_DIR, "tools.json")


# ══════════════════════════════════════════════════════════════════════════════
# 2. PROCESS MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════

_proc_lock = threading.Lock()
_current_proc = None     # subprocess.Popen
_current_label = None
_output_lines = []       # buffered output
_proc_done = False
_proc_exit_code = None


def _read_output(proc):
    """Background thread: read subprocess stdout+stderr into _output_lines."""
    global _proc_done, _proc_exit_code
    try:
        for line in proc.stdout:
            with _proc_lock:
                _output_lines.append(("out", line))
        proc.wait()
    except Exception:
        pass
    with _proc_lock:
        _proc_done = True
        _proc_exit_code = proc.returncode


def _split_cmd(cmd):
    """Split a cmd string into argv, expanding ~ on each token.

    Avoids shell=True so nothing from tools.json gets re-parsed by a shell.
    """
    argv = shlex.split(cmd)
    return [os.path.expanduser(a) for a in argv]


def start_tool(cmd, label, timeout=None):
    """Start a tool subprocess. Returns (ok, error_msg)."""
    global _current_proc, _current_label, _output_lines, _proc_done, _proc_exit_code

    try:
        argv = _split_cmd(cmd)
    except ValueError as e:
        return False, f"Invalid command: {e}"
    if not argv:
        return False, "Empty command"

    with _proc_lock:
        if _current_proc and _current_proc.poll() is None:
            return False, f"{_current_label} is still running. Stop it first."
        _output_lines = []
        _proc_done = False
        _proc_exit_code = None
        _current_label = label

        env = os.environ.copy()
        env["PATH"] = "/data/data/com.termux/files/usr/bin:" + env.get("PATH", "")
        env["HOME"] = os.path.expanduser("~")
        env["TERM"] = "dumb"

        try:
            proc = subprocess.Popen(
                argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1, env=env, cwd=REPO_DIR,
                preexec_fn=os.setsid,
            )
        except Exception as e:
            return False, str(e)

        _current_proc = proc

    t = threading.Thread(target=_read_output, args=(proc,), daemon=True)
    t.start()

    # Auto-kill after timeout (non-long-running tools).
    # Bug fix: capture proc as default arg so the closure times the right process.
    if timeout and timeout > 0:
        def _auto_kill(target_proc=proc):
            time.sleep(timeout)
            with _proc_lock:
                if target_proc.poll() is None:
                    _output_lines.append(("out", f"\n[TIMEOUT] Killed after {timeout}s\n"))
                    try:
                        os.killpg(os.getpgid(target_proc.pid), signal.SIGKILL)
                    except Exception:
                        pass
        threading.Thread(target=_auto_kill, daemon=True).start()

    return True, None


def stop_tool(force=False):
    """Stop the running tool. Returns (ok, message)."""
    global _current_proc
    with _proc_lock:
        proc = _current_proc
    if not proc or proc.poll() is not None:
        return True, "Nothing running."
    try:
        pgid = os.getpgid(proc.pid)
        sig = signal.SIGKILL if force else signal.SIGTERM
        try:
            os.killpg(pgid, sig)
        except PermissionError:
            # Process runs as root (su 0) — use su to kill it
            sig_num = 9 if force else 15
            subprocess.run(["su", "0", "kill", f"-{sig_num}", f"-{pgid}"],
                           timeout=5, capture_output=True)
        return True, "Force killed." if force else "Stop signal sent."
    except Exception as e:
        return False, str(e)


def get_output_since(index):
    """Get output lines since index. Returns (lines, new_index, done, exit_code).

    Bug fix: trims _output_lines when it exceeds MAX_OUTPUT_LINES to prevent
    unbounded memory growth from long-running tools.
    """
    with _proc_lock:
        # Trim old entries if buffer is too large
        if len(_output_lines) > MAX_OUTPUT_LINES:
            excess = len(_output_lines) - MAX_OUTPUT_LINES
            del _output_lines[:excess]
            # Adjust caller's index so they don't re-read or skip
            index = max(0, index - excess)
        new_lines = _output_lines[index:]
        return new_lines, len(_output_lines), _proc_done, _proc_exit_code


# ══════════════════════════════════════════════════════════════════════════════
# 3. CONFIG LOADING / SAVING
# ══════════════════════════════════════════════════════════════════════════════

def load_config():
    """Load tools config. User config takes priority over default."""
    path = USER_CONFIG if os.path.exists(USER_CONFIG) else DEFAULT_CONFIG
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return {"categories": []}


def save_config(data):
    """Save tools config to user location."""
    os.makedirs(os.path.dirname(USER_CONFIG), exist_ok=True)
    with open(USER_CONFIG, "w") as f:
        json.dump(data, f, indent=2)


# ── TAK server upstream ──────────────────────────────────────────────────────
#
# Optional top-level "tak_server" block in tools.json makes cot_bridge.py fan
# out to a TAK server in addition to the local UDP listener. The settings UI
# edits it; the ATAK BRIDGE launch path appends the matching CLI flags.

def _tak_server_cfg():
    """Return the tak_server block from the active config, or None."""
    cfg = load_config().get("tak_server")
    if not cfg or not cfg.get("enabled") or not cfg.get("host") or not cfg.get("port"):
        return None
    return cfg


def apply_tak_server_flags(cmd):
    """If the cmd invokes cot_bridge.py, append TAK server flags from config."""
    if "cot_bridge.py" not in cmd:
        return cmd
    cfg = _tak_server_cfg()
    if not cfg:
        return cmd
    extra = ["--tak-server", f"{cfg['host']}:{cfg['port']}"]
    if cfg.get("tls"):
        extra.append("--tak-tls")
        for flag, key in (("--tak-cert", "cert"), ("--tak-key", "key"), ("--tak-ca", "ca")):
            val = cfg.get(key)
            if val:
                extra.extend([flag, val])
    return cmd + " " + " ".join(shlex.quote(x) for x in extra)


def test_tak_server(cfg):
    """Open a short-lived connection to the TAK server and send one CoT blip.

    Returns (ok, message). Used by /api/tak/test to verify reachability from
    the settings UI before launching the live bridge.
    """
    host = cfg.get("host")
    port = cfg.get("port")
    if not host or not port:
        return False, "Host and port are required"
    try:
        port = int(port)
    except (TypeError, ValueError):
        return False, f"Invalid port: {port!r}"

    now = time.time()
    t = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now))
    stale = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now + 30))
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<event version="2.0" uid="AX12-TAK-TEST" type="a-f-A-M-F-Q" '
        f'time="{t}" start="{t}" stale="{stale}" how="m-g">'
        f'<point lat="0.0000000" lon="0.0000000" hae="100.0" ce="10.0" le="10.0"/>'
        f'<detail>'
        f'<contact callsign="AX12-TAK-TEST"/>'
        f'<remarks>AX12 launcher connectivity test</remarks>'
        f'</detail>'
        f'</event>\n'
    ).encode("utf-8")

    try:
        raw = socket.create_connection((host, port), timeout=5.0)
    except OSError as e:
        return False, f"Connect failed: {e}"

    try:
        if cfg.get("tls"):
            cert = cfg.get("cert")
            key = cfg.get("key")
            if not cert or not key:
                raw.close()
                return False, "TLS requires cert and key paths"
            import ssl
            ca = cfg.get("ca") or None
            try:
                ctx = ssl.create_default_context(cafile=ca)
                ctx.load_cert_chain(certfile=cert, keyfile=key)
                sock = ctx.wrap_socket(raw, server_hostname=host)
            except (OSError, ssl.SSLError, FileNotFoundError) as e:
                raw.close()
                return False, f"TLS handshake failed: {e}"
        else:
            sock = raw

        try:
            sock.sendall(xml)
        except OSError as e:
            return False, f"Send failed: {e}"
        finally:
            try:
                sock.close()
            except OSError:
                pass
        return True, f"Sent test CoT to {host}:{port}"
    except Exception as e:
        try:
            raw.close()
        except OSError:
            pass
        return False, str(e)


# ══════════════════════════════════════════════════════════════════════════════
# 4. PRE-FLIGHT CHECKS
# ══════════════════════════════════════════════════════════════════════════════

def check_requirements(requires):
    """Check a list of requirements. Returns (ok, [failure_messages])."""
    if not requires:
        return True, []
    failures = []
    for req in requires:
        if req == "root":
            try:
                r = subprocess.run(["su", "0", "id"], capture_output=True,
                                   text=True, timeout=3)
                if "uid=0" not in r.stdout:
                    failures.append("Root access (su 0) not available")
            except Exception:
                failures.append("Root access (su 0) not available")

        elif req.startswith("serial:"):
            dev = req.split(":", 1)[1]
            if not os.path.exists(dev):
                failures.append(f"Serial port {dev} not found")
            else:
                # Check if it's busy
                try:
                    r = subprocess.run(
                        ["su", "0", "sh", "-c", f"ls -la /proc/*/fd/* 2>/dev/null | grep {dev}"],
                        capture_output=True, text=True, timeout=3)
                    if r.stdout.strip():
                        failures.append(f"{dev} may be in use by another process")
                except Exception:
                    pass  # non-fatal

        elif req == "gps":
            try:
                r = subprocess.run(
                    ["su", "0", "dumpsys", "location"],
                    capture_output=True, text=True, timeout=5)
                if "Location[" not in r.stdout:
                    failures.append("No GPS fix available")
            except Exception:
                failures.append("Could not check GPS status")

        elif req == "network":
            try:
                r = subprocess.run(
                    ["ip", "addr", "show", "wlan0"],
                    capture_output=True, text=True, timeout=3)
                if "inet " not in r.stdout:
                    failures.append("WiFi (wlan0) not connected")
            except Exception:
                failures.append("Could not check network status")

    return len(failures) == 0, failures


# ── Special commands ─────────────────────────────────────────────────────────

def run_special(cmd):
    """Run a special __command__ and return output string."""
    if cmd == "__update__":
        lines = []
        r = subprocess.run(["git", "-C", REPO_DIR, "pull", "--ff-only"],
                           capture_output=True, text=True, timeout=60)
        lines.append(r.stdout)
        if r.stderr:
            lines.append(r.stderr)
        if r.returncode == 0:
            lines.append("\nRe-installing Lua scripts...")
            lines.append(_copy_lua())
        else:
            lines.append(f"\ngit pull failed (exit {r.returncode})")
        return "\n".join(lines)

    elif cmd == "__lua__":
        return _copy_lua()

    return "Unknown special command"


def _copy_lua():
    """Copy lua scripts and return status string."""
    lines = []
    try:
        lua_files = [f for f in os.listdir(LUA_SRC) if f.endswith(".lua")]
    except Exception as e:
        return f"Error listing lua dir: {e}"
    ok = 0
    for fname in lua_files:
        src = os.path.join(LUA_SRC, fname)
        r = subprocess.run(["su", "0", "cp", src, LUA_DEST + "/"],
                           capture_output=True, timeout=10)
        if r.returncode == 0:
            ok += 1
        else:
            lines.append(f"FAIL: {fname}")
    lines.append(f"\n{ok}/{len(lua_files)} Lua scripts installed")
    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# 5. SETUP WIZARD CHECKS
# ══════════════════════════════════════════════════════════════════════════════

def check_atak_installed():
    try:
        r = subprocess.run(["pm", "list", "packages"], capture_output=True,
                           text=True, timeout=5)
        for line in r.stdout.splitlines():
            pkg = line.replace("package:", "").strip()
            if "atak" in pkg.lower():
                return True, pkg
    except Exception:
        pass
    return False, None


ATAK_PREFS_PATH = "/storage/emulated/0/atak/config/prefs/cot_streams.xml"


def _read_atak_prefs():
    """Return the cot_streams.xml content as a string, or None if missing."""
    try:
        r = subprocess.run(["su", "0", "cat", ATAK_PREFS_PATH],
                           capture_output=True, text=True, timeout=3)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout
    except Exception:
        pass
    return None


def check_atak_udp_configured():
    """True iff an enabled connectString targets UDP port 4242."""
    import xml.etree.ElementTree as ET
    xml_str = _read_atak_prefs()
    if not xml_str:
        return False
    try:
        root = ET.fromstring(xml_str)
    except ET.ParseError:
        return False
    for pref in root.findall("preference"):
        if pref.get("name") != "cot_streams":
            continue
        for entry in pref.findall("entry"):
            key = entry.get("key", "")
            if key.startswith("connectString") and entry.text and "4242" in entry.text:
                return True
    return False


def inject_atak_udp_config():
    """Add a UDP 4242 stream to ATAK prefs, preserving existing streams."""
    import xml.etree.ElementTree as ET

    atak_dir = "/storage/emulated/0/atak"
    try:
        r = subprocess.run(["su", "0", "ls", atak_dir], capture_output=True,
                           text=True, timeout=3)
        if r.returncode != 0:
            return False, "ATAK config directory not found. Launch ATAK once first, then re-run setup."
    except Exception as e:
        return False, str(e)

    existing = _read_atak_prefs()
    if existing:
        try:
            root = ET.fromstring(existing)
        except ET.ParseError:
            root = ET.Element("preferences")
    else:
        root = ET.Element("preferences")

    pref = None
    for p in root.findall("preference"):
        if p.get("name") == "cot_streams":
            pref = p
            break
    if pref is None:
        pref = ET.SubElement(root, "preference", {"version": "1", "name": "cot_streams"})

    # Find current count and bail early if our entry already exists.
    count = 0
    for entry in pref.findall("entry"):
        if entry.get("key") == "count":
            try:
                count = int((entry.text or "0").strip())
            except ValueError:
                count = 0
        if (entry.get("key", "").startswith("connectString")
                and entry.text and "4242" in entry.text):
            return True, "UDP 4242 already configured."

    idx = count
    new_entries = [
        (f"description{idx}", "class java.lang.String", "AX12 CoT Bridge"),
        (f"enabled{idx}",     "class java.lang.Boolean", "true"),
        (f"connectString{idx}", "class java.lang.String", "udp+cotsocket://0.0.0.0:4242"),
    ]
    for key, cls, val in new_entries:
        e = ET.SubElement(pref, "entry", {"key": key, "class": cls})
        e.text = val

    # Update or create the count entry.
    count_entry = None
    for entry in pref.findall("entry"):
        if entry.get("key") == "count":
            count_entry = entry
            break
    if count_entry is None:
        count_entry = ET.SubElement(
            pref, "entry",
            {"key": "count", "class": "class java.lang.Integer"})
    count_entry.text = str(idx + 1)

    body = ('<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>\n'
            + ET.tostring(root, encoding="unicode"))

    pref_dir = f"{atak_dir}/config/prefs"
    try:
        subprocess.run(["su", "0", "mkdir", "-p", pref_dir],
                       capture_output=True, timeout=5)
        proc = subprocess.run(
            ["su", "0", "tee", ATAK_PREFS_PATH],
            input=body, capture_output=True, text=True, timeout=5)
        if proc.returncode == 0:
            return True, "UDP input configured (port 4242). Restart ATAK to apply."
        return False, f"Write failed: {proc.stderr}"
    except Exception as e:
        return False, str(e)


def run_setup_check():
    checks = {}
    try:
        r = subprocess.run(["su", "0", "id"], capture_output=True, text=True, timeout=3)
        checks["root"] = {"ok": "uid=0" in r.stdout, "detail": "su 0 available"}
    except Exception:
        checks["root"] = {"ok": False, "detail": "su 0 failed"}

    installed, pkg = check_atak_installed()
    checks["atak_installed"] = {"ok": installed, "detail": pkg if installed else "Not installed"}

    # Bug fix: call check_atak_udp_configured once, store the result
    if installed:
        udp_ok = check_atak_udp_configured()
        checks["atak_udp"] = {"ok": udp_ok, "detail": "UDP 4242" if udp_ok else "Not configured"}
    else:
        checks["atak_udp"] = {"ok": False, "detail": "ATAK not installed"}

    checks["serial"] = {"ok": os.path.exists("/dev/ttyS1"), "detail": "/dev/ttyS1"}
    return checks


# ══════════════════════════════════════════════════════════════════════════════
# 6. ANSI TO HTML CONVERSION
# ══════════════════════════════════════════════════════════════════════════════

ANSI_COLORS = {
    "30": "#333", "31": "#ef4444", "32": "#00d4aa", "33": "#f59e0b",
    "34": "#3b82f6", "35": "#a855f7", "36": "#00d4aa", "37": "#ccc",
    "90": "#555", "91": "#ef5350", "92": "#34d399", "93": "#fbbf24",
    "94": "#60a5fa", "95": "#c084fc", "96": "#5eead4", "97": "#eee",
}


def ansi_to_html(text):
    """Convert ANSI escape codes to HTML spans."""
    escaped = html_mod.escape(text)
    pattern = re.compile(r'\x1b\[([0-9;]*)m')
    result = []
    open_spans = 0
    last = 0
    for m in pattern.finditer(escaped):
        result.append(escaped[last:m.start()])
        codes = m.group(1).split(";") if m.group(1) else ["0"]
        last = m.end()
        for code in codes:
            if code in ("0", ""):
                result.append("</span>" * open_spans)
                open_spans = 0
            elif code == "1":
                result.append('<span style="font-weight:bold">')
                open_spans += 1
            elif code in ANSI_COLORS:
                result.append(f'<span style="color:{ANSI_COLORS[code]}">')
                open_spans += 1
    result.append(escaped[last:])
    result.append("</span>" * open_spans)
    return "".join(result)


# ══════════════════════════════════════════════════════════════════════════════
# 7. DEVICE STATUS
# ══════════════════════════════════════════════════════════════════════════════

def get_status():
    """Battery % and uptime."""
    try:
        r = subprocess.run(["su", "0", "cat", "/sys/class/power_supply/battery/capacity"],
                           capture_output=True, text=True, timeout=2)
        batt = r.stdout.strip() + "%" if r.returncode == 0 else "?"
    except Exception:
        batt = "?"
    try:
        with open("/proc/uptime") as f:
            secs = int(float(f.read().split()[0]))
        h, m = secs // 3600, (secs % 3600) // 60
        uptime = f"{h}h{m:02d}m"
    except Exception:
        uptime = "?"
    return batt, uptime


def get_full_status():
    """Full device status for the /api/status endpoint."""
    batt, uptime = get_status()

    # GPS: check if /dev/stpgps exists or dumpsys shows a fix
    gps_ok = False
    if os.path.exists("/dev/stpgps"):
        gps_ok = True
    else:
        try:
            r = subprocess.run(
                ["su", "0", "dumpsys", "location"],
                capture_output=True, text=True, timeout=3)
            if "Location[" in r.stdout:
                gps_ok = True
        except Exception:
            pass

    # Serial ports
    serial_ttyS0 = os.path.exists("/dev/ttyS0")
    serial_ttyS1 = os.path.exists("/dev/ttyS1")

    return {
        "battery": batt,
        "uptime": uptime,
        "gps": gps_ok,
        "serial_ttyS0": serial_ttyS0,
        "serial_ttyS1": serial_ttyS1,
    }


# ══════════════════════════════════════════════════════════════════════════════
# 8. HTML TEMPLATES
# ══════════════════════════════════════════════════════════════════════════════

def build_page():
    config = load_config()
    batt, uptime = get_status()
    buttons_html = ""
    for cat in config.get("categories", []):
        buttons_html += f'<div class="cat">\n'
        buttons_html += f'<div class="cat-hdr">{html_mod.escape(cat["name"])}</div>\n'
        buttons_html += '<div class="grid">\n'
        for tool in cat.get("tools", []):
            label = html_mod.escape(tool["label"])
            desc = html_mod.escape(tool.get("description", ""))
            shortcut = html_mod.escape(tool.get("shortcut", ""))
            buttons_html += (
                f'<button class="btn" onclick="runTool(\'{shortcut}\')">'
                f'<span class="btn-label">{label}</span>'
                f'<span class="btn-desc">{desc}</span>'
                f'</button>\n'
            )
        buttons_html += '</div></div>\n'

    return PAGE_HTML.replace("{{BUTTONS}}", buttons_html) \
                    .replace("{{BATT}}", batt) \
                    .replace("{{UPTIME}}", uptime)


PAGE_HTML = r"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,user-scalable=no">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="theme-color" content="#08090a">
<title>AX12 TAC</title>
<link rel="icon" href="/icon.png" type="image/png">
<link rel="apple-touch-icon" href="/icon.png">
<link rel="manifest" href="/manifest.json">
<style>
/* ── Reset ─────────────────────────────────────────────────────── */
*{margin:0;padding:0;box-sizing:border-box;-webkit-tap-highlight-color:transparent}
html,body{
  width:100%;height:100%;
  background:#08090a;color:#e4e4e7;
  font-family:-apple-system,'Inter','Segoe UI',system-ui,sans-serif;
  font-size:14px;overflow-x:hidden;
  -webkit-font-smoothing:antialiased;
}

/* ── Header ────────────────────────────────────────────────────── */
.hdr{
  background:linear-gradient(180deg,#0f1114 0%,#0c0d10 100%);
  padding:14px 16px;
  border-bottom:1px solid #1a1d23;
  box-shadow:0 1px 0 rgba(0,212,170,0.05);
  position:sticky;top:0;z-index:10;
}
.hdr-row{display:flex;justify-content:space-between;align-items:center}
.logo{font-size:13px;font-weight:600;letter-spacing:5px;display:flex;align-items:center;gap:1px}
.logo-ax12{color:#00d4aa}
.logo-sep{color:#3f3f46;margin:0 2px}
.logo-tac{color:#3f3f46}
.logo-tools{color:#e4e4e7}
.hdr-right{display:flex;align-items:center;gap:14px}
.status-indicators{display:flex;align-items:center;gap:10px}
.status-dot{display:flex;align-items:center;gap:4px;font-size:9px;font-weight:600;letter-spacing:1px;color:#71717a;text-transform:uppercase}
.status-dot .dot{
  width:6px;height:6px;border-radius:50%;
  background:#3f3f46;
  flex-shrink:0;
}
.status-dot .dot.green{background:#00d4aa;box-shadow:0 0 4px rgba(0,212,170,0.4)}
.status-dot .dot.amber{background:#f59e0b;box-shadow:0 0 4px rgba(245,158,11,0.4)}
.status-dot .dot.red{background:#ef4444;box-shadow:0 0 4px rgba(239,68,68,0.4)}
.status-dot .dot.pulse{animation:pulse 2s ease-in-out infinite}
@keyframes pulse{0%,100%{opacity:0.6}50%{opacity:1}}
.stat-batt{font-size:10px;color:#71717a;font-weight:600;letter-spacing:1px;font-variant-numeric:tabular-nums}
.hdr-nav{display:flex;align-items:center;gap:6px}
.hdr-link{
  font-size:10px;color:#71717a;letter-spacing:1px;font-weight:600;
  cursor:pointer;padding:6px 8px;border-radius:4px;
  border:1px solid transparent;
  transition:color 0.1s,border-color 0.1s;
}
.hdr-link:active{color:#e4e4e7;border-color:#1a1d23}

/* ── Main content ──────────────────────────────────────────────── */
.wrap{padding:14px 14px 80px;max-width:480px;margin:0 auto}

/* ── Categories ────────────────────────────────────────────────── */
.cat{margin-bottom:16px}
.cat-hdr{
  font-size:10px;font-weight:600;color:#71717a;
  letter-spacing:3px;padding:6px 10px;margin-bottom:8px;
  border-left:2px solid #00d4aa;
  text-transform:uppercase;
}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}

/* ── Buttons ───────────────────────────────────────────────────── */
.btn{
  background:#0f1114;
  border:1px solid #1a1d23;
  color:#e4e4e7;
  padding:14px 12px;border-radius:6px;
  font-family:inherit;font-size:12px;cursor:pointer;
  text-align:center;display:flex;flex-direction:column;
  align-items:center;gap:4px;min-height:56px;
  transition:border-color 0.1s,box-shadow 0.1s;
}
.btn:active{
  background:#141619;
  border-color:#00d4aa;
  box-shadow:0 0 0 1px rgba(0,212,170,0.15);
}
.btn.disabled{opacity:0.3;pointer-events:none}
.btn-label{font-weight:700;letter-spacing:1.5px;font-size:12px}
.btn-desc{font-size:9px;color:#71717a;letter-spacing:0.3px;line-height:1.3}

/* ── Toast ─────────────────────────────────────────────────────── */
.toast{
  position:fixed;top:-60px;left:50%;transform:translateX(-50%);
  background:#0f1114;
  border:1px solid #ef4444;
  color:#fca5a5;
  padding:12px 20px;border-radius:6px;
  font-size:12px;z-index:200;max-width:90%;text-align:center;
  letter-spacing:0.3px;
  box-shadow:0 4px 12px rgba(0,0,0,0.5);
  transition:top 0.2s ease-out;
}
.toast.visible{top:20px}
.toast.fade-out{top:-60px;transition:top 0.3s ease-in}

/* ── Loading spinner ───────────────────────────────────────────── */
.loading{display:none;padding:40px;text-align:center;color:#71717a;font-size:11px;letter-spacing:2px}
.loading.active{display:block}
.loading::before{
  content:'';display:block;width:24px;height:24px;
  border:2px solid #1a1d23;border-top-color:#00d4aa;
  border-radius:50%;margin:0 auto 12px;
  animation:spin 0.8s linear infinite;
}
@keyframes spin{to{transform:rotate(360deg)}}

/* ── Output view (full screen takeover) ────────────────────────── */
.output-view{
  position:fixed;top:0;left:0;right:0;bottom:0;
  background:#08090a;z-index:100;
  flex-direction:column;
  transform:translateY(100%);opacity:0;
  transition:transform 0.2s ease-out,opacity 0.15s ease-out;
  display:flex;
}
.output-view.active{transform:translateY(0);opacity:1}
.out-hdr{
  background:linear-gradient(180deg,#0f1114 0%,#0c0d10 100%);
  padding:14px 16px;
  border-bottom:1px solid #1a1d23;
  display:flex;justify-content:space-between;align-items:center;
}
.out-title{font-size:12px;color:#e4e4e7;letter-spacing:3px;font-weight:600;display:flex;align-items:center;gap:8px}
.out-title .run-dot{
  width:6px;height:6px;border-radius:50%;
  background:#00d4aa;
  animation:pulse 2s ease-in-out infinite;
  flex-shrink:0;
}
.out-title .run-dot.stopped{background:#3f3f46;animation:none}
.out-status{
  font-size:10px;padding:4px 10px;border-radius:4px;
  letter-spacing:1px;font-weight:600;
}
.out-status.running{color:#00d4aa;background:rgba(0,212,170,0.08);border:1px solid rgba(0,212,170,0.2)}
.out-status.done{color:#71717a;background:rgba(113,113,122,0.08);border:1px solid #1a1d23}
.out-status.error{color:#ef4444;background:rgba(239,68,68,0.08);border:1px solid rgba(239,68,68,0.2)}
.out-status.preflight-fail{color:#f59e0b;background:rgba(245,158,11,0.08);border:1px solid rgba(245,158,11,0.2)}
.out-body{
  flex:1;overflow-y:auto;padding:12px 14px;
  font-family:'SF Mono','Cascadia Code','Consolas',monospace;
  font-size:11px;line-height:1.7;
  white-space:pre-wrap;word-break:break-all;
  color:#a1a1aa;
  background:#06070a;
  box-shadow:inset 0 2px 4px rgba(0,0,0,0.3);
  scroll-behavior:smooth;
}
.out-body .stderr{color:#f59e0b}
.out-buttons{
  padding:10px 14px;display:flex;gap:8px;
  background:linear-gradient(180deg,#0f1114 0%,#0c0d10 100%);
  border-top:1px solid #1a1d23;
}
.out-btn{
  flex:1;padding:14px;border-radius:6px;
  font-family:inherit;font-size:12px;font-weight:700;
  letter-spacing:1.5px;cursor:pointer;text-align:center;
  transition:border-color 0.1s,box-shadow 0.1s;
}
.out-btn.stop{background:#0f1114;border:1px solid rgba(239,68,68,0.3);color:#ef4444}
.out-btn.stop:active{background:#1a0a0a;border-color:#ef4444;box-shadow:0 0 0 1px rgba(239,68,68,0.15)}
.out-btn.stop.force{background:#1a0505;border-color:#ef4444;color:#fca5a5}
.out-btn.back{background:#0f1114;border:1px solid #1a1d23;color:#71717a}
.out-btn.back:active{background:#141619;border-color:#3f3f46}

/* ── Settings view ─────────────────────────────────────────────── */
.settings-view{
  position:fixed;top:0;left:0;right:0;bottom:0;
  background:#08090a;z-index:100;
  flex-direction:column;
  transform:translateY(100%);opacity:0;
  transition:transform 0.2s ease-out,opacity 0.15s ease-out;
  display:flex;
}
.settings-view.active{transform:translateY(0);opacity:1}
.settings-body{flex:1;overflow-y:auto;padding:14px}
.settings-cat{
  margin-bottom:16px;background:#0f1114;
  border:1px solid #1a1d23;border-radius:6px;padding:12px;
}
.settings-cat-name{font-size:10px;color:#71717a;letter-spacing:3px;font-weight:600;margin-bottom:10px;text-transform:uppercase}
.settings-tool{display:flex;align-items:center;gap:8px;padding:8px 0;border-bottom:1px solid #1a1d23}
.settings-tool:last-child{border-bottom:none}
.settings-tool-info{flex:1;font-size:12px;color:#e4e4e7}
.settings-tool-cmd{
  font-size:9px;color:#3f3f46;margin-top:3px;
  font-family:'SF Mono','Cascadia Code','Consolas',monospace;
}
.settings-btn-sm{
  background:#0f1114;border:1px solid #1a1d23;color:#71717a;
  padding:6px 10px;border-radius:4px;
  font-family:inherit;font-size:10px;font-weight:600;cursor:pointer;
  transition:border-color 0.1s;
}
.settings-btn-sm:active{border-color:#3f3f46}
.settings-btn-sm.del{border-color:rgba(239,68,68,0.2);color:#ef4444}
.settings-btn-sm.del:active{border-color:#ef4444}

/* ── Add tool form ─────────────────────────────────────────────── */
.add-form{
  background:#0f1114;border:1px solid #1a1d23;
  border-radius:6px;padding:12px;margin-top:14px;
}
.add-form input,.add-form select{
  background:#08090a;border:1px solid #1a1d23;color:#e4e4e7;
  padding:8px 10px;font-family:inherit;font-size:12px;
  border-radius:4px;width:100%;margin-bottom:8px;
  transition:border-color 0.1s;
  outline:none;
}
.add-form input:focus,.add-form select:focus{border-color:#00d4aa;box-shadow:0 0 0 1px rgba(0,212,170,0.1)}
.add-form input::placeholder{color:#3f3f46}
</style>
</head>
<body>

<!-- TOAST -->
<div class="toast" id="toast"></div>

<!-- MAIN VIEW -->
<div id="main-view">
  <div class="hdr">
    <div class="hdr-row">
      <div class="logo">
        <span class="logo-ax12">AX12</span>
        <span class="logo-sep">/</span>
        <span class="logo-tac">TAC</span>
        <span class="logo-sep">&nbsp;</span>
        <span class="logo-tools">TOOLS</span>
      </div>
      <div class="hdr-right">
        <div class="status-indicators">
          <div class="status-dot" id="ind-gps"><span class="dot" id="dot-gps"></span>GPS</div>
          <div class="status-dot" id="ind-ser"><span class="dot" id="dot-ser"></span>SER</div>
          <div class="stat-batt" id="stat-batt">{{BATT}}</div>
        </div>
        <div class="hdr-nav">
          <div class="hdr-link" onclick="location.href='/setup'">SETUP</div>
          <div class="hdr-link" onclick="showSettings()">&#9881;</div>
        </div>
      </div>
    </div>
  </div>
  <div class="wrap" id="buttons">
    {{BUTTONS}}
  </div>
</div>

<!-- OUTPUT VIEW -->
<div class="output-view" id="output-view">
  <div class="out-hdr">
    <div class="out-title"><span class="run-dot" id="run-dot"></span><span id="out-title-text">TOOL</span></div>
    <div class="out-status running" id="out-status">RUNNING</div>
  </div>
  <div class="loading" id="loading">STARTING...</div>
  <div class="out-body" id="out-body"></div>
  <div class="out-buttons">
    <button class="out-btn stop" id="stop-btn" onclick="stopTool()">STOP</button>
    <button class="out-btn back" id="back-btn" onclick="goBack()">BACK</button>
  </div>
</div>

<!-- SETTINGS VIEW -->
<div class="settings-view" id="settings-view">
  <div class="out-hdr">
    <div class="out-title"><span id="settings-title-text">SETTINGS</span></div>
    <div class="out-status done" style="cursor:pointer" onclick="hideSettings()">CLOSE</div>
  </div>
  <div class="settings-body" id="settings-body"></div>
  <div class="out-buttons">
    <button class="out-btn back" onclick="saveSettings()" style="border-color:rgba(0,212,170,0.3);color:#00d4aa">SAVE</button>
    <button class="out-btn back" onclick="hideSettings()">CANCEL</button>
  </div>
</div>

<script>
let pollTimer = null;
let outputIdx = 0;
let stopping = false;
let stopTime = 0;
let toolRunning = false;
let statusTimer = null;

/* ── Toast ─────────────────────────────────────────────────────── */
function showToast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = 'toast';
  void t.offsetWidth;
  t.className = 'toast visible';
  setTimeout(() => { t.className = 'toast fade-out'; }, 3000);
  setTimeout(() => { t.className = 'toast'; }, 3300);
}

/* ── Button state ──────────────────────────────────────────────── */
function setButtonsDisabled(disabled) {
  document.querySelectorAll('.btn').forEach(b => {
    if (disabled) b.classList.add('disabled');
    else b.classList.remove('disabled');
  });
}

/* ── Status polling ────────────────────────────────────────────── */
function pollStatus() {
  fetch('/api/status').then(r => r.json()).then(d => {
    const dotGps = document.getElementById('dot-gps');
    const dotSer = document.getElementById('dot-ser');
    const battEl = document.getElementById('stat-batt');

    if (d.gps) { dotGps.className = 'dot green pulse'; }
    else { dotGps.className = 'dot'; }

    if (d.serial_ttyS1) { dotSer.className = 'dot green'; }
    else if (d.serial_ttyS0) { dotSer.className = 'dot amber'; }
    else { dotSer.className = 'dot'; }

    if (d.battery && d.battery !== '?') { battEl.textContent = d.battery; }
  }).catch(() => {});
  statusTimer = setTimeout(pollStatus, 10000);
}

/* Start status polling on load */
pollStatus();

/* ── Run tool ──────────────────────────────────────────────────── */
function runTool(shortcut) {
  if (toolRunning) {
    showToast('A tool is already running. Stop it first.');
    return;
  }

  const body = document.getElementById('out-body');
  const title = document.getElementById('out-title-text');
  const runDot = document.getElementById('run-dot');
  const status = document.getElementById('out-status');
  const stopBtn = document.getElementById('stop-btn');
  const loading = document.getElementById('loading');

  body.innerHTML = '';
  outputIdx = 0;
  stopping = false;
  toolRunning = true;
  stopBtn.textContent = 'STOP';
  stopBtn.className = 'out-btn stop';
  stopBtn.style.display = '';
  title.textContent = shortcut.toUpperCase();
  runDot.className = 'run-dot';
  status.textContent = 'STARTING';
  status.className = 'out-status running';
  loading.className = 'loading active';
  setButtonsDisabled(true);

  document.getElementById('output-view').classList.add('active');

  fetch('/api/run', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({shortcut: shortcut})
  })
  .then(r => r.json())
  .then(data => {
    loading.className = 'loading';
    if (!data.ok) {
      toolRunning = false;
      setButtonsDisabled(false);
      runDot.className = 'run-dot stopped';
      status.textContent = data.preflight ? 'PRE-FLIGHT FAIL' : 'ERROR';
      status.className = 'out-status ' + (data.preflight ? 'preflight-fail' : 'error');
      body.innerHTML = '<div style="color:#f59e0b;white-space:pre-wrap">' + escHtml(data.error) + '</div>';
      stopBtn.style.display = 'none';
      return;
    }
    title.textContent = data.label || shortcut.toUpperCase();
    status.textContent = 'RUNNING';
    pollOutput();
  })
  .catch(e => {
    loading.className = 'loading';
    toolRunning = false;
    setButtonsDisabled(false);
    runDot.className = 'run-dot stopped';
    status.textContent = 'ERROR';
    status.className = 'out-status error';
    body.innerHTML = '<div style="color:#ef4444">' + escHtml(String(e)) + '</div>';
    stopBtn.style.display = 'none';
  });
}

/* ── Poll output ───────────────────────────────────────────────── */
function pollOutput() {
  if (pollTimer) clearTimeout(pollTimer);
  fetch('/api/output?since=' + outputIdx)
    .then(r => r.json())
    .then(data => {
      const body = document.getElementById('out-body');
      const status = document.getElementById('out-status');
      const stopBtn = document.getElementById('stop-btn');
      const loading = document.getElementById('loading');
      const runDot = document.getElementById('run-dot');

      if (data.lines && data.lines.length > 0) {
        loading.className = 'loading';
        for (const line of data.lines) {
          /* Bug fix: use insertAdjacentHTML instead of innerHTML += for DOM performance */
          body.insertAdjacentHTML('beforeend', line);
        }
        body.scrollTop = body.scrollHeight;
      }
      outputIdx = data.index;

      if (data.done) {
        loading.className = 'loading';
        toolRunning = false;
        setButtonsDisabled(false);
        runDot.className = 'run-dot stopped';
        if (data.exit_code === 0 || data.exit_code === null) {
          status.textContent = 'DONE';
          status.className = 'out-status done';
        } else {
          status.textContent = 'EXIT ' + data.exit_code;
          status.className = 'out-status error';
        }
        stopBtn.style.display = 'none';
        return;
      }

      if (stopping && (Date.now() - stopTime > 3000)) {
        stopBtn.textContent = 'FORCE KILL';
        stopBtn.className = 'out-btn stop force';
      }

      pollTimer = setTimeout(pollOutput, 300);
    })
    .catch(() => {
      pollTimer = setTimeout(pollOutput, 1000);
    });
}

/* ── Stop tool ─────────────────────────────────────────────────── */
function stopTool() {
  const stopBtn = document.getElementById('stop-btn');
  const force = stopBtn.textContent === 'FORCE KILL';

  if (!stopping) {
    stopping = true;
    stopTime = Date.now();
    stopBtn.textContent = 'STOPPING...';
  }

  fetch('/api/stop', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({force: force})
  });
}

function goBack() {
  if (pollTimer) clearTimeout(pollTimer);
  document.getElementById('output-view').classList.remove('active');
  if (toolRunning) {
    fetch('/api/stop', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({force: true})
    }).finally(() => {
      toolRunning = false;
      setButtonsDisabled(false);
    });
  }
}

/* ── Settings ──────────────────────────────────────────────────── */
function showSettings() {
  fetch('/api/config').then(r => r.json()).then(renderSettings);
  document.getElementById('settings-view').classList.add('active');
}

function hideSettings() {
  document.getElementById('settings-view').classList.remove('active');
}

function renderSettings(config) {
  const body = document.getElementById('settings-body');
  if (!config.tak_server) {
    config.tak_server = {enabled: false, host: '', port: 8087, tls: false, cert: '', key: '', ca: ''};
  }
  window._settingsConfig = config;
  const t = config.tak_server;
  let html = '';

  /* ── TAK Server upstream ──────────────────────────────────────── */
  html += '<div class="settings-cat">';
  html += '<div class="settings-cat-name">TAK SERVER UPSTREAM</div>';
  html += '<div class="settings-tool" style="padding:4px 0">';
  html +=   '<div class="settings-tool-info">';
  html +=     '<label style="display:flex;align-items:center;gap:8px;cursor:pointer">';
  html +=       '<input type="checkbox" id="tak-enabled" onchange="toggleTakForm()"' + (t.enabled ? ' checked' : '') + '>';
  html +=       '<span>Fan out CoT to a TAK server</span></label>';
  html +=     '<div class="settings-tool-cmd">In addition to the local UDP listener on :4242</div>';
  html +=   '</div></div>';
  html += '<div id="tak-form" style="display:' + (t.enabled ? 'block' : 'none') + ';padding-top:8px">';
  html +=   '<input id="tak-host" placeholder="Host (e.g. tak.example.mil)" value="' + escAttr(t.host || '') + '">';
  html +=   '<input id="tak-port" placeholder="Port (8087 TCP, 8089 TLS)" type="number" value="' + escAttr(t.port || '') + '">';
  html +=   '<label style="display:flex;align-items:center;gap:8px;margin-bottom:8px;cursor:pointer">';
  html +=     '<input type="checkbox" id="tak-tls" onchange="toggleTakTls()"' + (t.tls ? ' checked' : '') + '>';
  html +=     '<span style="font-size:12px;color:#e4e4e7">Use TLS (mutual, client cert required)</span></label>';
  html +=   '<div id="tak-tls-fields" style="display:' + (t.tls ? 'block' : 'none') + '">';
  html +=     '<input id="tak-cert" placeholder="Client cert PEM path" value="' + escAttr(t.cert || '') + '">';
  html +=     '<input id="tak-key"  placeholder="Client key PEM path (can be same as cert)" value="' + escAttr(t.key || '') + '">';
  html +=     '<input id="tak-ca"   placeholder="CA bundle PEM path (optional)" value="' + escAttr(t.ca || '') + '">';
  html +=   '</div>';
  html +=   '<button class="settings-btn-sm" style="border-color:rgba(0,212,170,0.3);color:#00d4aa" onclick="testTakServer()">TEST CONNECTION</button>';
  html +=   '<div id="tak-test-msg" class="settings-tool-cmd" style="margin-top:8px"></div>';
  html += '</div>';
  html += '</div>';

  config.categories.forEach((cat, ci) => {
    html += '<div class="settings-cat"><div class="settings-cat-name">' + escHtml(cat.name) + '</div>';
    cat.tools.forEach((tool, ti) => {
      html += '<div class="settings-tool">';
      html += '<div class="settings-tool-info">' + escHtml(tool.label);
      html += '<div class="settings-tool-cmd">' + escHtml(tool.cmd) + '</div></div>';
      html += '<button class="settings-btn-sm" onclick="moveTool(' + ci + ',' + ti + ',-1)">&#9650;</button>';
      html += '<button class="settings-btn-sm" onclick="moveTool(' + ci + ',' + ti + ',1)">&#9660;</button>';
      html += '<button class="settings-btn-sm del" onclick="delTool(' + ci + ',' + ti + ')">DEL</button>';
      html += '</div>';
    });
    html += '</div>';
  });
  html += '<div class="add-form">';
  html += '<div class="settings-cat-name">ADD TOOL</div>';
  html += '<select id="add-cat">';
  config.categories.forEach((cat, ci) => {
    html += '<option value="' + ci + '">' + escHtml(cat.name) + '</option>';
  });
  html += '</select>';
  html += '<input id="add-label" placeholder="LABEL (e.g. MY TOOL)">';
  html += '<input id="add-desc" placeholder="Description">';
  html += '<input id="add-cmd" placeholder="Command (e.g. su 0 python3 tools/my_tool.py)">';
  html += '<input id="add-shortcut" placeholder="Shortcut (e.g. mytool)">';
  html += '<button class="settings-btn-sm" style="border-color:rgba(0,212,170,0.3);color:#00d4aa" onclick="addTool()">ADD</button>';
  html += '</div>';
  body.innerHTML = html;
}

function moveTool(ci, ti, dir) {
  const cfg = window._settingsConfig;
  const tools = cfg.categories[ci].tools;
  const ni = ti + dir;
  if (ni < 0 || ni >= tools.length) return;
  [tools[ti], tools[ni]] = [tools[ni], tools[ti]];
  renderSettings(cfg);
}

function delTool(ci, ti) {
  const cfg = window._settingsConfig;
  cfg.categories[ci].tools.splice(ti, 1);
  renderSettings(cfg);
}

function addTool() {
  const cfg = window._settingsConfig;
  const ci = parseInt(document.getElementById('add-cat').value);
  const label = document.getElementById('add-label').value.trim();
  const cmd = document.getElementById('add-cmd').value.trim();
  if (!label || !cmd) return;
  cfg.categories[ci].tools.push({
    label: label,
    description: document.getElementById('add-desc').value.trim(),
    cmd: cmd,
    shortcut: document.getElementById('add-shortcut').value.trim() || label.toLowerCase().replace(/\s+/g, '-'),
    requires: [],
    long_running: false,
    timeout: 30
  });
  renderSettings(cfg);
}

function collectTakServer() {
  const t = window._settingsConfig.tak_server || {};
  const enabledEl = document.getElementById('tak-enabled');
  if (!enabledEl) return t;
  t.enabled = enabledEl.checked;
  const host = document.getElementById('tak-host');
  const port = document.getElementById('tak-port');
  const tls = document.getElementById('tak-tls');
  const cert = document.getElementById('tak-cert');
  const key = document.getElementById('tak-key');
  const ca = document.getElementById('tak-ca');
  if (host) t.host = host.value.trim();
  if (port) t.port = parseInt(port.value) || 0;
  if (tls) t.tls = tls.checked;
  if (cert) t.cert = cert.value.trim();
  if (key) t.key = key.value.trim();
  if (ca) t.ca = ca.value.trim();
  window._settingsConfig.tak_server = t;
  return t;
}

function toggleTakForm() {
  const enabled = document.getElementById('tak-enabled').checked;
  document.getElementById('tak-form').style.display = enabled ? 'block' : 'none';
}

function toggleTakTls() {
  const tls = document.getElementById('tak-tls').checked;
  document.getElementById('tak-tls-fields').style.display = tls ? 'block' : 'none';
}

function testTakServer() {
  const cfg = collectTakServer();
  const msg = document.getElementById('tak-test-msg');
  msg.textContent = 'Testing...';
  msg.style.color = '#71717a';
  fetch('/api/tak/test', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(cfg)
  }).then(r => r.json()).then(data => {
    msg.textContent = data.message || (data.ok ? 'OK' : 'FAIL');
    msg.style.color = data.ok ? '#00d4aa' : '#ef4444';
  }).catch(e => {
    msg.textContent = String(e);
    msg.style.color = '#ef4444';
  });
}

function saveSettings() {
  collectTakServer();
  fetch('/api/config', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(window._settingsConfig)
  }).then(r => r.json()).then(data => {
    if (data.ok) {
      hideSettings();
      location.reload();
    }
  });
}

function escHtml(s) {
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

function escAttr(s) {
  return String(s).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
</script>
</body>
</html>"""


# ── Setup wizard page ────────────────────────────────────────────────────────

SETUP_HTML = r"""<!DOCTYPE html>
<html><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,user-scalable=no">
<meta name="theme-color" content="#08090a">
<title>AX12 SETUP</title><link rel="icon" href="/icon.png" type="image/png">
<style>
*{margin:0;padding:0;box-sizing:border-box;-webkit-tap-highlight-color:transparent}
html,body{
  background:#08090a;color:#e4e4e7;
  font-family:-apple-system,'Inter','Segoe UI',system-ui,sans-serif;
  font-size:14px;-webkit-font-smoothing:antialiased;
}
.hdr{
  background:linear-gradient(180deg,#0f1114 0%,#0c0d10 100%);
  padding:14px 16px;
  border-bottom:1px solid #1a1d23;
  box-shadow:0 1px 0 rgba(0,212,170,0.05);
  display:flex;justify-content:space-between;align-items:center;
}
.logo{font-size:13px;font-weight:600;color:#e4e4e7;letter-spacing:5px}
.logo span{color:#00d4aa}
.back-link{
  color:#71717a;font-size:10px;cursor:pointer;padding:6px 8px;
  letter-spacing:1px;font-weight:600;border-radius:4px;
  border:1px solid transparent;transition:color 0.1s,border-color 0.1s;
}
.back-link:active{color:#e4e4e7;border-color:#1a1d23}
.wrap{padding:16px;max-width:480px;margin:0 auto}
.step{
  background:#0f1114;border:1px solid #1a1d23;
  border-radius:6px;padding:14px;margin-bottom:12px;
}
.step-hdr{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px}
.step-title{font-size:11px;font-weight:600;color:#e4e4e7;letter-spacing:2px}
.step-status{font-size:9px;padding:3px 10px;border-radius:4px;letter-spacing:1px;font-weight:600}
.step-status.ok{color:#00d4aa;background:rgba(0,212,170,0.08);border:1px solid rgba(0,212,170,0.2)}
.step-status.fail{color:#ef4444;background:rgba(239,68,68,0.08);border:1px solid rgba(239,68,68,0.2)}
.step-status.manual{color:#f59e0b;background:rgba(245,158,11,0.08);border:1px solid rgba(245,158,11,0.2)}
.step-status.loading{color:#71717a;background:rgba(113,113,122,0.08);border:1px solid #1a1d23}
.step-body{font-size:12px;color:#a1a1aa;line-height:1.6}
.step-body b{color:#e4e4e7}
.step-body code{
  background:#08090a;padding:2px 6px;border-radius:3px;
  color:#00d4aa;font-family:'SF Mono','Cascadia Code','Consolas',monospace;
  font-size:11px;
}
.step-body a{color:#3b82f6;text-decoration:none}
.step-body a:active{color:#60a5fa}
.step-btn{
  background:#0f1114;border:1px solid rgba(0,212,170,0.3);
  color:#00d4aa;padding:10px 18px;border-radius:4px;
  font-family:inherit;font-size:11px;font-weight:600;
  letter-spacing:1px;cursor:pointer;margin-top:10px;
  transition:border-color 0.1s;
}
.step-btn:active{border-color:#00d4aa;background:#141619}
.step-btn.disabled{opacity:0.3;pointer-events:none}
.params{
  background:#08090a;border:1px solid #1a1d23;border-radius:4px;
  padding:10px;margin:10px 0;
  font-family:'SF Mono','Cascadia Code','Consolas',monospace;
  font-size:11px;line-height:2;
}
.params .k{color:#f59e0b}.params .v{color:#00d4aa}
.note{font-size:11px;color:#71717a;margin-top:8px;line-height:1.5}
</style></head><body>
<div class="hdr">
  <div class="logo"><span>AX12</span> SETUP</div>
  <div class="back-link" onclick="location.href='/'">BACK</div>
</div>
<div class="wrap">
  <div class="step"><div class="step-hdr"><div class="step-title">1. ROOT ACCESS</div><div class="step-status loading" id="s1">CHECKING</div></div><div class="step-body">Factory root via su 0.</div></div>

  <div class="step"><div class="step-hdr"><div class="step-title">2. INSTALL ATAK</div><div class="step-status loading" id="s2">CHECKING</div></div><div class="step-body" id="b2">Checking...</div></div>

  <div class="step"><div class="step-hdr"><div class="step-title">3. ATAK NETWORK INPUT</div><div class="step-status loading" id="s3">CHECKING</div></div><div class="step-body" id="b3">Checking...</div></div>

  <div class="step"><div class="step-hdr"><div class="step-title">4. ELRS MAVLINK MODE</div><div class="step-status manual" id="s4">MANUAL</div></div>
  <div class="step-body">Open Flyshark on the AX12:<br><br><b>System Menu &gt; ELRS Lua &gt; Link Mode &gt; MAVLink</b><br><br>Tap <b>Save &amp; Reboot</b>. Then power cycle the receiver on the drone.<br><div class="note">Both TX and RX need ELRS 3.5+. You can switch back to CRSF anytime for normal flying.</div></div></div>

  <div class="step"><div class="step-hdr"><div class="step-title">5. FLIGHT CONTROLLER</div><div class="step-status manual" id="s5">MANUAL</div></div>
  <div class="step-body">Connect to FC with Mission Planner or QGC. Set on the UART where ELRS RX is connected:<div class="params"><span class="k">SERIALn_PROTOCOL</span> = <span class="v">2</span> (MAVLink 2)<br><span class="k">SERIALn_BAUD</span> = <span class="v">460</span> (460800)<br><span class="k">SRn_POSITION</span> = <span class="v">1</span><br><span class="k">SRn_EXTRA1</span> = <span class="v">1</span><br><span class="k">SRn_EXTRA2</span> = <span class="v">1</span><br><span class="k">SRn_EXT_STAT</span> = <span class="v">1</span></div>Reboot FC after saving. RX must be ESP-based (RP1/RP2/RP3, EP1/EP2).<div class="note">Only needs to be done once per drone.</div></div></div>

  <div class="step"><div class="step-hdr"><div class="step-title">6. FLY</div><div class="step-status ok" id="s6">READY</div></div>
  <div class="step-body">Power on drone, wait for GPS lock, tap <b>ATAK BRIDGE</b>, switch to ATAK. Your drone is on the map.<br><br><button class="step-btn" onclick="location.href='/'">BACK TO TOOLS</button></div></div>
</div>
<script>
fetch('/api/setup-check').then(r=>r.json()).then(d=>{
  const s1=document.getElementById('s1');
  if(d.root.ok){s1.textContent='OK';s1.className='step-status ok'}else{s1.textContent='FAIL';s1.className='step-status fail'}

  const s2=document.getElementById('s2'),b2=document.getElementById('b2');
  if(d.atak_installed.ok){s2.textContent='INSTALLED';s2.className='step-status ok';b2.innerHTML=d.atak_installed.detail}
  else{s2.textContent='NOT FOUND';s2.className='step-status fail';b2.innerHTML='<b>IMPORTANT:</b> The AX12 runs Android 9. ATAK 5.x requires Android 10+. You need <b>ATAK-CIV 4.10</b>.<br><br>Download:<br>&bull; <a href="https://apkpure.com/atak-civ-civil-use/com.atakmap.app.civ/versions" target="_blank">APKPure — ATAK old versions</a> (get 4.10.0)<br>&bull; <a href="https://files.civtak.org" target="_blank">files.civtak.org</a> (official repo)<br>&bull; <a href="https://github.com/deptofdefense/AndroidTacticalAssaultKit-CIV/releases" target="_blank">GitHub releases</a> (DoD source)<br><br>Install the APK, open ATAK once, then come back.<br><br><button class="step-btn" onclick="location.reload()">CHECK AGAIN</button>'}

  const s3=document.getElementById('s3'),b3=document.getElementById('b3');
  if(d.atak_udp.ok){s3.textContent='CONFIGURED';s3.className='step-status ok';b3.innerHTML='UDP 4242 input ready.'}
  else if(!d.atak_installed.ok){s3.textContent='WAITING';s3.className='step-status manual';b3.innerHTML='Install ATAK first (step 2).'}
  else{s3.textContent='NOT SET';s3.className='step-status fail';b3.innerHTML='ATAK needs UDP input on port 4242.<br><br><button class="step-btn" id="cfg-btn" onclick="cfgAtak()">AUTO-CONFIGURE</button><div class="note" id="cfg-msg"></div><br><div class="note">If auto-config fails: ATAK &gt; Settings &gt; Network Preferences &gt; Add &gt; UDP, port 4242, address 0.0.0.0</div>'}
}).catch(()=>{document.getElementById('s1').textContent='ERROR'});

function cfgAtak(){
  const b=document.getElementById('cfg-btn'),m=document.getElementById('cfg-msg');
  b.classList.add('disabled');b.textContent='CONFIGURING...';
  fetch('/api/setup-configure-atak',{method:'POST'}).then(r=>r.json()).then(d=>{
    if(d.ok){m.innerHTML='<span style="color:#00d4aa">'+d.message+'</span>';document.getElementById('s3').textContent='CONFIGURED';document.getElementById('s3').className='step-status ok'}
    else{m.innerHTML='<span style="color:#ef4444">'+d.message+'</span>';b.classList.remove('disabled');b.textContent='RETRY'}
  }).catch(e=>{m.innerHTML='<span style="color:#ef4444">'+e+'</span>';b.classList.remove('disabled');b.textContent='RETRY'});
}
</script></body></html>"""


# ══════════════════════════════════════════════════════════════════════════════
# 9. HTTP HANDLER
# ══════════════════════════════════════════════════════════════════════════════

class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        sys.stderr.write("[%s] %s\n" % (self.log_date_time_string(), fmt % args))
        sys.stderr.flush()

    def _json(self, data, code=200):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def _check_origin(self):
        """Reject state-changing requests from other origins.

        Browsers always set Origin on cross-origin POST. Same-origin fetches
        from the served page also set it. Absent Origin (curl, launcher scripts
        on the device) is allowed.
        """
        origin = self.headers.get("Origin")
        if origin is None:
            return True
        allowed = ("http://localhost:", "http://127.0.0.1:")
        if origin.startswith(allowed):
            return True
        self._json({"ok": False, "error": "Forbidden origin"}, code=403)
        return False

    def _html(self, content):
        body = content.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/":
            self._html(build_page())

        elif self.path.startswith("/api/output"):
            # Parse ?since=N
            since = 0
            if "?" in self.path:
                for part in self.path.split("?")[1].split("&"):
                    if part.startswith("since="):
                        # Bug fix: wrap in try/except for malformed values
                        try:
                            since = int(part.split("=")[1])
                        except (ValueError, IndexError):
                            since = 0
            lines, new_idx, done, exit_code = get_output_since(since)
            html_lines = []
            for kind, text in lines:
                html_lines.append(ansi_to_html(text))
            self._json({
                "lines": html_lines,
                "index": new_idx,
                "done": done,
                "exit_code": exit_code,
            })

        elif self.path == "/api/config":
            self._json(load_config())

        elif self.path == "/api/status":
            self._json(get_full_status())

        elif self.path == "/setup":
            self._html(SETUP_HTML)

        elif self.path == "/api/setup-check":
            self._json(run_setup_check())

        elif self.path == "/icon.png":
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", len(ICON_PNG))
            self.send_header("Cache-Control", "public, max-age=86400")
            self.end_headers()
            self.wfile.write(ICON_PNG)

        elif self.path == "/manifest.json":
            manifest = {
                "name": "AX12 TAC TOOLS",
                "short_name": "TAC",
                "start_url": "/",
                "display": "standalone",
                "background_color": "#08090a",
                "theme_color": "#08090a",
                "icons": [{"src": "/icon.png", "sizes": "192x192", "type": "image/png"}]
            }
            self._json(manifest)

        else:
            self.send_error(404)

    def do_POST(self):
        if not self._check_origin():
            return
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(body)
        except Exception:
            data = {}

        if self.path == "/api/run":
            shortcut = data.get("shortcut", "")
            config = load_config()

            # Find tool by shortcut
            tool = None
            for cat in config.get("categories", []):
                for t in cat.get("tools", []):
                    if t.get("shortcut") == shortcut:
                        tool = t
                        break
                if tool:
                    break

            if not tool:
                self._json({"ok": False, "error": f"Unknown tool: {shortcut}"})
                return

            # Pre-flight checks
            ok, failures = check_requirements(tool.get("requires", []))
            if not ok:
                msg = "Pre-flight check failed:\n\n" + "\n".join(f"  - {f}" for f in failures)
                self._json({"ok": False, "error": msg, "preflight": True})
                return

            cmd = tool["cmd"]
            label = tool["label"]
            timeout = tool.get("timeout")
            if tool.get("long_running"):
                timeout = None

            # ATAK BRIDGE gets TAK-server flags appended from the tak_server
            # config block if one is enabled. Other tools pass through.
            cmd = apply_tak_server_flags(cmd)

            # Handle special commands
            if cmd.startswith("__"):
                output = run_special(cmd)
                with _proc_lock:
                    global _output_lines, _proc_done, _proc_exit_code, _current_label
                    _output_lines = [("out", output)]
                    _proc_done = True
                    _proc_exit_code = 0
                    _current_label = label
                self._json({"ok": True, "label": label})
                return

            started, err = start_tool(cmd, label, timeout)
            if not started:
                self._json({"ok": False, "error": err})
                return
            self._json({"ok": True, "label": label})

        elif self.path == "/api/stop":
            force = data.get("force", False)
            ok, msg = stop_tool(force)
            self._json({"ok": ok, "message": msg})

        elif self.path == "/api/config":
            save_config(data)
            self._json({"ok": True})

        elif self.path == "/api/setup-configure-atak":
            ok, msg = inject_atak_udp_config()
            self._json({"ok": ok, "message": msg})

        elif self.path == "/api/tak/test":
            # Accept an optional ad-hoc config in the request body so the
            # settings UI can test before saving. Falls back to the persisted
            # tak_server block when the body is empty.
            cfg = data if data else (load_config().get("tak_server") or {})
            ok, msg = test_tak_server(cfg)
            self._json({"ok": ok, "message": msg})

        else:
            self.send_error(404)

    def do_OPTIONS(self):
        # Same-origin only — no CORS preflight needed.
        self.send_response(405)
        self.end_headers()


class ThreadedServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


# ══════════════════════════════════════════════════════════════════════════════
# 10. MAIN / SERVER
# ══════════════════════════════════════════════════════════════════════════════

def main():
    port = PORT
    if len(sys.argv) > 1:
        for i, arg in enumerate(sys.argv[1:], 1):
            if arg == "--port" and i + 1 < len(sys.argv):
                port = int(sys.argv[i + 1])
            elif arg.startswith("--port="):
                port = int(arg.split("=")[1])

    # Check if another server is actively listening
    # Bug fix: close the socket in a finally block to prevent leaks
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect(("127.0.0.1", port))
        # Connection succeeded — something is already serving
        print(f"[tac-web] Port {port} already in use — server may already be running")
        sys.exit(0)
    except (ConnectionRefusedError, OSError):
        pass  # Nothing listening — safe to start
    finally:
        sock.close()

    # Bug fix: bind to 127.0.0.1 (localhost only), not 0.0.0.0
    server = ThreadedServer(("127.0.0.1", port), Handler)
    print(f"[tac-web] Serving on http://localhost:{port}")
    print(f"[tac-web] Bookmark this URL to your home screen")
    print(f"[tac-web] Ctrl+C to stop")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[tac-web] Shutting down")
        server.shutdown()


if __name__ == "__main__":
    main()
