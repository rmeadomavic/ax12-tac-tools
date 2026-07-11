#!/data/data/com.termux/files/usr/bin/bash
# Shows the AX12 network/WiFi location (no GNSS antenna - not a satellite fix).
su 0 /data/data/com.termux/files/usr/bin/python3 ~/ax12-tac-tools/tools/gps_tool.py position
echo ""
echo "Press Enter to close."
read -r
