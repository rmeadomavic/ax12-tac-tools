# AX12 Tactical Tools

Operational UxS tools for the RadioMaster AX12.

## Device
- Android 9, MediaTek MT8788 SoC, ELRS LR1121 RF module
- ELRS Backpack WiFi for MAVLink at 10.0.0.1:14550
- Root access via `su 0` (factory userdebug build)
- GPS via MT6631 GNSS chipset
- IMU: ICM-42607 (driver broken in current firmware)

## Repo
- Published at github.com/rmeadomavic/ax12-tac-tools, branch `main`
- Structure: `tools/` (Python), `lua/` (Lua scripts), `scripts/` (shell), `docs/`
- Related: github.com/rmeadomavic/ax12-research (protocol research, hardware docs)
- Native `.so` and `.apk` files are gitignored

## Development Rules
- All Python scripts require root: `su 0 python3 script.py`
- Python tools use stdlib only — no external dependencies
- Lua scripts follow EdgeTX convention: `-- TNS|Name|TNE` header, `return { init=init, run=run }`
- Lua install path: `/storage/emulated/0/AX12LUA/SCRIPTS/TOOLS/`
- Preserve existing code patterns when editing tools
