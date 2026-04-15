#!/data/data/com.termux/files/usr/bin/bash
# Pre-flight airspace restriction check.
su 0 /data/data/com.termux/files/usr/bin/python3 ~/ax12-tac-tools/tools/airspace_check.py brief
echo ""
echo "Press Enter to close."
read -r
