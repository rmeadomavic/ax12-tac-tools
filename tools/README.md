# AX12 Tactical Tools — Python

Python tools for tactical UxS operations. Stdlib only, runs under Termux. Most require root (`su 0`).

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
