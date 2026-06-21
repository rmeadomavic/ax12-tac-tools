# Changelog

All notable changes to **AX12 Tactical Tools** are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Repository baseline scaffolding (SECURITY.md, ISSUE_TEMPLATE forms, dependabot config, pre-commit hooks).

### Changed
- Corrected all operator-self-position GPS claims to match verified hardware: the AX12 has no GNSS antenna populated, so `gps_tool.py`/`gps_position.py` return WiFi/network location only, never a satellite fix. Renamed launcher entries ("GPS Position" → "Net Location", "GPS Monitor" → "GNSS Diag") in `launcher.py`, `tools.json`, README, GETTING_STARTED, and CLAUDE.md. Drone-telemetry GPS (CRSF/MAVLink, Lua OSD) is unaffected.

### Fixed
- `docs/tak-setup.md`: removed the `a-f-G-U-C` "pilot position" CoT type row — that marker is not implemented and would require operator GPS the radio lacks. `cot_bridge.py` emits only the vehicle track.

### Security
- Enabled GitHub Dependabot vulnerability alerts and automated security update PRs.
- Enabled GitHub secret scanning + push protection.

[Unreleased]: https://github.com/rmeadomavic/ax12-tac-tools/commits/main
