#!/data/data/com.termux/files/usr/bin/python3
"""AX12 Tactical Tools — Web Launcher

Touch-friendly web UI for the RadioMaster AX12. Serves on localhost:8080.
Bookmark to home screen for app-like access.

Usage:
    python3 web_launcher.py              # start server
    python3 web_launcher.py --port 9090  # custom port
"""

import html as html_mod
import http.server
import json
import os
import re
import signal
import socketserver
import subprocess
import sys
import threading
import time

import base64

PORT = 8080

# 192x192 tactical crosshair icon (base64 PNG)
ICON_B64 = "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"
ICON_PNG = base64.b64decode(ICON_B64)
REPO_DIR = os.path.dirname(os.path.abspath(__file__))
PYTHON3 = "/data/data/com.termux/files/usr/bin/python3"
LUA_SRC = os.path.join(REPO_DIR, "lua")
LUA_DEST = "/storage/emulated/0/AX12LUA/SCRIPTS/TOOLS"

# User config overrides the default
USER_CONFIG = os.path.expanduser("~/.config/ax12-tac-tools/tools.json")
DEFAULT_CONFIG = os.path.join(REPO_DIR, "tools.json")

# ── Process management ────────────────────────────────────────────────────────

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


def start_tool(cmd, label, timeout=None):
    """Start a tool subprocess. Returns (ok, error_msg)."""
    global _current_proc, _current_label, _output_lines, _proc_done, _proc_exit_code

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
            cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1, env=env, cwd=REPO_DIR,
            preexec_fn=os.setsid,
        )
    except Exception as e:
        return False, str(e)

    with _proc_lock:
        _current_proc = proc

    t = threading.Thread(target=_read_output, args=(proc,), daemon=True)
    t.start()

    # Auto-kill after timeout (non-long-running tools)
    if timeout and timeout > 0:
        def _auto_kill():
            time.sleep(timeout)
            with _proc_lock:
                if _current_proc and _current_proc.poll() is None:
                    _output_lines.append(("out", f"\n[TIMEOUT] Killed after {timeout}s\n"))
                    try:
                        os.killpg(os.getpgid(_current_proc.pid), signal.SIGKILL)
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
    """Get output lines since index. Returns (lines, new_index, done, exit_code)."""
    with _proc_lock:
        new_lines = _output_lines[index:]
        return new_lines, len(_output_lines), _proc_done, _proc_exit_code


# ── Config ────────────────────────────────────────────────────────────────────

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


# ── Pre-flight checks ────────────────────────────────────────────────────────

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


# ── Special commands ──────────────────────────────────────────────────────────

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


# ── Setup wizard checks ───────────────────────────────────────────────────────

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


def check_atak_udp_configured():
    try:
        r = subprocess.run(
            ["su", "0", "sh", "-c", "grep -r '4242' /storage/emulated/0/atak/ 2>/dev/null"],
            capture_output=True, text=True, timeout=5)
        if "4242" in r.stdout:
            return True
    except Exception:
        pass
    return False


def inject_atak_udp_config():
    atak_dir = "/storage/emulated/0/atak"
    try:
        r = subprocess.run(["su", "0", "ls", atak_dir], capture_output=True,
                           text=True, timeout=3)
        if r.returncode != 0:
            return False, "ATAK config directory not found. Launch ATAK once first, then re-run setup."
    except Exception as e:
        return False, str(e)

    pref_xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>\n<preferences>\n  <preference version="1" name="cot_streams">\n    <entry key="count" class="class java.lang.Integer">1</entry>\n    <entry key="description0" class="class java.lang.String">AX12 CoT Bridge</entry>\n    <entry key="enabled0" class="class java.lang.Boolean">true</entry>\n    <entry key="connectString0" class="class java.lang.String">udp+cotsocket://0.0.0.0:4242</entry>\n  </preference>\n</preferences>'

    pref_dir = f"{atak_dir}/config/prefs"
    try:
        subprocess.run(["su", "0", "mkdir", "-p", pref_dir], capture_output=True, timeout=5)
        proc = subprocess.run(
            ["su", "0", "sh", "-c", f"cat > {pref_dir}/cot_streams.xml"],
            input=pref_xml, capture_output=True, text=True, timeout=5)
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

    if installed:
        checks["atak_udp"] = {"ok": check_atak_udp_configured(), "detail": "UDP 4242" if check_atak_udp_configured() else "Not configured"}
    else:
        checks["atak_udp"] = {"ok": False, "detail": "ATAK not installed"}

    checks["serial"] = {"ok": os.path.exists("/dev/ttyS1"), "detail": "/dev/ttyS1"}
    return checks


