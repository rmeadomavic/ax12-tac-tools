# AX12 Tactical Tools

Operational UxS tools for the RadioMaster AX12. Python stdlib only, Lua scripts for the Flyshark VM, runs on-device in Termux. No external dependencies.

![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)
![Python 3.13](https://img.shields.io/badge/python-3.13-yellow.svg)
![Platform: Android 9](https://img.shields.io/badge/platform-Android%209-green.svg)

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│  RadioMaster AX12  (Android 9 / Termux)                  │
│                                                          │
│  tools/                    lua/                          │
│  ├─ mavlink_bridge.py      ├─ tak-osd.lua    (HUD)      │
│  ├─ cot_bridge.py          ├─ ccip.lua       (targeting) │
│  ├─ hydra_display.py       ├─ nineline.lua   (CAS)      │
│  ├─ airspace_check.py      ├─ mgrs-tool.lua  (coords)   │
│  ├─ payload_drop.py        ├─ preflight.lua  (checklist) │
│  └─ ...                    └─ ...                        │
└────────┬──────────────────────────┬──────────────────────┘
         │                          │
    ELRS Backpack WiFi         Flyshark Lua VM
    UDP 14550 ↔ TCP 5760       720×1280 touchscreen
         │                          │
    ┌────▼────┐               ┌─────▼─────┐
    │ Vehicle │               │  On-screen │
    │ MAVLink │               │  widgets   │
    └────┬────┘               └───────────┘
         │
    ┌────▼────┐
    │  ATAK   │
    │  (CoT)  │
    └─────────┘
```

## Quick Start

```bash
su 0 python3 tools/cot_bridge.py --test          # ATAK CoT bridge (synthetic data)
su 0 python3 tools/mavlink_bridge.py test         # MAVLink bridge (synthetic data)
su 0 python3 tools/airspace_check.py brief        # pre-flight airspace brief
su 0 python3 tools/gps_tool.py position           # current GPS position
```

## Tools

| Tool | Purpose | Usage |
|------|---------|-------|
| `cot_bridge.py` | MAVLink-to-CoT bridge for ATAK | `su 0 python3 tools/cot_bridge.py` |
| `test_cot.py` | CoT test sender | `python3 tools/test_cot.py` |
| `mavlink_bridge.py` | QGC/Mission Planner bridge via ELRS Backpack | `python3 tools/mavlink_bridge.py bridge` |
| `hydra_display.py` | AI object detection telemetry client | `python3 tools/hydra_display.py demo` |
| `airspace_check.py` | Offline airspace restriction briefing | `python3 tools/airspace_check.py brief` |
| `payload_drop.py` | Aerial drop point calculator | `python3 tools/payload_drop.py calc --alt 50 --speed 10` |
| `rover_nav.py` | ArduRover GPS navigation and geofencing | `python3 tools/rover_nav.py --demo` |
| `imu_tracker.py` | ICM-42607 IMU head tracking | `su 0 python3 tools/imu_tracker.py` |
| `gps_tool.py` | GPS position from MT6631 GNSS | `su 0 python3 tools/gps_tool.py position` |
| `gps_position.py` | GPS display with NMEA and satellite info | `su 0 python3 tools/gps_position.py` |

## Lua Scripts

Copy `.lua` files to `/storage/emulated/0/AX12LUA/SCRIPTS/TOOLS/` on the device. Access via RadioMaster App > System Menu > Lua Scripts > Tools.

### Tactical

| Script | Description |
|--------|-------------|
| **tak-osd** | TAK-style HUD — GPS, MGRS, compass, RSSI/LQ, mission timer |
| **ccip** | Impact point targeting — physics model, range rings, drift vector, RELEASE cue |
| **nineline** | 9-Line CAS brief template — auto-fills target elevation and grid from GPS |
| **mgrs-tool** | MGRS coordinate converter — WGS84 to UTM/MGRS, waypoint save, distance/bearing |
| **mission-timer** | 6-phase timer — STARTUP / LAUNCH / TRANSIT / ON STATION / RTB / RECOVERY |
| **preflight** | 12-item pre-flight checklist — telemetry auto-check, GO/NO-GO |
| **freq-decon** | RF frequency deconfliction — 900/2400/5800 MHz bands, conflict detection |

### Flight Ops

| Script | Description |
|--------|-------------|
| **fw-helper** | Fixed-wing helper — approach calc, stall speed, bank angle, wind triangle |
| **wind-calc** | Wind component calculator — headwind/crosswind, Beaufort scale, GO/NO-GO |
| **bf-osd** | Betaflight OSD — artificial horizon, compass tape, battery, military style toggle |
| **compass** | Compass rose with attitude indicator |
| **training** | 6 flight exercises — HOVER, BOX, FIGURE 8, ORBIT, SPEED RUN, LANDING |
| **g-force** | G-force and attitude display from accelerometer |
| **servo-test** | Servo/motor output tester for ArduPilot |

### Field Utility

| Script | Description |
|--------|-------------|
| **battery-log** | TX battery voltage tracking — graph, CSV logging, discharge rate |
| **flight-log** | Flight logging with JSON persistence |
| **ch-notes** | Channel label editor |
| **motor-test** | Motor/ESC test display |
| **site-manager** | Flying site database — GPS save, distance/bearing |
| **unit-conv** | Unit converter — speed, distance, altitude, temp, weight, pressure |
| **stopwatch** | Stopwatch with lap timing |

## Prerequisites

- RadioMaster AX12 with root access (factory userdebug build)
- Termux with Python 3.10+
- ELRS firmware 3.5+ for MAVLink link mode
- ATAK for CoT integration (optional)

## Related

Protocol research, hardware docs, and UMBUS tooling: [ax12-research](https://github.com/rmeadomavic/ax12-research)

## License

[MIT](LICENSE)
