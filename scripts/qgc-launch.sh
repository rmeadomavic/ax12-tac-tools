#!/data/data/com.termux/files/usr/bin/bash
# QGroundControl + MAVLink Bridge Launcher for the AX12.
# Starts the bridge detached (survives launcher teardown), relaxes
# /dev/ttyS1 perms for the serial path, then opens QGC.

PY=/data/data/com.termux/files/usr/bin/python3
BRIDGE=$HOME/ax12-tac-tools/tools/mavlink_bridge.py
LOGDIR=$HOME/.ax12-logs
mkdir -p "$LOGDIR"
BRIDGE_LOG=$LOGDIR/mavlink_bridge.log
BRIDGE_PID=$LOGDIR/mavlink_bridge.pid

QGC_PKG=org.mavlink.qgroundcontrol
QGC_ACT=$QGC_PKG/$QGC_PKG.QGCActivity

echo "================================================"
echo "  QGroundControl + MAVLink Bridge"
echo "================================================"

echo
echo "[1/3] MAVLink bridge (UDP 14550 <-> TCP 5760)..."
port_in_use() { (exec 3<>/dev/tcp/127.0.0.1/5760) 2>/dev/null && return 0 || return 1; }

if port_in_use; then
    echo "  TCP 5760 already bound -- assuming bridge is running"
elif [ -f "$BRIDGE_PID" ] && kill -0 "$(cat $BRIDGE_PID)" 2>/dev/null; then
    echo "  Bridge already running (PID $(cat $BRIDGE_PID))"
else
    nohup $PY $BRIDGE bridge > "$BRIDGE_LOG" 2>&1 &
    echo $! > "$BRIDGE_PID"
    disown 2>/dev/null || true
    sleep 1
    if kill -0 "$(cat $BRIDGE_PID)" 2>/dev/null; then
        echo "  Started (PID $(cat $BRIDGE_PID)), log: $BRIDGE_LOG"
    else
        echo "  FAIL -- check $BRIDGE_LOG"
        exit 1
    fi
fi

echo
echo "[2/3] /dev/ttyS1 permissions..."
if [ -e /dev/ttyS1 ]; then
    if su 0 chmod 666 /dev/ttyS1 2>/dev/null; then
        echo "  /dev/ttyS1 -> 666 (serial path available)"
    else
        echo "  /dev/ttyS1 present, chmod skipped (no root)"
    fi
else
    echo "  /dev/ttyS1 not present on this device"
fi

echo
echo "[3/3] Launching QGroundControl..."
if su 0 pm list packages 2>/dev/null | grep -qx "package:$QGC_PKG"; then
    if su 0 am start -n "$QGC_ACT" >/dev/null 2>&1; then
        echo "  QGC launched"
    elif am start -n "$QGC_ACT" >/dev/null 2>&1; then
        echo "  QGC launched (no root)"
    else
        echo "  FAIL: am start refused the activity"
        exit 2
    fi
else
    echo "  QGC is not installed."
    echo "  APK: github.com/Radiomaster-RC/qgroundcontrol (release v5.0.8+)"
    exit 3
fi

echo
echo "------------------------------------------------"
echo "  In QGC: Application Settings -> Comm Links -> Add"
echo "    TCP    host 127.0.0.1   port 5760    (via bridge)"
echo "    Serial /dev/ttyS1       460800        (direct)"
echo
echo "  Control the vehicle from QGC's Fly view:"
echo "    - slide-to-arm"
echo "    - mode dropdown (LOITER / GUIDED / AUTO / RTL)"
echo "    - takeoff / land / RTL from action menu"
echo "    - long-press map in GUIDED to fly there"
echo "    - Plan view for waypoint missions"
echo
echo "  Stop bridge: kill \$(cat $BRIDGE_PID)"
echo "================================================"
