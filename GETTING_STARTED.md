# Getting Started

These tools put your drone on ATAK while you fly it. CoT bridge reads MAVLink off ELRS, pushes position/heading/mode to the COP. Also has a TAK OSD, CCIP, 9-line, freq decon, mission timer, and preflight on the touchscreen.

About 30 minutes from a stock AX12 to a live track on the map.

## What You Need

- RadioMaster AX12 (stock firmware)
- WiFi for initial setup
- ATAK-CIV **4.10.x** (see below — 5.x won't run on Android 9)

## Step 1: Install Termux

Termux is a Linux terminal for Android. **Don't use the Play Store version.** It's dead.

Get the real one from `github.com/termux/termux-app/releases`. Download the universal APK on the AX12's browser, install it. If you have a computer handy you can also `adb install` it.

## Step 2: Run the Installer

Open Termux, paste:

```
pkg install -y curl && curl -sL https://raw.githubusercontent.com/rmeadomavic/ax12-tac-tools/main/install.sh | bash
```

Installs Python/git/SSH, clones the repo, copies Lua scripts to Flyshark, sets up the web launcher. Safe to re-run if something breaks.

## Step 3: Open the Web UI

Go to `localhost:8080` in Chrome. Bookmark it to your home screen (three dots > Add to Home screen) and it acts like an app. Starts on boot if you have Termux:Boot.

Tap a button, the tool runs. Gear icon for settings: add/remove/reorder tools there. Changes persist across updates.

From the command line (SSH, etc.): `tac atak`, `tac gps`, `tac --help`.

## ATAK Setup

**Important: The AX12 is Android 9. ATAK 5.x needs Android 10+. You need ATAK-CIV 4.10.x specifically.** Get it from [tak.gov](https://tak.gov) (free registration) or [APKPure old versions](https://apkpure.com/atak-civ-civil-use/com.atakmap.app.civ/versions). No Play Services needed.

There's a setup wizard in the web UI (tap SETUP in the header) that walks through this and auto-configures the UDP input.

The short version:
1. Install ATAK 4.10, open it once
2. ATAK > Settings > Network Preferences > add UDP input, port 4242
3. Tap ATAK BRIDGE in the web launcher
4. Your drone shows up on the map

For live telemetry you also need ELRS in MAVLink mode and the FC configured. Details in the setup wizard and [docs/mavlink-setup.md](docs/mavlink-setup.md).

### Feeding Other Devices

```
su 0 python3 tools/cot_bridge.py --atak-host 192.168.1.50    # specific EUD/tablet
su 0 python3 tools/cot_bridge.py --atak-host 239.2.3.1       # multicast to all TAK clients
```

Full reference: [docs/tak-setup.md](docs/tak-setup.md)

## Lua Scripts

Auto-installed to Flyshark. System Menu > Lua Scripts > Tools.

TAK OSD, CCIP, 9-line CAS, MGRS, freq decon, mission timer, preflight, wind calc, and more. Full list in [lua/README.md](lua/README.md).

## Updating

```
tac update
```

Or tap UPDATE in the web UI. Pulls latest code and re-copies Lua scripts.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `su 0` permission denied | Check `/system/xbin/su` exists. Restart Termux. |
| No GPS fix | Go outside. Wait 60s for cold start. |
| Serial port busy | Close Flyshark. ATAK bridge uses ttyS1 (separate from Flyshark's ttyS0). |
| `tac` not found | `source ~/.bashrc` or reopen Termux. |
| Packages fail | `pkg update && pkg upgrade` |
| No track on ATAK | Check UDP input on 4242. Run `tac cot-test` first. |
| Track stale/frozen | ELRS not in MAVLink mode. Check ELRS Lua > Link Mode. |

## More

Hardware docs, protocol research, UMBUS tooling: [ax12-research](https://github.com/rmeadomavic/ax12-research)
