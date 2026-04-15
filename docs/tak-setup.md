# TAK Integration Guide

End-to-end guide for streaming vehicle position to ATAK/CivTAK and displaying a
TAK-style HUD on the AX12 touchscreen. For a quick overview see the main README;
this document covers every option in depth.

---

## Architecture

```
Vehicle --RF--> ELRS TX module --> /dev/ttyS1 --> cot_bridge.py --> ATAK (UDP :4242)
                               \-> Backpack WiFi (UDP :14550) --> mavlink_bridge.py --> QGC (TCP :5760)
```

Two independent data paths run in parallel:

**Serial path — CoT/ATAK**
ELRS MAVLink passthrough delivers raw MAVLink v1/v2 frames from the vehicle
directly to `/dev/ttyS1` at 460800 baud. `cot_bridge.py` reads those frames,
decodes `GLOBAL_POSITION_INT` and `HEARTBEAT`, and emits Cursor-on-Target (CoT)
XML datagrams to ATAK over UDP. No GCS software is involved; the AX12 itself
acts as the CoT injector.

**WiFi path — QGC/Mission Planner**
The ELRS TX Backpack creates a WiFi AP (`10.0.0.1`) and forwards the same
MAVLink stream over UDP on port 14550. `mavlink_bridge.py` connects to that
UDP stream and re-serves it as a TCP server on port 5760 for QGroundControl
or Mission Planner on a laptop. These two paths can run simultaneously —
use serial for CoT and WiFi for GCS without conflict.

---

## Installing ATAK

### Option 1: CivTAK from tak.gov (recommended)

Register for a free account at `tak.gov`, download the CivTAK APK, and
sideload it onto the AX12.

```bash
adb connect <AX12-IP>:5555
adb install ATAK-CIV-*.apk
```

CivTAK is the civilian-licensed version of ATAK with full map and CoT support.
Registration is free and unlocks the full feature set.

### Option 2: ATAK-CIV from Google Play Store

Search for **ATAK-CIV** in the Play Store. The AX12 ships without Google Play
Services so this option may require installing the Play Store framework first.
Use Option 1 or Option 3 if Play Store is unavailable.

### Option 3: Sideload via ADB

If you already have the APK (from tak.gov or a team distribution):

```bash
adb connect <AX12-IP>:5555 && adb install ATAK-CIV-*.apk
```

Enable ADB over TCP on the AX12 first:

```bash
su 0 setprop service.adb.tcp.port 5555
su 0 stop adbd && su 0 start adbd
```

---

## Configuring ATAK

### Add a UDP network input

1. Open ATAK on the AX12
2. Tap the hamburger menu (top-left) > **Settings**
3. Navigate to **Network Preferences** > **Network Connections**
4. Tap the **+** button to add a new input
5. Set:
   - **Type:** Input
   - **Protocol:** UDP
   - **Address:** `0.0.0.0` (listen on all interfaces)
   - **Port:** `4242`
   - **Description:** `AX12 CoT Bridge`
6. Tap **OK** and confirm the input appears as active (green indicator)

ATAK will now accept CoT datagrams sent to any local address on port 4242.

### Optional: offline map data

ATAK defaults to online tile servers. For field use without internet:

1. Download an MBTiles or DTED file for your area of operations
2. Copy to `/sdcard/atak/imagery/` on the AX12
3. In ATAK: Settings > Maps > Offline Map Catalog — select your tile package

---

## Running the CoT Bridge

### Test mode (no vehicle required)

Tap **COT TEST** in the web launcher, or from the command line:

```bash
tac cot-test
```

For a continuous moving track (synthetic drone orbiting Null Island):

```bash
tac atak
# falls back to synthetic data automatically if no serial connection
```

The synthetic source orbits `(0, 0)` — Null Island — at 100 m altitude. Open
ATAK and zoom to 0°N 0°E to confirm the icon appears and moves.

### Live mode prerequisites

Before running live, verify:

| Requirement | Check |
|-------------|-------|
| ELRS firmware | TX and RX both on **3.5.0 or later** |
| RX hardware | Must be **ESP-based** (RP1/RP2/RP3, EP1/EP2, BetaFPV Nano) |
| ELRS link mode | Set to **MAVLink** in the ELRS Lua script |
| FC UART | `SERIALn_PROTOCOL = 2` (MAVLink 2), `SERIALn_BAUD = 460` |
| FC reboot | Required after changing serial protocol |
| RX power cycle | Required after changing ELRS link mode |

See `docs/mavlink-setup.md` for full ArduPilot parameter configuration.

### Launch (live)

Tap **ATAK BRIDGE** in the web launcher (`http://localhost:8080`), or from
the command line:

```bash
tac atak
```

Root is required for serial port access. If the serial port cannot be opened,
the bridge automatically falls back to synthetic data and prints a warning.

### Configuration options

| Flag | Default | Description |
|------|---------|-------------|
| `--port` | `/dev/ttyS1` | Serial port to read MAVLink from |
| `--baud` | `460800` | Serial baud rate |
| `--atak-host` | `127.0.0.1` | ATAK UDP destination address |
| `--atak-port` | `4242` | ATAK UDP destination port |
| `--uid` | `ELRS-Drone-1` | CoT UID and callsign displayed in ATAK |
| `--interval` | `2.0` | Seconds between CoT transmissions |
| `--test` | off | Use synthetic data instead of serial |

Example — custom callsign, 1-second updates:

