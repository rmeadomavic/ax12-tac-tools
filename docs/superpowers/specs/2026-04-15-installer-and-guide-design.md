# AX12 Tactical Tools — Installer & User Guide Design

**Date:** 2026-04-15
**Status:** Approved
**Audience:** Community AX12 owners (strangers on GitHub, no assumed context)

## Overview

Add a one-command installer, a TUI launcher, and a plain-language getting-started guide to the ax12-tac-tools repo. The goal is to take someone from "just bought an AX12" to "drone on the ATAK map" with minimal copy-paste and zero terminal expertise beyond pasting one line.

## User Journey

1. **Manual:** Install Termux APK from F-Droid or GitHub Releases (cannot be automated)
2. **One command in Termux:**
   ```
   pkg install -y curl && curl -sL https://raw.githubusercontent.com/rmeadomavic/ax12-tac-tools/main/install.sh | bash
   ```
3. **Installer** detects what's missing and handles everything (device setup + tool install)
4. **Done.** User types `tac` to open the launcher menu, or accesses Lua scripts through Flyshark's System Menu > Lua Scripts > Tools

Day-to-day usage after install:
- `tac` — open TUI menu
- `tac atak` — directly launch ATAK CoT bridge
- `tac mavlink` — directly launch MAVLink bridge
- `tac gps` — show GPS position
- Lua scripts accessible natively through Flyshark

## Component 1: install.sh

Single entry point. Idempotent (safe to re-run). Detects what's already installed and skips it. Lives in repo root so the curl-pipe one-liner works from GitHub raw.

### Phase 1 — Device Setup

Runs only inside Termux on Android. Exits with a clear error if run elsewhere.

Steps:
1. `pkg update && pkg upgrade -y`
2. Install packages: `python openssh git curl wget` — skip already-installed
3. Optionally install advanced packages: `binutils dtc strace` (prompted, default no)
4. Configure sshd auto-start via `~/.termux/boot/start-sshd.sh` if Termux:Boot is present
5. Start sshd if not running
6. Print SSH connection info (IP address, port 8022)
7. Prompt: "Install Tailscale for remote access? (y/N)" — if yes, print manual APK install instructions (cannot be scripted)

### Phase 2 — Tool Install

Steps:
1. `git clone https://github.com/rmeadomavic/ax12-tac-tools.git ~/ax12-tac-tools` — or `git -C ~/ax12-tac-tools pull` if already cloned
2. Copy all `lua/*.lua` files to `/storage/emulated/0/AX12LUA/SCRIPTS/TOOLS/` using `su 0 cp`
3. Add `tac` alias to `~/.bashrc`:
   ```bash
   alias tac='/data/data/com.termux/files/usr/bin/python3 ~/ax12-tac-tools/launcher.py'
   ```
   Uses the full Termux Python path for reliability across shell contexts (root, SSH, boot scripts).
4. Source `~/.bashrc` so the alias is immediately available
5. Run self-test: Python version check, Lua files in place, `/dev/ttyS0` exists
6. Print summary: what was installed, what was skipped, `tac` to start

### Design Decisions

- No interactive prompts during install except Tailscale and advanced packages — everything else auto-detects
- Script itself does not need root; escalates with `su 0` only for Lua file copy
- Colorized output with `[OK]` / `[SKIP]` / `[FAIL]` indicators
- If `git` is not yet installed (first-run bootstrap via curl-pipe), phase 1 installs it before phase 2 needs it
- If the repo was already cloned (re-run), does `git pull` to update, then re-copies Lua files

## Component 2: launcher.py

Curses-based TUI menu. Stdlib only (no external dependencies). Runs in Termux on the AX12's 720x1280 touchscreen.

### Categories and Items

```
TAK INTEGRATION
  ATAK CoT Bridge     — Stream drone position to ATAK map
  MAVLink Bridge       — Connect QGC/Mission Planner via ELRS
  CoT Test Send        — Send one test blip to verify ATAK

FLIGHT OPS
  Airspace Brief       — Pre-flight airspace restriction check
  Payload Drop Calc    — Aerial drop point calculator
  Rover Navigation     — ArduRover GPS nav and geofencing
  GPS Position         — Current GPS fix from MT6631

SENSORS
  IMU Tracker          — ICM-42607 head tracking
  GPS Monitor          — Continuous GPS with NMEA/satellite info
  Hydra AI Display     — Object detection telemetry client

SYSTEM
  Update Tools         — git pull + re-copy Lua scripts
  Reinstall Lua        — Re-copy Lua scripts to Flyshark
  About                — Version, repo URL, credits
```

### Interaction Model

- Arrow keys to navigate, Enter to launch
- Touch support via curses touch events (if terminal supports it)
- Each item shows a one-line description on the status bar before launch
- Tools requiring root auto-prepend `su 0`
- Tool output streams directly in the terminal
- Press any key to return to menu after tool exits
- `q` or Ctrl+C to quit

### Direct Launch Shortcuts

The launcher accepts a subcommand argument for direct launch without the menu:

