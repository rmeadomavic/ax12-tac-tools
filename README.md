# AX12 Tactical Tools

The AX12 is an Android radio. Run the CoT bridge on it and your aircraft shows up on the COP while you fly. The bridge reads MAVLink telemetry off the ELRS link on `/dev/ttyS1` and publishes the track as Cursor-on-Target to ATAK and any TAK server. The radio does it. No laptop, no second GCS.

The bridge sends the aircraft's position, straight from MAVLink. It never needs the operator's own position. That matters here: this radio has no GNSS antenna, so anything that wants the operator's location is dead. The aircraft track is unaffected.

![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)
![Python 3.13](https://img.shields.io/badge/python-3.13-yellow.svg)
![Platform: Android 9](https://img.shields.io/badge/platform-Android%209-green.svg)

## Install

Open Termux, paste this:

```
pkg install -y curl && curl -sL https://raw.githubusercontent.com/rmeadomavic/ax12-tac-tools/main/install.sh | bash
```

Setup walkthrough: [GETTING_STARTED.md](GETTING_STARTED.md).

## Run the bridge

Set ATAK to listen on UDP 4242, then start the bridge:

```
su 0 python3 tools/cot_bridge.py
```

Your aircraft appears on the map. Confirm ATAK is listening before you fly:

```
python3 tools/test_cot.py            # one blip to ATAK at 0,0
```

Feed a TAK server, or a specific tablet, instead of the local map:

```
su 0 python3 tools/cot_bridge.py --tak-server tak.example:8087
su 0 python3 tools/cot_bridge.py --atak-host 192.168.1.50
```

TAK server framing, TLS, and mission-package certs: [docs/tak-setup.md](docs/tak-setup.md).

## Auto-start on boot

Copy the opt-in boot hook so the bridge comes up on power-up:

```
mkdir -p ~/.termux/boot
cp ~/ax12-tac-tools/boot/start-cot-bridge.sh ~/.termux/boot/
chmod +x ~/.termux/boot/start-cot-bridge.sh
```

Needs the Termux:Boot app from F-Droid. Delete the file to turn it off.

## Also in here

- `mavlink_bridge.py` serves MAVLink over TCP to QGC or Mission Planner on a laptop.
- Lua touchscreen scripts: TAK OSD, CCIP, 9-line CAS, freq decon, mission timer, preflight. Full list in [lua/README.md](lua/README.md).
- A web launcher on `localhost:8080` and a `tac` CLI for SSH use.

Runs in Termux, stdlib Python only. The bridge is the point; the rest is along for the ride.

## Prerequisites

- RadioMaster AX12 (stock firmware; root is built in)
- ELRS 3.5+ in MAVLink mode
- ATAK-CIV **4.10.x** (5.x needs Android 10+, won't install on the AX12)

## Related

Protocol research, hardware teardown, UMBUS tooling: [ax12-research](https://github.com/rmeadomavic/ax12-research)

## License

[MIT](LICENSE)
