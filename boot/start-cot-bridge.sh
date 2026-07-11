#!/data/data/com.termux/files/usr/bin/bash
# Opt-in Termux:Boot hook. Auto-starts the AX12 CoT bridge on power-up.
#
# Install:
#   mkdir -p ~/.termux/boot
#   cp ~/ax12-tac-tools/boot/start-cot-bridge.sh ~/.termux/boot/
#   chmod +x ~/.termux/boot/start-cot-bridge.sh
#
# Needs the Termux:Boot app (F-Droid) and root for /dev/ttyS1. Delete the copy
# in ~/.termux/boot to turn it off. Output lands in the log path below.

LOG="$HOME/cot-bridge-boot.log"
PYTHON3="/data/data/com.termux/files/usr/bin/python3"
BRIDGE="$HOME/ax12-tac-tools/tools/cot_bridge.py"

# Keep the CPU awake after the screen locks so the bridge keeps publishing.
termux-wake-lock

echo "[$(date)] starting cot_bridge" >> "$LOG"
exec su 0 "$PYTHON3" "$BRIDGE" >> "$LOG" 2>&1