| Shortcut | Launches |
|----------|----------|
| `tac atak` | `su 0 python3 tools/cot_bridge.py` |
| `tac mavlink` | `python3 tools/mavlink_bridge.py bridge` |
| `tac cot-test` | `python3 tools/test_cot.py` |
| `tac airspace` | `su 0 python3 tools/airspace_check.py brief` |
| `tac drop` | `su 0 python3 tools/payload_drop.py calc` |
| `tac rover` | `python3 tools/rover_nav.py --demo` |
| `tac gps` | `su 0 python3 tools/gps_tool.py position` |
| `tac imu` | `su 0 python3 tools/imu_tracker.py` |
| `tac gps-mon` | `su 0 python3 tools/gps_position.py` |
| `tac hydra` | `python3 tools/hydra_display.py demo` |
| `tac update` | `git pull` + re-copy Lua |
| `tac lua` | Re-copy Lua scripts only |

Unknown subcommands print the help/shortcut list.

### Design Decisions

- No web server. TUI runs in Termux directly — less infrastructure, no port conflicts, works offline
- Modeled on the existing `launcher_tui.py` in ax12-research but scoped to tac-tools only
- All paths are relative to `~/ax12-tac-tools/`
- The `SYSTEM > Update` action runs `git pull` then re-copies Lua files, so the user never needs to remember the update process

## Component 3: GETTING_STARTED.md

Lives in repo root. Written for someone who just bought an AX12 and has never used a terminal. Tone: friendly, direct, no jargon without explanation.

### Structure

1. **What is this?** — 3 sentences. Your AX12 is a tactical computer. These tools unlock drone tracking on ATAK, mission planning, GPS tools, and 20+ Lua scripts for the touchscreen. One install command, then you're operational.

2. **What you need** — AX12, WiFi network, ~30 minutes.

3. **Step 1: Install Termux** — F-Droid link, GitHub Releases link. Explicit: do NOT use Google Play version. Brief ADB sideload alternative for users with a computer.

4. **Step 2: Run the installer** — The one-liner. What to expect (package installs, progress indicators, completion summary). Mention it's safe to re-run.

5. **Step 3: Try it out** — Type `tac`, pick "CoT Test Send" to verify the launcher works. Show expected output.

6. **TAK Integration Guide** (dedicated section, this is the headline feature):
   - What ATAK is and why it matters (one paragraph)
   - Install ATAK on the AX12 (APK source, install command)
   - Configure ATAK: open Settings > Network Preferences > add UDP input on port 4242
   - Run the bridge: `tac atak` or menu > TAK Integration > ATAK CoT Bridge
   - What you should see: a blue drone icon labeled "ELRS-Drone-1" on the map
   - For live drone telemetry: link to `docs/mavlink-setup.md` (ELRS MAVLink mode + FC parameters)
   - Troubleshooting: no icon appears, icon appears but doesn't move, "serial port busy"

7. **Lua Scripts** — How to find them in Flyshark (System Menu > Lua Scripts > Tools). Brief table of highlights (tak-osd, ccip, nineline, preflight). Note they're auto-installed by the installer.

8. **Updating** — `tac update` from the menu, or `tac update` from the command line. That's it.

9. **Troubleshooting** — Common issues: no root (`su 0 id` to verify), serial port busy (stop Flyshark first or use strace), GPS no fix (outdoor + wait 60s), Termux crashes (update packages).

10. **Deep Dive** — Links to ax12-research repo for rooting guide, hardware teardown, UMBUS protocol, and advanced tooling.

## Component 4: docs/tak-setup.md

Dedicated TAK/ATAK integration guide, separate from the getting-started doc. For users who want the full picture.

### Contents

1. Architecture diagram: Vehicle → ELRS → AX12 → CoT Bridge → ATAK
2. ATAK installation on AX12 (APK options: CivTAK from tak.gov, ATAK-CIV from Play Store)
3. ATAK network configuration (UDP input, multicast options)
4. CoT bridge configuration (serial port, baud rate, UID, interval, CoT type)
5. MAVLink bridge for QGC (link to existing `mavlink-setup.md`)
6. Multi-device setup: AX12 as bridge, ATAK on a phone/tablet on same network
7. Custom callsigns and CoT types
8. TAK OSD Lua script: what it shows, how to customize

## File Layout (New Files Only)

```
ax12-tac-tools/
├── install.sh                # Bootstrap installer (curl-pipe entry point)
├── launcher.py               # TUI menu launcher
├── GETTING_STARTED.md        # Plain-language guide for new users
└── docs/
    └── tak-setup.md          # Dedicated TAK/ATAK integration guide
```

No changes to existing files. The installer and launcher reference existing tools in `tools/`, `lua/`, and `scripts/` by path.

## Out of Scope

- Magisk / persistent root (documented in ax12-research, not this repo's problem)
- ATAK APK distribution (legal/licensing — guide links to official sources)
- Web-based launcher (TUI is sufficient; web launcher exists in ax12-research for those who want it)
- Claude Code installation on the AX12 (covered in ax12-research root guide)
- Automated Tailscale installation (requires manual APK install + OAuth sign-in)