```bash
su 0 python3 tools/cot_bridge.py --uid AlphaActual --interval 1.0
```

---

## Multi-device Setup

### Same WiFi network — target a specific device

If ATAK is running on a tablet or laptop on the same WiFi network as the AX12:

```bash
su 0 python3 tools/cot_bridge.py --atak-host 192.168.1.50
```

Replace `192.168.1.50` with the IP of the device running ATAK.

### Multicast — all ATAK clients on the network

ATAK listens for multicast CoT on the standard TAK multicast group by default:

```bash
su 0 python3 tools/cot_bridge.py --atak-host 239.2.3.1
```

Every ATAK instance on the local network will receive the track simultaneously.
Requires the network to support IP multicast (most WiFi APs do).

---

## CoT Details

### Type codes

| Code | Meaning |
|------|---------|
| `a-f-A-M-F-Q` | Friendly / Air / Military / Fixed-wing / UAV — used for the vehicle |
| `a-f-G-U-C` | Friendly / Ground / Unit / Combat — used for the pilot position |

The `a-f-A-M-F-Q` breakdown: `a` = atom (concrete entity), `f` = friend,
`A` = air, `M` = military, `F` = fixed-wing, `Q` = UAV/drone.

### What ATAK displays

Each CoT update populates the following fields on the ATAK map:

- **Position:** latitude, longitude (WGS84, 7 decimal places)
- **Altitude:** HAE in meters
- **Track:** course (degrees true) and ground speed (m/s)
- **Callsign:** the `--uid` value
- **Remarks:** flight mode, armed/disarmed state, speed, altitude MSL

Example remarks string: `LOITER | Armed | 5.2m/s | 112m MSL`

### Stale timeout

CoT events include a `stale` timestamp set 10 seconds in the future. If the
bridge stops transmitting, ATAK removes the icon from the map after 10 seconds.
This prevents stale tracks from lingering after loss of link.

---

## TAK OSD Lua Script

`lua/tak-osd.lua` renders a TAK-style tactical HUD directly on the AX12
touchscreen through the Flyshark Lua VM — **no ATAK app required.**

### Features

- GPS coordinates in military degree-minute format (N/S/E/W)
- MGRS grid reference
- Compass rose with cardinal indicators (red N, green E/S/W) and heading readout
- RSSI and Link Quality (LQ) bars with color-coded thresholds
- TX battery voltage and percentage bar
- Flight mode and RF mode readout
- Stick channel bars (AIL, ELE, THR, RUD) with raw values
- Armed/Disarmed status
- Mission Elapsed Timer (MET)

### Installation and launch

1. Copy `lua/tak-osd.lua` to `/storage/emulated/0/AX12LUA/SCRIPTS/TOOLS/`
   on the AX12
2. Open **RadioMaster App > System Menu > Lua Scripts > Tools**
3. Select **TAK OSD**

The script runs in CRSF mode and reads telemetry values (`gps-lat`, `gps-lon`,
`Hdg`, `RQly`, `tx-voltage`, etc.) from the Flyshark telemetry source. It does
not require MAVLink link mode — standard CRSF telemetry is sufficient.

Double-tap the top-left corner of the screen to exit the script.

---

## MAVLink Bridge for QGC

`tools/mavlink_bridge.py` bridges the ELRS Backpack WiFi MAVLink stream
(UDP `10.0.0.1:14550`) to a TCP server on port 5760 that QGroundControl and
Mission Planner expect.

```bash
tac mavlink
# equivalent: python3 tools/mavlink_bridge.py bridge
```

This path uses WiFi rather than the serial port, so it runs in parallel with
the CoT bridge without conflict. QGC connects to `<AX12-IP>:5760`.

For full setup including stream rates, ELRS configuration, and QGC comm link
settings, see `docs/mavlink-setup.md`.

---

## Troubleshooting

### No icon appears on the ATAK map

1. Confirm the UDP input is configured correctly (port 4242, protocol UDP,
   address 0.0.0.0) and shows as active in ATAK Network Connections
2. Run `python3 tools/test_cot.py` — if the bridge is on the same device as
   ATAK, a single blip should appear immediately
3. In test mode the track orbits Null Island (0°N 0°E) — zoom out far enough
   to see it, or search for the callsign in the ATAK search bar

### Icon appears but position is wrong

Test mode sends to coordinates `(0, 0)` by design. Switch to live mode to get
real position. In live mode, verify the flight controller is sending
`GLOBAL_POSITION_INT` (message ID 33) — this requires a GPS fix on the FC and
`SRn_POSITION` set to at least 1.

### Serial open failed

The bridge prints `Serial open failed` and falls back to synthetic data when:

- The process is not running as root (`su 0` is required)
- `/dev/ttyS1` is held by another process (QGC, a previous bridge instance)
- ELRS is not in MAVLink link mode (port exists but delivers no MAVLink frames)

Check for conflicting processes:

```bash
su 0 ls -la /proc/*/fd/* 2>/dev/null | grep ttyS1
```

### Multiple bridges conflict

Only one process can hold `/dev/ttyS1` open at a time. Run one bridge per
path:

- **CoT bridge:** uses `/dev/ttyS1` (serial)
- **MAVLink/QGC bridge:** uses the Backpack WiFi UDP stream — no serial access

These two bridges can run simultaneously because they use different transport
paths. Do not run two instances of `cot_bridge.py` simultaneously.
