# AX12 Tac Tools — Improvement Ideas

Brainstormed 2026-04-15. Context: SORCC military FPV/robotics instruction, community AX12 operators, demo-ready product.

## What's Working

- CoT bridge → ATAK pipeline is the core value prop and it works
- Web launcher replaces the terminal — right call for operators
- Setup wizard catches the ATAK 4.10/Android 9 issue before they waste time
- Config-driven tool registry lets operators customize
- Lua scripts are solid and cover real operational needs

## What Needs Work (This Session)

### 1. Visual Polish
The UI works but looks like a weekend project. For demos and first impressions it needs to feel like a product — think Anduril Lattice or Palantir Gotham. Not flashy, just confident. Specific changes:
- Better font stack — Inter or system-ui instead of Courier New for UI chrome, keep monospace for output
- Subtle depth — very faint gradients, box shadows, not flat
- Micro-interactions — button press feedback, smooth view transitions, status badge pulses
- Status bar at top — live indicators for GPS fix, serial port, ATAK connection (not just static battery/uptime)
- Tighter spacing and alignment — the grid gaps and padding are slightly off
- The output view needs a proper terminal feel — dark inset, scanline or glow effect (subtle)

### 2. Voice / Tone
All the docs read like they were generated. They need to read like one operator wrote them for another. Short sentences. No filler. No lists of capabilities with bold headers. Just "here's what this does, here's how to set it up, here's what to watch out for."

### 3. Reliability
- Tools that hang with no output need a "waiting for output..." message after 3s
- The double-process / zombie port issue needs a proper fix (maybe PID file)
- Server restart should be one clean operation

## Future Ideas (Not This Session)

### Live Status Dashboard
Replace the static battery/uptime bar with a live status strip:
- GPS: FIX / NO FIX (with coordinates if available)
- Serial: ttyS0 OK / ttyS1 OK / BUSY
- ATAK: CONNECTED / NOT RUNNING (check if UDP 4242 is bound)
- Link: RSSI/LQ from ELRS telemetry
- Battery: voltage + percentage

This turns the launcher from a tool menu into an actual ground station dashboard.

### Mission Mode
A single-screen view for active operations:
- ATAK bridge running (status + last CoT sent)
- GPS position updating
- Link quality bar
- Mission timer
- One-tap stop-all

This is the screen you look at during a flight — not the tool menu.

### Hydra/Argus Integration
Available but not front-and-center:
- Add as an "ADVANCED" or "AI" category in tools.json
- Hydra display (object detection telemetry) is already a tool
- Argus is the Raspberry Pi companion — could add a status check or SSH bridge
- Keep these for users who know what they are

### Field Briefing Generator
Pre-mission briefing tool that pulls:
- Current GPS position + MGRS grid
- Weather (if network available, otherwise manual input)
- Airspace restrictions
- Freq decon status
- Vehicle preflight checklist status
Outputs a formatted brief you can screenshot or share.

### Multi-Vehicle Support
The CoT bridge currently tracks one drone. Multi-vehicle would need:
- Multiple bridge instances with different UIDs
- Or a single bridge that reads from multiple serial sources
- Each vehicle gets its own callsign on ATAK
- This is the path to a real small-unit UAS cell

### TAK Server Integration
Instead of just localhost CoT, support connecting to a TAK server:
- Mesh networking between multiple AX12 operators
- Shared COP across the team
- The AX12 becomes a TAK endpoint, not just a local tool
- Requires network planning (WiFi mesh, Meshtastic, or cellular)

### Export / Logging
- Log all CoT events to a JSONL file for post-mission review
- Export flight track as KML/KMZ for Google Earth
- Mission replay in the web UI

## Priority for This Session
1. Visual overhaul (highest demo impact)
2. Voice pass on docs (second highest — first thing community sees)
3. Code cleanup from review (reliability)
4. Live status indicators (if time permits — high value, moderate effort)
