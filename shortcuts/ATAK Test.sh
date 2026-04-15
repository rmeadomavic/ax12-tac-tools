#!/data/data/com.termux/files/usr/bin/bash
# Sends a single test blip to ATAK to verify the connection.
/data/data/com.termux/files/usr/bin/python3 ~/ax12-tac-tools/tools/test_cot.py
echo ""
echo "Check ATAK for ELRS-Drone-1 at 0,0."
echo "Press Enter to close."
read -r