SETUP_HTML = r"""<!DOCTYPE html>
<html><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,user-scalable=no">
<title>AX12 SETUP</title><link rel="icon" href="/icon.png" type="image/png">
<style>
*{margin:0;padding:0;box-sizing:border-box;-webkit-tap-highlight-color:transparent}
html,body{background:#0a0a0a;color:#e0e0e0;font-family:'Courier New',monospace;font-size:14px}
.hdr{background:#0f0f0f;padding:12px 16px;border-bottom:1px solid #1a3a1a;display:flex;justify-content:space-between;align-items:center}
.logo{font-size:13px;font-weight:700;color:#4a4;letter-spacing:3px}
.back-link{color:#3a3;font-size:11px;cursor:pointer;padding:8px;letter-spacing:1px}
.wrap{padding:16px;max-width:480px;margin:0 auto}
.step{background:#0f0f0f;border:1px solid #1a3a1a;border-radius:4px;padding:14px;margin-bottom:12px}
.step-hdr{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px}
.step-title{font-size:12px;font-weight:700;color:#6c6;letter-spacing:1px}
.step-status{font-size:10px;padding:2px 8px;border-radius:2px;letter-spacing:1px}
.step-status.ok{color:#4f4;background:rgba(79,255,79,0.1);border:1px solid #2a4a2a}
.step-status.fail{color:#c66;background:rgba(204,102,102,0.1);border:1px solid #4a2a2a}
.step-status.manual{color:#ca3;background:rgba(204,170,51,0.1);border:1px solid #4a3a1a}
.step-status.loading{color:#3a3;background:rgba(42,74,42,0.1);border:1px solid #1a3a1a}
.step-body{font-size:11px;color:#4a4;line-height:1.6}
.step-body code{background:#111;padding:1px 4px;border-radius:2px;color:#6c6}
.step-btn{background:#1a2a1a;border:1px solid #2a4a2a;color:#6c6;padding:8px 16px;border-radius:3px;font-family:inherit;font-size:11px;font-weight:700;letter-spacing:1px;cursor:pointer;margin-top:8px}
.step-btn:active{background:#2a3a2a}
.step-btn.disabled{opacity:0.3;pointer-events:none}
.params{background:#111;border:1px solid #1a3a1a;border-radius:3px;padding:8px;margin:8px 0;font-size:10px;line-height:1.8}
.params .k{color:#ca3}.params .v{color:#6c6}
.note{font-size:10px;color:#555;margin-top:6px;line-height:1.4}
</style></head><body>
<div class="hdr">
  <div class="logo">FIRST TIME SETUP</div>
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
  else{s2.textContent='NOT FOUND';s2.className='step-status fail';b2.innerHTML='<b>IMPORTANT:</b> The AX12 runs Android 9. ATAK 5.x requires Android 10+. You need <b>ATAK-CIV 4.10</b>.<br><br>Download:<br>&bull; <a href="https://apkpure.com/atak-civ-civil-use/com.atakmap.app.civ/versions" style="color:#6c6" target="_blank">APKPure — ATAK old versions</a> (get 4.10.0)<br>&bull; <a href="https://files.civtak.org" style="color:#6c6" target="_blank">files.civtak.org</a> (official repo)<br>&bull; <a href="https://github.com/deptofdefense/AndroidTacticalAssaultKit-CIV/releases" style="color:#6c6" target="_blank">GitHub releases</a> (DoD source)<br><br>Install the APK, open ATAK once, then come back.<br><br><button class="step-btn" onclick="location.reload()">CHECK AGAIN</button>'}

  const s3=document.getElementById('s3'),b3=document.getElementById('b3');
  if(d.atak_udp.ok){s3.textContent='CONFIGURED';s3.className='step-status ok';b3.innerHTML='UDP 4242 input ready.'}
  else if(!d.atak_installed.ok){s3.textContent='WAITING';s3.className='step-status manual';b3.innerHTML='Install ATAK first (step 2).'}
  else{s3.textContent='NOT SET';s3.className='step-status fail';b3.innerHTML='ATAK needs UDP input on port 4242.<br><br><button class="step-btn" id="cfg-btn" onclick="cfgAtak()">AUTO-CONFIGURE</button><div class="note" id="cfg-msg"></div><br><div class="note">If auto-config fails: ATAK &gt; Settings &gt; Network Preferences &gt; Add &gt; UDP, port 4242, address 0.0.0.0</div>'}
}).catch(()=>{document.getElementById('s1').textContent='ERROR'});

function cfgAtak(){
  const b=document.getElementById('cfg-btn'),m=document.getElementById('cfg-msg');
  b.classList.add('disabled');b.textContent='CONFIGURING...';
  fetch('/api/setup-configure-atak',{method:'POST'}).then(r=>r.json()).then(d=>{
    if(d.ok){m.innerHTML='<span style="color:#4f4">'+d.message+'</span>';document.getElementById('s3').textContent='CONFIGURED';document.getElementById('s3').className='step-status ok'}
    else{m.innerHTML='<span style="color:#c66">'+d.message+'</span>';b.classList.remove('disabled');b.textContent='RETRY'}
  }).catch(e=>{m.innerHTML='<span style="color:#c66">'+e+'</span>';b.classList.remove('disabled');b.textContent='RETRY'});
}
</script></body></html>"""


