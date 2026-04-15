# Getting Started with AX12 Tactical Tools

Your RadioMaster AX12 isn't just a remote control — it's an Android computer with a touchscreen, GPS, and WiFi. These tools turn it into a live tactical display: **your drone appears on a real map on the controller in your hands, updating in real time as it flies.** You see its position, altitude, heading, speed, and flight mode — all while holding the sticks. No phone, no tablet, no laptop required.

Beyond live tracking, you get 20+ Lua scripts (military HUD, targeting, mission timer, preflight checklists) and Python tools for airspace checks, payload drop calculations, and rover navigation. One install command, then you're operational.

---

## What You Need

- RadioMaster AX12 transmitter
- WiFi network (during setup)
- About 30 minutes

---

## Step 1: Install Termux

Termux is a terminal app for Android — it's how you run commands on the AX12. You need the official version from GitHub, **not** the Google Play version.

> **Do NOT install the Google Play version — it's outdated and broken.**

### Option A: From the AX12 itself (no computer needed)

1. Open the browser on the AX12
2. Go to: `github.com/termux/termux-app/releases`
3. Download the latest **universal APK** (look for `termux-app_v*_universal.apk`)
4. When prompted, tap **Install** — if Android asks to allow installs from unknown sources, accept it

### Option B: From your computer via ADB

1. Download the universal APK from `github.com/termux/termux-app/releases` on your computer
2. Enable USB debugging on the AX12:
   - Go to **Settings > About**
   - Tap **Build Number** 7 times until you see "You are now a developer"
   - Go back to **Settings > Developer Options**
   - Enable **USB Debugging**
3. Connect the AX12 to your computer with a USB cable
4. Run: `adb install termux.apk`

---

## Step 2: Run the Installer

Open Termux and paste this single command:

```
pkg install -y curl && curl -sL https://raw.githubusercontent.com/rmeadomavic/ax12-tac-tools/main/install.sh | bash
```

The installer will:
- Install required packages (Python, git, tools)
- Clone the ax12-tac-tools repo to your device
- Copy all Lua scripts to the right folder for the RadioMaster app
- Add a `tac` shortcut command to your shell

It takes a few minutes depending on your WiFi speed. It's safe to re-run if anything goes wrong — it won't break what's already installed.

---

## Step 3: Try It Out

Once the install finishes, type `tac` to open the interactive menu:

```
╔══════════════════════════════╗
║     AX12 Tactical Tools      ║
╠══════════════════════════════╣
║  [1] ATAK CoT Bridge         ║
║  [2] GPS Info                ║
║  [3] Airspace Check          ║
║  [4] ELRS Status             ║
║  [5] MAVLink Monitor         ║
║  [6] CoT Test (Null Island)  ║
║  [7] System Info             ║
║  [0] Exit                    ║
╚══════════════════════════════╝
```

You can also call tools directly from the command line:

| Command | What it does |
|---|---|
| `tac atak` | Start the live ATAK CoT bridge |
| `tac gps` | Show GPS fix, coordinates, accuracy |
| `tac airspace` | Check airspace restrictions |
| `tac --help` | List all available commands |

---

## TAK Integration (The Main Event)

This is what you came here for. ATAK (Android Team Awareness Kit) is the mapping app used by US military and first responders for real-time situational awareness. Install it on your AX12 and run the CoT bridge — now your drone's live GPS position streams straight from the ELRS link onto the map on your controller's screen. You fly the drone and watch it move on the map at the same time, on the same device, in your hands. Altitude, speed, heading, flight mode — all updating in real time.

### Install ATAK

Two options:
- **Recommended:** Register (free) at [tak.gov](https://tak.gov) and download ATAK
- **Quicker:** Search the Play Store for **"ATAK-CIV"** (civilian version)

### Configure ATAK

Once ATAK is installed on your phone or tablet:

1. Open ATAK > **Settings > Network Preferences**
2. Tap **Add Input**
3. Set protocol to **UDP**
4. Set port to **4242**
5. Set address to **0.0.0.0** (listens on all interfaces)
6. Save and return to the map

### Test the connection

Run `tac cot-test` in Termux. This sends a test position packet to ATAK. Look for a marker called **"ELRS-Drone-1"** appearing at Null Island (0°N, 0°E) on the map. If you see it, your network path is working.

### Go live

Run `tac atak` to start the live bridge. It reads MAVLink telemetry from your drone via the ELRS link and forwards it to ATAK as CoT (Cursor on Target) messages in real time.

**Requirements for live operation:**
- ELRS 3.5 or newer
- ESP-based receiver (e.g. EP1, EP2, SuperMini)
- MAVLink link mode enabled on the receiver
- ArduPilot flight controller with telemetry configured

For full MAVLink setup instructions, see [docs/mavlink-setup.md](docs/mavlink-setup.md).

### Troubleshooting ATAK

| Problem | Fix |
|---|---|
| No icon on map after `tac cot-test` | Check ATAK UDP input is set to port 4242 |
| Drone icon appears but doesn't move | Check ELRS receiver is in MAVLink mode, not CRSF passthrough |
| "Serial port busy" error | Flyshark holds ttyS0 — ATAK bridge uses ttyS1 separately, so close Flyshark and retry |

---

## Lua Scripts

Lua scripts run directly on the AX12's touchscreen through the RadioMaster app. No phone or external device needed.

**To access them:** RadioMaster App > System Menu > Lua Scripts > Tools

Highlights:

| Script | What it does |
|---|---|
| TAK OSD | Displays ATAK-style HUD overlay with drone position data |
| CCIP | Continuously Computed Impact Point — ballistic targeting reticle |
| 9-Line CAS | Close Air Support 9-line briefing form |
| MGRS Tool | Military Grid Reference System coordinate converter |
| Preflight | Systematic pre-flight checklist |
| Mission Timer | Elapsed and countdown timer with audio alerts |
| Wind Calc | Wind drift calculator for fixed-wing and payload drops |

Full documentation for all scripts: [lua/README.md](lua/README.md)

---

## Updating

To get the latest tools and scripts:

```
tac update
```

Or pick it from the menu — option is listed near the bottom.

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

## Deep Dive

Want to go further? The companion research repo has everything:

**[github.com/rmeadomavic/ax12-research](https://github.com/rmeadomavic/ax12-research)**

Includes:
- Root access guide (the AX12 ships with factory root — here's how to use it)
- Hardware teardown with photos
- UMBUS serial protocol reverse-engineering notes
- Full tool usage guide with examples
