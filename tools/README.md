# AX12 Tactical Tools — Python

Stdlib only, runs under Termux. Most require root (`su 0`).

## Core — flight kit

| Tool | Purpose | Usage |
|------|---------|-------|
| `cot_bridge.py` | MAVLink-to-CoT bridge for ATAK. The main one. | `su 0 python3 tools/cot_bridge.py` |
| `test_cot.py` | First-run check: does ATAK see you? | `python3 tools/test_cot.py` |

## Extras — dev, diagnostics, platform-specific

| Tool | Purpose | Usage |
|------|---------|-------|
| `mavlink_bridge.py` | Expose MAVLink to a laptop GCS (QGC, Mission Planner). Tuning/bench. | `python3 tools/mavlink_bridge.py bridge` |
| `gps_position.py` | GNSS diagnostic — confirms zero satellites (no antenna). Diagnostic. | `su 0 python3 tools/gps_position.py` |