#── ANSI to HTML ──────────────────────────────────────────────────────────────

ANSI_COLORS = {
    "30": "#333", "31": "#c53030", "32": "#5a9c4f", "33": "#b45309",
    "34": "#3b82f6", "35": "#a855f7", "36": "#5a9c4f", "37": "#ccc",
    "90": "#555", "91": "#ef5350", "92": "#6fbf5f", "93": "#f59e0b",
    "94": "#60a5fa", "95": "#c084fc", "96": "#7fcf6f", "97": "#eee",
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


# ── Device status ─────────────────────────────────────────────────────────────

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


# ── HTML ──────────────────────────────────────────────────────────────────────

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
<title>AX12 TAC</title>
<link rel="icon" href="/icon.png" type="image/png">
<link rel="apple-touch-icon" href="/icon.png">
<link rel="manifest" href="/manifest.json">
<style>
*{margin:0;padding:0;box-sizing:border-box;-webkit-tap-highlight-color:transparent}
html,body{width:100%;height:100%;background:#0a0a0a;color:#e0e0e0;font-family:'Courier New',monospace;font-size:14px;overflow-x:hidden}

/* Header */
.hdr{background:#0f0f0f;padding:12px 16px;border-bottom:1px solid #1a3a1a;position:sticky;top:0;z-index:10}
.hdr-row{display:flex;justify-content:space-between;align-items:center}
.logo{font-size:13px;font-weight:700;color:#4a4;letter-spacing:3px}
.hdr-right{display:flex;align-items:center;gap:12px}
.stat{font-size:10px;color:#3a3;letter-spacing:1px}
.gear{font-size:16px;color:#3a3;cursor:pointer;padding:4px}
.gear:hover{color:#6d6}

/* Main content */
.wrap{padding:12px 12px 80px;max-width:480px;margin:0 auto}

/* Categories */
.cat{margin-bottom:14px}
.cat-hdr{font-size:10px;font-weight:700;color:#3a3;letter-spacing:2px;padding:4px 8px;margin-bottom:6px;border-left:2px solid #2a4a2a;background:rgba(42,74,42,0.1)}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:6px}

/* Buttons */
.btn{background:#111;border:1px solid #1a3a1a;color:#6c6;padding:14px 10px;border-radius:3px;font-family:inherit;font-size:12px;cursor:pointer;text-align:center;display:flex;flex-direction:column;align-items:center;gap:2px;min-height:52px;transition:background 0.1s,border-color 0.1s}
.btn:active{background:#1a3a1a;border-color:#3a6a3a}
.btn.disabled{opacity:0.3;pointer-events:none}
.btn-label{font-weight:700;letter-spacing:1px}
.btn-desc{font-size:9px;color:#3a3;letter-spacing:0.5px}

/* Toast notification for errors */
.toast{position:fixed;top:20px;left:50%;transform:translateX(-50%);background:#3a1a1a;border:1px solid #6a2a2a;color:#f88;padding:12px 20px;border-radius:4px;font-size:12px;z-index:200;display:none;max-width:90%;text-align:center;letter-spacing:0.5px}
.toast.visible{display:block;animation:fadeout 3s forwards}
@keyframes fadeout{0%,70%{opacity:1}100%{opacity:0}}

/* Loading spinner */
.loading{display:none;padding:40px;text-align:center;color:#3a3;font-size:11px;letter-spacing:2px}
.loading.active{display:block}
.loading::before{content:'';display:block;width:24px;height:24px;border:2px solid #1a3a1a;border-top-color:#4a4;border-radius:50%;margin:0 auto 12px;animation:spin 0.8s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}

/* Output view (full screen takeover) */
.output-view{display:none;position:fixed;top:0;left:0;right:0;bottom:0;background:#0a0a0a;z-index:100;flex-direction:column}
.output-view.active{display:flex}
.out-hdr{background:#0f0f0f;padding:12px 16px;border-bottom:1px solid #1a3a1a;display:flex;justify-content:space-between;align-items:center}
.out-title{font-size:12px;color:#4a4;letter-spacing:2px;font-weight:700}
.out-status{font-size:10px;padding:3px 8px;border-radius:2px;letter-spacing:1px}
.out-status.running{color:#4f4;background:rgba(79,255,79,0.1);border:1px solid #2a4a2a}
.out-status.done{color:#6c6;background:rgba(108,204,108,0.05);border:1px solid #1a3a1a}
.out-status.error{color:#c66;background:rgba(204,102,102,0.1);border:1px solid #4a2a2a}
.out-status.preflight-fail{color:#ca3;background:rgba(204,170,51,0.1);border:1px solid #4a3a1a}
.out-body{flex:1;overflow-y:auto;padding:10px 12px;font-size:11px;line-height:1.6;white-space:pre-wrap;word-break:break-all;color:#4a4}
.out-body .stderr{color:#ca3}
.out-buttons{padding:10px 12px;display:flex;gap:8px;background:#0f0f0f;border-top:1px solid #1a3a1a}
.out-btn{flex:1;padding:12px;border-radius:3px;font-family:inherit;font-size:12px;font-weight:700;letter-spacing:1px;cursor:pointer;text-align:center;border:1px solid}
.out-btn.stop{background:#2a1a1a;border-color:#4a2a2a;color:#c66}
.out-btn.stop:active{background:#3a2a2a}
.out-btn.stop.force{background:#4a1a1a;border-color:#6a2a2a;color:#f66}
.out-btn.back{background:#1a2a1a;border-color:#2a4a2a;color:#6c6}
.out-btn.back:active{background:#2a3a2a}

/* Settings view */
.settings-view{display:none;position:fixed;top:0;left:0;right:0;bottom:0;background:#0a0a0a;z-index:100;flex-direction:column}
.settings-view.active{display:flex}
.settings-body{flex:1;overflow-y:auto;padding:12px}
.settings-cat{margin-bottom:16px;background:#0f0f0f;border:1px solid #1a3a1a;border-radius:4px;padding:10px}
.settings-cat-name{font-size:11px;color:#3a3;letter-spacing:2px;font-weight:700;margin-bottom:8px}
.settings-tool{display:flex;align-items:center;gap:8px;padding:6px 0;border-bottom:1px solid #111}
.settings-tool:last-child{border-bottom:none}
.settings-tool-info{flex:1;font-size:11px;color:#6c6}
.settings-tool-cmd{font-size:9px;color:#333;margin-top:2px}
.settings-btn-sm{background:#111;border:1px solid #1a3a1a;color:#3a3;padding:4px 8px;border-radius:2px;font-family:inherit;font-size:10px;cursor:pointer}
.settings-btn-sm:active{background:#1a3a1a}
.settings-btn-sm.del{border-color:#3a1a1a;color:#a44}

/* Add tool form */
.add-form{background:#0f0f0f;border:1px solid #1a3a1a;border-radius:4px;padding:10px;margin-top:12px}
.add-form input,.add-form select{background:#111;border:1px solid #1a3a1a;color:#6c6;padding:6px 8px;font-family:inherit;font-size:11px;border-radius:2px;width:100%;margin-bottom:6px}
.add-form input::placeholder{color:#2a4a2a}
</style>
</head>
<body>

<!-- TOAST -->
<div class="toast" id="toast"></div>

<!-- MAIN VIEW -->
<div id="main-view">
  <div class="hdr">
    <div class="hdr-row">
      <div class="logo">AX12 TAC TOOLS</div>
      <div class="hdr-right">
        <div class="stat">{{BATT}} &bull; {{UPTIME}}</div>
        <div class="gear" onclick="location.href='/setup'" style="font-size:11px;letter-spacing:1px">SETUP</div>
        <div class="gear" onclick="showSettings()">&#9881;</div>
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
    <div class="out-title" id="out-title">TOOL</div>
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
    <div class="out-title">SETTINGS</div>
    <div class="out-status done" style="cursor:pointer" onclick="hideSettings()">CLOSE</div>
  </div>
  <div class="settings-body" id="settings-body"></div>
  <div class="out-buttons">
    <button class="out-btn back" onclick="saveSettings()">SAVE</button>
    <button class="out-btn back" onclick="hideSettings()">CANCEL</button>
  </div>
</div>

<script>
let pollTimer = null;
let outputIdx = 0;
let stopping = false;
let stopTime = 0;
let toolRunning = false;

function showToast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = 'toast';
  void t.offsetWidth; // force reflow for re-animation
  t.className = 'toast visible';
  setTimeout(() => { t.className = 'toast'; }, 3000);
}

function setButtonsDisabled(disabled) {
  document.querySelectorAll('.btn').forEach(b => {
    if (disabled) b.classList.add('disabled');
    else b.classList.remove('disabled');
  });
}

function runTool(shortcut) {
  if (toolRunning) {
    showToast('A tool is already running. Stop it first.');
    return;
  }

  const body = document.getElementById('out-body');
  const title = document.getElementById('out-title');
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
      status.textContent = data.preflight ? 'PRE-FLIGHT FAIL' : 'ERROR';
      status.className = 'out-status ' + (data.preflight ? 'preflight-fail' : 'error');
      body.innerHTML = '<div style="color:#ca3;white-space:pre-wrap">' + escHtml(data.error) + '</div>';
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
    status.textContent = 'ERROR';
    status.className = 'out-status error';
    body.innerHTML = '<div style="color:#c66">' + escHtml(String(e)) + '</div>';
    stopBtn.style.display = 'none';
  });
}

function pollOutput() {
  if (pollTimer) clearTimeout(pollTimer);
  fetch('/api/output?since=' + outputIdx)
    .then(r => r.json())
    .then(data => {
      const body = document.getElementById('out-body');
      const status = document.getElementById('out-status');
      const stopBtn = document.getElementById('stop-btn');
      const loading = document.getElementById('loading');

      // Hide loading spinner on first output
      if (data.lines && data.lines.length > 0) {
        loading.className = 'loading';
        for (const line of data.lines) {
          body.innerHTML += line;
        }
        body.scrollTop = body.scrollHeight;
      }
      outputIdx = data.index;

      if (data.done) {
        loading.className = 'loading';
        toolRunning = false;
        setButtonsDisabled(false);
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

      // Escalate to force kill after 3s
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
  // If tool is still running, stop it in the background
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

function showSettings() {
  fetch('/api/config').then(r => r.json()).then(renderSettings);
  document.getElementById('settings-view').classList.add('active');
}

function hideSettings() {
  document.getElementById('settings-view').classList.remove('active');
}

function renderSettings(config) {
  const body = document.getElementById('settings-body');
  window._settingsConfig = config;
  let html = '';
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
  html += '<button class="settings-btn-sm" onclick="addTool()">ADD</button>';
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

function saveSettings() {
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
</script>
</body>
</html>"""


# ── HTTP Server ───────────────────────────────────────────────────────────────

class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        sys.stderr.write("[%s] %s\n" % (self.log_date_time_string(), fmt % args))
        sys.stderr.flush()

    def _json(self, data, code=200):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

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
                        since = int(part.split("=")[1])
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
                "background_color": "#0a0a0a",
                "theme_color": "#0a0a0a",
                "icons": [{"src": "/icon.png", "sizes": "192x192", "type": "image/png"}]
            }
            self._json(manifest)

        else:
            self.send_error(404)

    def do_POST(self):
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

        else:
            self.send_error(404)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()


class ThreadedServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    port = PORT
    if len(sys.argv) > 1:
        for i, arg in enumerate(sys.argv[1:], 1):
            if arg == "--port" and i + 1 < len(sys.argv):
                port = int(sys.argv[i + 1])
            elif arg.startswith("--port="):
                port = int(arg.split("=")[1])

    # Check if another server is actively listening
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect(("127.0.0.1", port))
        sock.close()
        # Connection succeeded — something is already serving
        print(f"[tac-web] Port {port} already in use — server may already be running")
        sys.exit(0)
    except (ConnectionRefusedError, OSError):
        pass  # Nothing listening — safe to start

    server = ThreadedServer(("0.0.0.0", port), Handler)
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
