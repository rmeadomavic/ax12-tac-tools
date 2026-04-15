#!/data/data/com.termux/files/usr/bin/bash
# Shows current GPS fix from the MT6631 GNSS.
su 0 /data/data/com.termux/files/usr/bin/python3 ~/ax12-tac-tools/tools/gps_tool.py position
echo ""
echo "Press Enter to close."
read -r
