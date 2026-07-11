# Changelog

All notable changes to **AX12 Tactical Tools** are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Repository baseline scaffolding (SECURITY.md, ISSUE_TEMPLATE forms, dependabot config, pre-commit hooks).
- `tools/cot_bridge.py` now decodes SYS_STATUS (msg 1) and shows aircraft pack voltage on the CoT track.
- `tests/test_cot_bridge.py`: stdlib unit tests for the MAVLink parse-to-CoT path (GLOBAL_POSITION_INT, HEARTBEAT, SYS_STATUS, bad-CRC rejection, CoT XML). Wired into CI.
- `boot/start-cot-bridge.sh`: opt-in Termux:Boot hook to auto-start the bridge on power-up.

### Changed
- Corrected all operator-self-position GPS claims to match verified hardware: the AX12 has no GNSS antenna populated, so `gps_tool.py`/`gps_position.py` return WiFi/network location only, never a satellite fix. Renamed launcher entries ("GPS Position" → "Net Location", "GPS Monitor" → "GNSS Diag") in `launcher.py`, `tools.json`, README, GETTING_STARTED, and CLAUDE.md. Drone-telemetry GPS (CRSF/MAVLink, Lua OSD) is unaffected.
- Reorganized the launcher around a BRIDGE category (CoT Bridge, ATAK Test, MAVLink GCS) shown first in `tools.json`, `launcher.py`, and the web UI; non-bridge tools demoted below. Shortcut keys unchanged.
- README now leads with the CoT bridge (what it does, how to run/test/auto-start it) and drops the exhaustive per-tool tables for a short "also in here" list.

### Removed
- **Collapse to the CoT bridge.** Removed the entire `lua/` touchscreen suite and the non-bridge Python tools (`gps_tool.py`, `payload_drop.py`, `rover_nav.py`, `airspace_check.py`), and de-registered them everywhere they were referenced (`tools.json`, `launcher.py`, `web_launcher.py`, `install.sh`, `shortcuts/`, `docs/`, and CI). The repo is now strictly the AX12→COP bridge: CoT bridge, ATAK test, MAVLink GCS, and the GNSS diagnostic.
- Three dead Lua scripts that need hardware the AX12 lacks: `mgrs-tool.lua` and `site-manager.lua` (both require the operator's own GNSS fix; no GPS antenna is populated) and `g-force.lua` (accelerometer driver is broken in stock firmware). De-registered from `lua/README.md` and `GETTING_STARTED.md`.

### Fixed
- `docs/tak-setup.md`: removed the `a-f-G-U-C` "pilot position" CoT type row — that marker is not implemented and would require operator GPS the radio lacks. `cot_bridge.py` emits only the vehicle track.

### Security
- Enabled GitHub Dependabot vulnerability alerts and automated security update PRs.
- Enabled GitHub secret scanning + push protection.

[Unreleased]: https://github.com/rmeadomavic/ax12-tac-tools/commits/main
