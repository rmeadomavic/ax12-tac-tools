# AX12 Tactical Tools — Lua Scripts

## Install

Copy `.lua` files to `/storage/emulated/0/AX12LUA/SCRIPTS/TOOLS/` on the device.

## Access

RadioMaster App > System Menu > Lua Scripts > Tools.

## Convention

All scripts use the standard module pattern:

```lua
-- TNS|Script Name|TNE

local function init()
  -- initialization
end

local function run(event, touchState)
  -- main loop
end

return { init=init, run=run }
```

## Tactical

| Script | Description |
|--------|-------------|
| **tak-osd** | TAK-style HUD — GPS, MGRS, compass, RSSI/LQ, mission timer |
| **ccip** | Impact point targeting — physics model, range rings, drift vector, RELEASE cue |
| **nineline** | 9-Line CAS brief template — auto-fills target elevation and grid from GPS |
| **mgrs-tool** | MGRS coordinate converter — WGS84 to UTM/MGRS, waypoint save, distance/bearing |
| **mission-timer** | 6-phase timer — STARTUP / LAUNCH / TRANSIT / ON STATION / RTB / RECOVERY |
| **preflight** | 12-item pre-flight checklist — telemetry auto-check, GO/NO-GO |
| **freq-decon** | RF frequency deconfliction — 900/2400/5800 MHz bands, conflict detection |

## Flight Ops

| Script | Description |
|--------|-------------|
| **fw-helper** | Fixed-wing helper — approach calc, stall speed, bank angle, wind triangle |
| **wind-calc** | Wind component calculator — headwind/crosswind, Beaufort scale, GO/NO-GO |
| **bf-osd** | Betaflight OSD — artificial horizon, compass tape, battery, military style toggle |
| **compass** | Compass rose with attitude indicator |
| **training** | 6 flight exercises — HOVER, BOX, FIGURE 8, ORBIT, SPEED RUN, LANDING |
| **g-force** | G-force and attitude display from accelerometer |
| **servo-test** | Servo/motor output tester for ArduPilot |

## Field Utility

| Script | Description |
|--------|-------------|
| **battery-log** | TX battery voltage tracking — graph, CSV logging, discharge rate |
| **flight-log** | Flight logging with JSON persistence |
| **ch-notes** | Channel label editor |
| **motor-test** | Motor/ESC test display |
| **site-manager** | Flying site database — GPS save, distance/bearing |
| **unit-conv** | Unit converter — speed, distance, altitude, temp, weight, pressure |
| **stopwatch** | Stopwatch with lap timing |
