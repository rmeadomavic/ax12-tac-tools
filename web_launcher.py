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

PORT = 8080
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
        if force:
            os.killpg(pgid, signal.SIGKILL)
            return True, "Force killed."
        else:
            os.killpg(pgid, signal.SIGTERM)
            return True, "Stop signal sent."
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


# ── ANSI to HTML ──────────────────────────────────────────────────────────────

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
.btn-label{font-weight:700;letter-spacing:1px}
.btn-desc{font-size:9px;color:#3a3;letter-spacing:0.5px}

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

<!-- MAIN VIEW -->
<div id="main-view">
  <div class="hdr">
    <div class="hdr-row">
      <div class="logo">AX12 TAC TOOLS</div>
      <div class="hdr-right">
        <div class="stat">{{BATT}} &bull; {{UPTIME}}</div>
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
  <div class="out-body" id="out-body"></div>
  <div class="out-buttons">
    <button class="out-btn stop" id="stop-btn" onclick="stopTool()">STOP</button>
    <button class="out-btn back" onclick="goBack()">BACK</button>
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
let forceTimer = null;

function runTool(shortcut) {
  const body = document.getElementById('out-body');
  const title = document.getElementById('out-title');
  const status = document.getElementById('out-status');
  const stopBtn = document.getElementById('stop-btn');

  body.innerHTML = '';
  outputIdx = 0;
  stopping = false;
  stopBtn.textContent = 'STOP';
  stopBtn.className = 'out-btn stop';
  title.textContent = shortcut.toUpperCase();
  status.textContent = 'STARTING';
  status.className = 'out-status running';

  document.getElementById('output-view').classList.add('active');

  fetch('/api/run', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({shortcut: shortcut})
  })
  .then(r => r.json())
  .then(data => {
    if (!data.ok) {
      status.textContent = data.preflight ? 'PRE-FLIGHT FAIL' : 'ERROR';
      status.className = 'out-status ' + (data.preflight ? 'preflight-fail' : 'error');
      body.innerHTML = '<div style="color:#ca3">' + escHtml(data.error) + '</div>';
      stopBtn.style.display = 'none';
      return;
    }
    title.textContent = data.label || shortcut.toUpperCase();
    status.textContent = 'RUNNING';
    stopBtn.style.display = '';
    pollOutput();
  })
  .catch(e => {
    status.textContent = 'ERROR';
    status.className = 'out-status error';
    body.innerHTML = '<div style="color:#c66">' + escHtml(String(e)) + '</div>';
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

      if (data.lines && data.lines.length > 0) {
        for (const line of data.lines) {
          body.innerHTML += line;
        }
        body.scrollTop = body.scrollHeight;
      }
      outputIdx = data.index;

      if (data.done) {
        if (data.exit_code === 0) {
          status.textContent = 'DONE';
          status.className = 'out-status done';
        } else {
          status.textContent = 'EXIT ' + data.exit_code;
          status.className = 'out-status error';
        }
        stopBtn.style.display = 'none';
        if (forceTimer) clearTimeout(forceTimer);
        return;
      }

      // Check if stop was requested and escalate to force kill
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
  if (forceTimer) clearTimeout(forceTimer);
  document.getElementById('output-view').classList.remove('active');
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
        pass  # suppress access logs

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

    # Check if port is already in use
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", port))
        sock.close()
    except OSError:
        print(f"[tac-web] Port {port} already in use — server may already be running")
        sys.exit(0)

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
