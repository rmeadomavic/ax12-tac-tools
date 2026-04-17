# AX12 Tactical Tools

Your AX12 runs Android. These tools turn it into a TAK endpoint. The CoT bridge pulls MAVLink telemetry off ELRS and puts your drone on the COP while you fly it. No second device in the loop.

There's also a TAK OSD for the touchscreen, CCIP, 9-line CAS template, freq decon, mission timer, and preflight checklist. Everything runs on-device in Termux. No pip, no npm, no dependencies beyond what ships with Python.

## Install

Open Termux, paste this:

```
pkg install -y curl && curl -sL https://raw.githubusercontent.com/rmeadomavic/ax12-tac-tools/main/install.sh | bash
```

After that, open `localhost:8080` in Chrome. Bookmark it to your home screen. It acts like an app. The server starts on boot if you have Termux:Boot installed.

Setup walkthrough: [GETTING_STARTED.md](GETTING_STARTED.md)

![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)
![Python 3.13](https://img.shields.io/badge/python-3.13-yellow.svg)
![Platform: Android 9](https://img.shields.io/badge/platform-Android%209-green.svg)

## What's in Here

```
tools/           Python tools (CoT bridge, MAVLink bridge, GPS, airspace, etc.)
lua/             Lua scripts for the Flyshark touchscreen UI
shortcuts/       Termux:Widget home screen shortcuts
web_launcher.py  The web UI server
launcher.py      CLI/TUI launcher (for SSH use)
install.sh       One-command installer
tools.json       Tool registry (edit to add/remove/reorder tools)
```

### Python Tools

| Tool | What it does |
|------|-------------|
| `cot_bridge.py` | MAVLink → CoT for ATAK. The main one. |
| `mavlink_bridge.py` | ELRS Backpack WiFi → TCP for QGC/Mission Planner |
| `test_cot.py` | Sends a single CoT blip to verify ATAK is listening |
| `airspace_check.py` | Offline airspace restriction briefing |
| `payload_drop.py` | Drop point calculator |
| `gps_tool.py` | GPS position from the MT6631 |
| `gps_position.py` | Continuous GPS with NMEA and satellite info |
| `rover_nav.py` | ArduRover GPS nav and geofencing |
| `imu_tracker.py` | ICM-42607 head tracking |
| `hydra_display.py` | AI detection telemetry client (Hydra project) |

### Lua Scripts (Touchscreen)

Installed automatically to Flyshark. Access: System Menu > Lua Scripts > Tools.

**Tactical:** TAK OSD, CCIP targeting, 9-line CAS, MGRS converter, mission timer, preflight checklist, freq decon

**Flight Ops:** Fixed-wing helper, wind calc, Betaflight OSD, compass, training exercises, g-force, servo test

**Field Utility:** Battery log, flight log, channel notes, motor test, site manager, unit converter, stopwatch

## Prerequisites

- RadioMaster AX12 (stock firmware; root is built in)
- Termux (installer handles the rest)
- ELRS 3.5+ for MAVLink
- ATAK-CIV **4.10.x** (5.x needs Android 10+, won't install on the AX12)

## Related

Protocol research, hardware teardown, UMBUS tooling: [ax12-research](https://github.com/rmeadomavic/ax12-research)

## License

[MIT](LICENSE)
