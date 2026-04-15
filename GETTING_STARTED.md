# Getting Started

The AX12 runs Android. These tools make it push your drone's position to ATAK over CoT so you can track it on the COP while you fly. Also includes a TAK-style HUD, CCIP, 9-line template, freq decon, mission timer, preflight checklist, and other field tools for the touchscreen.

One command to install. Takes about 30 minutes to get from a stock AX12 to a live drone track on the map.

---

## Requirements

- RadioMaster AX12 (stock firmware)
- WiFi (for initial setup only — everything runs on-device after that)
- ATAK installed on the AX12 (for UAS tracking on the COP)
- ~30 minutes for setup

---

## Step 1: Install Termux

Termux is a Linux terminal for Android — it's how the tools run on the AX12. **Do not use the Google Play version** — it's broken. Get the real one:

**From the AX12 (no computer):**
1. Open browser on the AX12 → `github.com/termux/termux-app/releases`
2. Download the **universal APK**
3. Install it (allow unknown sources if prompted)

**From a computer via ADB:**
1. Download the APK from the same link
2. Enable USB debugging: Settings > About > tap Build Number 7x > Developer Options > USB Debugging
3. `adb install termux-app_*.apk`

---

## Step 2: Run the Installer

Open Termux and paste this:

```
pkg install -y curl && curl -sL https://raw.githubusercontent.com/rmeadomavic/ax12-tac-tools/main/install.sh | bash
```

Takes a few minutes. It installs packages, clones the tools, copies Lua scripts to the radio app, sets up home screen shortcuts, and configures Termux to open the tool menu automatically. Safe to re-run.

---

## Step 3: Using It

Open Chrome on the AX12 and go to `http://localhost:8080`. You'll see the tool launcher — big buttons organized by category. Tap one to run it.

**Bookmark it to your home screen:** In Chrome, tap the menu (three dots) > "Add to Home screen". Now it's an icon on your home screen like any other app.

The web launcher starts automatically on boot (if Termux:Boot is installed) or whenever Termux opens. You shouldn't have to think about it.

**Settings:** Tap the gear icon to add/remove tools, reorder them, or change commands. Your changes are saved separately from the defaults so updates don't overwrite them.

**Command line** (over SSH or in Termux) — `tac atak`, `tac gps`, `tac airspace`, `tac --help` still work.

---

## ATAK Integration

The CoT bridge reads MAVLink off the ELRS serial link and pushes your aircraft to ATAK as an `a-f-A-M-F-Q` track. Position, alt MSL, heading, speed, flight mode, armed state — updates at 0.5 Hz.

### Install ATAK on the AX12

- **CivTAK** from [tak.gov](https://tak.gov) (free registration) — recommended
- **ATAK-CIV** from Play Store — if Play Services are set up on the device
- Sideload via ADB: `adb install ATAK-CIV-*.apk`

### Configure Network Input

1. ATAK > Settings > **Network Preferences**
2. Add UDP input: port **4242**, address **0.0.0.0**
3. Return to map

### Verify

```
tac cot-test
```

Sends a single CoT event to `127.0.0.1:4242`. Look for **ELRS-Drone-1** at 0°N 0°E on the map. If it shows, the path is good.

### Go Live

```
tac atak
```

Reads MAVLink from `/dev/ttyS1` (ELRS passthrough UART, 460800 baud), converts to CoT XML, pushes to ATAK on localhost. Aircraft appears on the map and updates as it flies.

**Requires:**
- ELRS TX/RX firmware 3.5+ with MAVLink link mode enabled
- ESP-based receiver (RP1/RP2/RP3, EP1/EP2 — STM receivers lack bandwidth)
- ArduPilot FC with MAVLink on the RX UART (`SERIALn_PROTOCOL=2`, `SERIALn_BAUD=460`)

Full FC and ELRS config: [docs/mavlink-setup.md](docs/mavlink-setup.md)

### Multi-device

To feed ATAK on a separate device (EUD, tablet, TAK server):

```
su 0 python3 tools/cot_bridge.py --atak-host 192.168.1.50    # specific device
su 0 python3 tools/cot_bridge.py --atak-host 239.2.3.1       # multicast to all TAK clients
```

Full TAK configuration reference: [docs/tak-setup.md](docs/tak-setup.md)

### Troubleshooting

| Issue | Fix |
|---|---|
| No track on COP | Verify ATAK UDP input on 4242. Run `tac cot-test` to isolate. |
| Track appears but stale | ELRS not in MAVLink mode — check ELRS Lua > Link Mode. |
| Serial port error | Another process on ttyS1. Kill or use `--test` for synthetic data. |

---

## Lua Scripts

These run on the AX12 touchscreen in the RadioMaster app. Access: **System Menu > Lua Scripts > Tools**.

| Script | Capability |
|---|---|
| **TAK OSD** | HUD overlay — MGRS grid, compass, RSSI/LQ, mission elapsed timer |
| **CCIP** | Continuously Computed Impact Point — ballistic model, range rings, RELEASE cue |
| **9-Line CAS** | CAS brief template — auto-fills target grid and elevation from GPS |
| **MGRS Tool** | WGS84 → MGRS converter, waypoint save, distance/bearing to saved points |
| **Freq Decon** | RF frequency deconfliction — 900/2400/5800 MHz bands, conflict detection |
| **Mission Timer** | 6-phase: STARTUP / LAUNCH / TRANSIT / ON STATION / RTB / RECOVERY |
| **Preflight** | 12-item checklist with telemetry auto-check, GO/NO-GO |
| **Wind Calc** | Headwind/crosswind components, Beaufort scale, GO/NO-GO for fixed-wing |

Full list: [lua/README.md](lua/README.md)

---

## Updating

```
tac update
```

Pulls latest code and re-copies Lua scripts. Also available from the menu.

---

## Troubleshooting

**`su 0` gives "Permission denied"**
The AX12 has factory root via `su 0`. If it's not working, check that `/system/xbin/su` exists. You may need to restart Termux.

**GPS shows no fix**
Go outside and wait about 60 seconds. The AX12's GPS needs a clear sky view for initial acquisition. Indoors it will not get a fix.

**"Serial port busy" when starting ATAK bridge**
Flyshark (the default ground station app) holds the ttyS0 serial port. The ATAK bridge uses ttyS1 separately, so they shouldn't conflict — but close Flyshark entirely and try again if you get this error.

**Termux crashes or packages fail to install**
Run `pkg update && pkg upgrade` to refresh the package list and update everything.

**"Command not found: tac" after install**
The install added the alias to `~/.bashrc` but your current session doesn't have it yet. Run `source ~/.bashrc` to load it, or just close and reopen Termux.

---

## More

Hardware docs, protocol research, and advanced tooling: [ax12-research](https://github.com/rmeadomavic/ax12-research)
