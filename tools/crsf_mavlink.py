#!/data/data/com.termux/files/usr/bin/python3
"""
CRSF-to-MAVLink Telemetry Bridge for RadioMaster AX12

Translates CRSF telemetry arriving over the ELRS radio link into MAVLink
messages and serves them over TCP for QGroundControl / Mission Planner.

Architecture:
    Drone (ArduPilot) -> ELRS RX -> ELRS TX module -> UMBUS serial (ttyS0)
                                                           |
                                              [Flyshark app owns port]
                                                           |
                                               strace snoop on reads
                                                           |
                                              UMBUS 0x15 frame extraction
                                                           |
                                              CRSF telemetry parsing
                                                           |
                                              MAVLink message building
                                                           |
                                              TCP server :5760 -> QGC

The AX12's built-in ELRS radio receives CRSF telemetry from drones, but
the Flyshark app exclusively holds /dev/ttyS0. We use strace to passively
snoop the serial traffic without disturbing the app, extract UMBUS 0x15
frames that wrap CRSF telemetry, translate the CRSF sensor data into
standard MAVLink messages, and serve them over TCP.

Modes:
    live     - Snoop CRSF telemetry from Flyshark via strace, translate
               to MAVLink, serve on TCP 5760
    demo     - Generate synthetic CRSF data (no drone needed), translate
               to MAVLink, serve on TCP 5760

Usage:
    # Live mode (requires root for strace):
    su 0 python3 crsf_mavlink.py live

    # Demo mode (synthetic data, no root needed):
    python3 crsf_mavlink.py --demo
    python3 crsf_mavlink.py --demo --duration 60
    python3 crsf_mavlink.py --demo --tcp-port 5760

    # QGC connection:
    #   Add TCP comm link -> Host: 127.0.0.1  Port: 5760

Python stdlib only. No pip packages.
"""

import argparse
import math
import os
import re
import signal
import socket
import struct
import subprocess
import sys
import threading
import time


# ===================================================================
# UMBUS Protocol (embedded from umbus.py for standalone operation)
# ===================================================================

UMBUS_SYNC = 0xA6

class FrameType:
    CHANNEL_DATA  = 0x57
    HEARTBEAT_MCU = 0x08
    EXTENDED      = 0x10
    ELRS_TELEM    = 0x15
    CMD_07        = 0x07
    CMD_0C        = 0x0C
    CMD_0E        = 0x0E
    IDLE          = 0x77

UMBUS_FRAME_SIZES = {
    FrameType.CHANNEL_DATA: 87,
    FrameType.HEARTBEAT_MCU: 7,
    FrameType.EXTENDED: 18,
    FrameType.ELRS_TELEM: 21,
    FrameType.CMD_07: 7,
    FrameType.CMD_0C: 12,
    FrameType.CMD_0E: 14,
    FrameType.IDLE: 87,
}

# CRC-8/MAXIM table (Dallas 1-Wire, poly 0x31)
CRC8_TABLE = bytes([
    0x00, 0x5E, 0xBC, 0xE2, 0x61, 0x3F, 0xDD, 0x83,
    0xC2, 0x9C, 0x7E, 0x20, 0xA3, 0xFD, 0x1F, 0x41,
    0x9D, 0xC3, 0x21, 0x7F, 0xFC, 0xA2, 0x40, 0x1E,
    0x5F, 0x01, 0xE3, 0xBD, 0x3E, 0x60, 0x82, 0xDC,
    0x23, 0x7D, 0x9F, 0xC1, 0x42, 0x1C, 0xFE, 0xA0,
    0xE1, 0xBF, 0x5D, 0x03, 0x80, 0xDE, 0x3C, 0x62,
    0xBE, 0xE0, 0x02, 0x5C, 0xDF, 0x81, 0x63, 0x3D,
    0x7C, 0x22, 0xC0, 0x9E, 0x1D, 0x43, 0xA1, 0xFF,
    0x46, 0x18, 0xFA, 0xA4, 0x27, 0x79, 0x9B, 0xC5,
    0x84, 0xDA, 0x38, 0x66, 0xE5, 0xBB, 0x59, 0x07,
    0xDB, 0x85, 0x67, 0x39, 0xBA, 0xE4, 0x06, 0x58,
    0x19, 0x47, 0xA5, 0xFB, 0x78, 0x26, 0xC4, 0x9A,
    0x65, 0x3B, 0xD9, 0x87, 0x04, 0x5A, 0xB8, 0xE6,
    0xA7, 0xF9, 0x1B, 0x45, 0xC6, 0x98, 0x7A, 0x24,
    0xF8, 0xA6, 0x44, 0x1A, 0x99, 0xC7, 0x25, 0x7B,
    0x3A, 0x64, 0x86, 0xD8, 0x5B, 0x05, 0xE7, 0xB9,
    0x8C, 0xD2, 0x30, 0x6E, 0xED, 0xB3, 0x51, 0x0F,
    0x4E, 0x10, 0xF2, 0xAC, 0x2F, 0x71, 0x93, 0xCD,
    0x11, 0x4F, 0xAD, 0xF3, 0x70, 0x2E, 0xCC, 0x92,
    0xD3, 0x8D, 0x6F, 0x31, 0xB2, 0xEC, 0x0E, 0x50,
    0xAF, 0xF1, 0x13, 0x4D, 0xCE, 0x90, 0x72, 0x2C,
    0x6D, 0x33, 0xD1, 0x8F, 0x0C, 0x52, 0xB0, 0xEE,
    0x32, 0x6C, 0x8E, 0xD0, 0x53, 0x0D, 0xEF, 0xB1,
    0xF0, 0xAE, 0x4C, 0x12, 0x91, 0xCF, 0x2D, 0x73,
    0xCA, 0x94, 0x76, 0x28, 0xAB, 0xF5, 0x17, 0x49,
    0x08, 0x56, 0xB4, 0xEA, 0x69, 0x37, 0xD5, 0x8B,
    0x57, 0x09, 0xEB, 0xB5, 0x36, 0x68, 0x8A, 0xD4,
    0x95, 0xCB, 0x29, 0x77, 0xF4, 0xAA, 0x48, 0x16,
    0xE9, 0xB7, 0x55, 0x0B, 0x88, 0xD6, 0x34, 0x6A,
    0x2B, 0x75, 0x97, 0xC9, 0x4A, 0x14, 0xF6, 0xA8,
    0x74, 0x2A, 0xC8, 0x96, 0x15, 0x4B, 0xA9, 0xF7,
    0xB6, 0xE8, 0x0A, 0x54, 0xD7, 0x89, 0x6B, 0x35,
])

UMBUS_CRC_INIT = {
    FrameType.EXTENDED: 0x7F,
    FrameType.ELRS_TELEM: 0x32,
}


def umbus_crc8(data, init=0x00):
    """CRC-8/MAXIM over data bytes."""
    crc = init
    for b in data:
        crc = CRC8_TABLE[b ^ crc]
    return crc


class UMBUSFrame:
    """A parsed UMBUS frame."""
    __slots__ = ('frame_type', 'raw', 'checksum_valid')

    def __init__(self, frame_type, raw, checksum_valid=True):
        self.frame_type = frame_type
        self.raw = raw
        self.checksum_valid = checksum_valid


class UMBUSDecoder:
    """Streaming UMBUS frame decoder."""

    def __init__(self):
        self._buf = bytearray()

    def feed(self, data):
        """Feed raw bytes, yield UMBUSFrame objects."""
        self._buf.extend(data)

        while True:
            sync_idx = -1
            for i in range(len(self._buf)):
                if self._buf[i] == UMBUS_SYNC:
                    sync_idx = i
                    break
            if sync_idx < 0:
                self._buf.clear()
                return
            if sync_idx > 0:
                del self._buf[:sync_idx]

            if len(self._buf) < 2:
                return

            ft = self._buf[1]

            # Determine frame size
            if ft == 0x08 and len(self._buf) >= 4:
                frame_size = 8 if self._buf[2] == 0x35 else 7
            else:
                frame_size = UMBUS_FRAME_SIZES.get(ft)
                if frame_size is None:
                    frame_size = ft
                    if frame_size < 3 or frame_size > 256:
                        del self._buf[0]
                        continue

            if len(self._buf) < frame_size:
                return

            raw = bytes(self._buf[:frame_size])
            del self._buf[:frame_size]

            # Verify checksum
            if ft == 0x08 and len(raw) == 7 and raw[2] != 0x35:
                chk_valid = True
            else:
                init = UMBUS_CRC_INIT.get(ft, 0x00)
                expected = umbus_crc8(raw[1:-1], init)
                chk_valid = (expected == raw[-1])

            yield UMBUSFrame(ft, raw, chk_valid)


# ===================================================================
# CRSF Protocol Constants and Parser
# ===================================================================

# CRSF frame type IDs (telemetry from vehicle)
CRSF_GPS           = 0x02
CRSF_BATTERY       = 0x08
CRSF_LINK_STATS    = 0x14
CRSF_RC_CHANNELS   = 0x16
CRSF_ATTITUDE      = 0x1E
CRSF_FLIGHT_MODE   = 0x21

CRSF_TYPE_NAMES = {
    CRSF_GPS: "GPS",
    CRSF_BATTERY: "BATTERY",
    CRSF_LINK_STATS: "LINK_STATISTICS",
    CRSF_RC_CHANNELS: "RC_CHANNELS",
    CRSF_ATTITUDE: "ATTITUDE",
    CRSF_FLIGHT_MODE: "FLIGHT_MODE",
}


class CRSFTelemetry:
    """Aggregated CRSF telemetry state from parsed frames."""

    def __init__(self):
        # GPS
        self.gps_lat = 0.0       # degrees
        self.gps_lon = 0.0       # degrees
        self.gps_alt = 0.0       # meters
        self.gps_speed = 0.0     # m/s
        self.gps_heading = 0.0   # degrees
        self.gps_sats = 0
        self.gps_valid = False
        self.gps_time = 0.0

        # Battery
        self.bat_voltage = 0.0   # V
        self.bat_current = 0.0   # A
        self.bat_capacity = 0    # mAh used
        self.bat_remaining = 0   # percent
        self.bat_valid = False
        self.bat_time = 0.0

        # Attitude
        self.att_pitch = 0.0     # degrees
        self.att_roll = 0.0      # degrees
        self.att_yaw = 0.0       # degrees
        self.att_valid = False
        self.att_time = 0.0

        # Flight mode
        self.flight_mode = ""
        self.flight_mode_time = 0.0

        # Link statistics
        self.rssi_up = 0         # dBm (uplink RSSI as reported by RX)
        self.rssi_down = 0       # dBm (downlink RSSI)
        self.lq = 0              # percent
        self.snr = 0             # dB
        self.rf_mode = 0
        self.tx_power = 0        # mW
        self.link_valid = False
        self.link_time = 0.0

        # Counters
        self.frames_parsed = 0
        self.frames_by_type = {}

    def update_gps(self, lat, lon, alt, speed, heading, sats):
        self.gps_lat = lat
        self.gps_lon = lon
        self.gps_alt = alt
        self.gps_speed = speed
        self.gps_heading = heading
        self.gps_sats = sats
        self.gps_valid = True
        self.gps_time = time.monotonic()

    def update_battery(self, voltage, current, capacity, remaining):
        self.bat_voltage = voltage
        self.bat_current = current
        self.bat_capacity = capacity
        self.bat_remaining = remaining
        self.bat_valid = True
        self.bat_time = time.monotonic()

    def update_attitude(self, pitch, roll, yaw):
        self.att_pitch = pitch
        self.att_roll = roll
        self.att_yaw = yaw
        self.att_valid = True
        self.att_time = time.monotonic()

    def update_flight_mode(self, mode_str):
        self.flight_mode = mode_str
        self.flight_mode_time = time.monotonic()

    def update_link_stats(self, rssi_up, rssi_down, lq, snr, rf_mode, tx_power):
        self.rssi_up = rssi_up
        self.rssi_down = rssi_down
        self.lq = lq
        self.snr = snr
        self.rf_mode = rf_mode
        self.tx_power = tx_power
        self.link_valid = True
        self.link_time = time.monotonic()


def parse_crsf_frame(frame_type, payload, state):
    """Parse a CRSF telemetry frame and update state.

    CRSF frame format (inside UMBUS 0x15 wrapper):
        The UMBUS 0x15 frame wraps CRSF data starting at byte 5.
        For actual CRSF telemetry (GPS, battery, etc.), the CRSF frame
        starts with: [addr] [len] [type] [payload...] [crc]

    For direct CRSF frames (not the UMBUS timing/handset sub-command):
        payload bytes contain the raw CRSF sensor data.
    """
    state.frames_parsed += 1
    state.frames_by_type[frame_type] = state.frames_by_type.get(frame_type, 0) + 1

    if frame_type == CRSF_GPS and len(payload) >= 15:
        # CRSF GPS: lat(i32 BE) lon(i32 BE) speed(u16 BE) heading(u16 BE)
        #           alt(u16 BE) sats(u8)
        lat = struct.unpack('>i', payload[0:4])[0] / 1e7
        lon = struct.unpack('>i', payload[4:8])[0] / 1e7
        speed = struct.unpack('>H', payload[8:10])[0] / 100.0  # m/s * 100
        heading = struct.unpack('>H', payload[10:12])[0] / 100.0  # deg * 100
        alt = struct.unpack('>H', payload[12:14])[0] - 1000  # offset by 1000m
        sats = payload[14]
        state.update_gps(lat, lon, float(alt), speed, heading, sats)
        return True

    elif frame_type == CRSF_BATTERY and len(payload) >= 8:
        # CRSF Battery: voltage(u16 BE) current(u16 BE) capacity(u24 BE) remaining(u8)
        voltage = struct.unpack('>H', payload[0:2])[0] / 10.0  # dV -> V
        current = struct.unpack('>H', payload[2:4])[0] / 10.0  # dA -> A
        capacity = (payload[4] << 16) | (payload[5] << 8) | payload[6]  # mAh
        remaining = payload[7]  # percent
        state.update_battery(voltage, current, capacity, remaining)
        return True

    elif frame_type == CRSF_ATTITUDE and len(payload) >= 6:
        # CRSF Attitude: pitch(i16 BE) roll(i16 BE) yaw(i16 BE)
        # Values in radians * 10000
        pitch = struct.unpack('>h', payload[0:2])[0] / 10000.0
        roll = struct.unpack('>h', payload[2:4])[0] / 10000.0
        yaw = struct.unpack('>h', payload[4:6])[0] / 10000.0
        state.update_attitude(
            math.degrees(pitch),
            math.degrees(roll),
            math.degrees(yaw),
        )
        return True

    elif frame_type == CRSF_FLIGHT_MODE and len(payload) >= 1:
        # CRSF Flight Mode: null-terminated string
        try:
            mode = payload.split(b'\x00', 1)[0].decode('ascii', errors='replace')
        except Exception:
            mode = "UNKNOWN"
        # Strip trailing asterisk (CRSF convention for armed)
        state.update_flight_mode(mode.rstrip('*'))
        return True

    elif frame_type == CRSF_LINK_STATS and len(payload) >= 10:
        # CRSF Link Statistics:
        #   u8 uplink_rssi_ant1, u8 uplink_rssi_ant2, u8 uplink_lq,
        #   i8 uplink_snr, u8 active_antenna, u8 rf_mode,
        #   u8 uplink_tx_power, u8 downlink_rssi, u8 downlink_lq, i8 downlink_snr
        rssi1 = -payload[0] if payload[0] else 0  # stored as positive, display negative
        rssi2 = -payload[1] if payload[1] else 0
        lq = payload[2]
        snr = struct.unpack('b', bytes([payload[3]]))[0]
        rf_mode = payload[5]
        tx_power_idx = payload[6]
        rssi_down = -payload[7] if payload[7] else 0

        # TX power table (ELRS)
        tx_power_mw = {
            0: 0, 1: 10, 2: 25, 3: 50, 4: 100,
            5: 250, 6: 500, 7: 1000, 8: 2000,
        }.get(tx_power_idx, 0)

        # Use the stronger antenna RSSI
        rssi = max(rssi1, rssi2) if rssi1 != 0 or rssi2 != 0 else rssi1

        state.update_link_stats(rssi, rssi_down, lq, snr, rf_mode, tx_power_mw)
        return True

    return False


# ===================================================================
# UMBUS-to-CRSF Extraction
# ===================================================================

# The UMBUS 0x15 frame wraps CRSF handset/timing data from the ELRS
# module. When actual vehicle telemetry is being forwarded (GPS, battery,
# etc.), the MCU may use different UMBUS frame types or embed CRSF
# frames differently.
#
# Based on ELRS architecture: the TX module receives telemetry from the
# RX (on the drone) and passes it to the handset via CRSF serial.
# On the AX12, this CRSF serial goes through the AT32 MCU which wraps
# it in UMBUS frames.
#
# The 0x15 frame format observed so far wraps CRSF handset/timing only.
# Full telemetry (GPS/batt/attitude) may come through:
#   1. Additional 0x15 frames with different CRSF types in the payload
#   2. Different UMBUS frame types
#   3. The extended (0x10) telemetry frames
#
# This extractor handles both known patterns and will log unknown types
# for future protocol analysis.

ELRS_INVALID_MARKER = 0xFFFF


def extract_crsf_from_umbus(frame, state):
    """Extract and parse CRSF telemetry from a UMBUS frame.

    For 0x15 frames, the CRSF data starts at byte 5:
        [0]     sync (0xA6)
        [1]     type (0x15)
        [2-3]   UMBUS header
        [4]     padding
        [5]     CRSF address
        [6]     CRSF length
        [7]     CRSF frame type
        [8...]  CRSF payload
        [-1]    UMBUS checksum

    Returns True if a CRSF frame was successfully parsed.
    """
    if frame.frame_type != FrameType.ELRS_TELEM:
        return False

    if not frame.checksum_valid:
        return False

    raw = frame.raw
    if len(raw) < 10:
        return False

    crsf_type = raw[7]

    # Check if this is a handset timing sub-command (0x3A with sub-cmd 0x10)
    # vs actual telemetry passthrough
    if crsf_type == 0x3A:
        # This is the timing/handset frame - extract link validity info
        # but it doesn't contain GPS/battery/attitude data
        if len(raw) >= 17:
            link_status = struct.unpack_from('<H', raw, 15)[0]
            if link_status != ELRS_INVALID_MARKER:
                # Link is active but this frame only has timing info
                pass
        return False

    # For actual CRSF telemetry types, the payload starts after the
    # CRSF header bytes within the UMBUS wrapper
    # CRSF payload starts at byte 8 (after addr, len, type)
    crsf_payload_start = 8
    # CRSF payload length = crsf_len - 2 (type byte + CRC byte)
    crsf_len = raw[6] if len(raw) > 6 else 0
    if crsf_len < 2:
        return False
    payload_len = crsf_len - 2
    crsf_payload_end = crsf_payload_start + payload_len

    if crsf_payload_end > len(raw) - 1:  # -1 for UMBUS checksum
        # Payload extends beyond frame - might be fragmented
        crsf_payload_end = len(raw) - 1

    payload = raw[crsf_payload_start:crsf_payload_end]

    if len(payload) > 0:
        return parse_crsf_frame(crsf_type, payload, state)

    return False


# ===================================================================
# MAVLink v2 Constants and Builder
# ===================================================================

MAVLINK_V2_START = 0xFD

# Message IDs
MSG_HEARTBEAT           = 0
MSG_SYS_STATUS          = 1
MSG_GPS_RAW_INT         = 24
MSG_ATTITUDE            = 30
MSG_GLOBAL_POSITION_INT = 33
MSG_RC_CHANNELS         = 65
MSG_VFR_HUD             = 74
MSG_STATUSTEXT          = 253
MSG_BATTERY_STATUS      = 147

# CRC extras (seed bytes for each message type)
CRC_EXTRA = {
    MSG_HEARTBEAT: 50,
    MSG_SYS_STATUS: 124,
    MSG_GPS_RAW_INT: 24,
    MSG_ATTITUDE: 39,
    MSG_GLOBAL_POSITION_INT: 104,
    MSG_RC_CHANNELS: 118,
    MSG_VFR_HUD: 20,
    MSG_STATUSTEXT: 83,
    MSG_BATTERY_STATUS: 154,
}

# ArduCopter flight mode mapping (CRSF mode string -> custom_mode)
COPTER_MODE_MAP = {
    "STABILIZE": 0, "STAB": 0,
    "ACRO": 1,
    "ALT_HOLD": 2, "ALTH": 2,
    "AUTO": 3,
    "GUIDED": 4,
    "LOITER": 5, "LOIT": 5,
    "RTL": 6,
    "CIRCLE": 7,
    "LAND": 9,
    "DRIFT": 11,
    "SPORT": 13,
    "FLIP": 14,
    "AUTOTUNE": 15, "ATUN": 15,
    "POSHOLD": 16, "PHLD": 16,
    "BRAKE": 17,
    "THROW": 18,
    "SMART_RTL": 21, "SRTL": 21,
    "FLOWHOLD": 22,
    "FOLLOW": 23,
    "ZIGZAG": 24,
}

# ArduPlane flight mode mapping
PLANE_MODE_MAP = {
    "MANUAL": 0, "MANU": 0,
    "CIRCLE": 1,
    "STABILIZE": 2, "STAB": 2,
    "TRAINING": 3,
    "ACRO": 4,
    "FBWA": 5,
    "FBWB": 6,
    "CRUISE": 7, "CRUS": 7,
    "AUTOTUNE": 8, "ATUN": 8,
    "AUTO": 10,
    "RTL": 11,
    "LOITER": 12, "LOIT": 12,
    "GUIDED": 15,
    "QSTABILIZE": 17,
    "QHOVER": 18,
    "QLOITER": 19,
    "QLAND": 20,
    "QRTL": 21,
}

# ArduRover flight mode mapping
ROVER_MODE_MAP = {
    "MANUAL": 0, "MANU": 0,
    "ACRO": 1,
    "STEERING": 3,
    "HOLD": 4,
    "LOITER": 5, "LOIT": 5,
    "FOLLOW": 6,
    "SIMPLE": 7,
    "AUTO": 10,
    "RTL": 11,
    "SMART_RTL": 12, "SRTL": 12,
    "GUIDED": 15,
}


class MAVLinkBuilder:
    """Build MAVLink v2 packets from CRSF telemetry data."""

    def __init__(self, sysid=1, compid=1):
        self.sysid = sysid
        self.compid = compid
        self.seq = 0

    def _crc_accumulate(self, data, crc=0xFFFF):
        """X.25 CRC-16 accumulate."""
        for byte in data:
            tmp = byte ^ (crc & 0xFF)
            tmp ^= (tmp << 4) & 0xFF
            crc = (crc >> 8) ^ (tmp << 8) ^ (tmp << 3) ^ (tmp >> 4)
            crc &= 0xFFFF
        return crc

    def _build_v2(self, msg_id, payload):
        """Build a complete MAVLink v2 frame."""
        payload_len = len(payload)
        header = struct.pack('<BBBBBBBHB',
                             MAVLINK_V2_START,
                             payload_len,
                             0,  # incompat_flags
                             0,  # compat_flags
                             self.seq & 0xFF,
                             self.sysid,
                             self.compid,
                             msg_id & 0xFFFF,
                             (msg_id >> 16) & 0xFF)
        self.seq = (self.seq + 1) & 0xFF

        crc_data = header[1:] + payload
        crc_extra = CRC_EXTRA.get(msg_id, 0)
        crc = self._crc_accumulate(crc_data)
        crc = self._crc_accumulate(bytes([crc_extra]), crc)

        return header + payload + struct.pack('<H', crc)

    def heartbeat(self, custom_mode=0, mav_type=2, autopilot=3,
                  base_mode=0x80 | 0x10, system_status=4, mav_version=3):
        """Build HEARTBEAT (msg 0)."""
        payload = struct.pack('<IBBBBB',
                              custom_mode, mav_type, autopilot,
                              base_mode, system_status, mav_version)
        return self._build_v2(MSG_HEARTBEAT, payload)

    def global_position_int(self, lat, lon, alt_msl, alt_agl,
                             heading=0.0, gs=0.0, vz=0.0):
        """Build GLOBAL_POSITION_INT (msg 33)."""
        time_boot = int(time.monotonic() * 1000) & 0xFFFFFFFF
        hdg = int(heading * 100) if heading >= 0 else 0xFFFF
        vx = int(gs * 100 * math.cos(math.radians(heading)))
        vy = int(gs * 100 * math.sin(math.radians(heading)))
        payload = struct.pack('<IiiiihhhH',
                              time_boot,
                              int(lat * 1e7),
                              int(lon * 1e7),
                              int(alt_msl * 1000),
                              int(alt_agl * 1000),
                              vx, vy, int(vz * 100), hdg)
        return self._build_v2(MSG_GLOBAL_POSITION_INT, payload)

    def gps_raw_int(self, lat, lon, alt, fix_type=3, sats=12,
                     hdop=120, vdop=120):
        """Build GPS_RAW_INT (msg 24)."""
        payload = struct.pack('<QiiiHHBBBB',
                              int(time.time() * 1e6),
                              int(lat * 1e7),
                              int(lon * 1e7),
                              int(alt * 1000),
                              hdop,
                              vdop,
                              fix_type,
                              sats,
                              0, 0)
        return self._build_v2(MSG_GPS_RAW_INT, payload)

    def sys_status(self, voltage=12.6, current=5.0, remaining=75):
        """Build SYS_STATUS (msg 1)."""
        payload = struct.pack('<IIIHHhbHHHHHhH',
                              0x0003FFFF,  # sensors present
                              0x0003FFFF,  # sensors enabled
                              0x0003FFFF,  # sensors health
                              500,         # load (0.5%)
                              int(voltage * 1000),
                              int(current * 100),
                              remaining,
                              0, 0, 0, 0, 0, 0, 0)
        return self._build_v2(MSG_SYS_STATUS, payload)

    def attitude(self, roll=0.0, pitch=0.0, yaw=0.0):
        """Build ATTITUDE (msg 30). Angles in degrees."""
        payload = struct.pack('<Iffffff',
                              int(time.monotonic() * 1000) & 0xFFFFFFFF,
                              math.radians(roll),
                              math.radians(pitch),
                              math.radians(yaw),
                              0.0, 0.0, 0.0)  # roll/pitch/yaw speed
        return self._build_v2(MSG_ATTITUDE, payload)

    def vfr_hud(self, airspeed=0.0, groundspeed=0.0, heading=0,
                throttle=0, alt=0.0, climb=0.0):
        """Build VFR_HUD (msg 74)."""
        payload = struct.pack('<ffffhH',
                              airspeed, groundspeed, float(heading),
                              float(throttle),
                              int(alt), int(climb * 100))
        return self._build_v2(MSG_VFR_HUD, payload)

    def statustext(self, severity=6, text=""):
        """Build STATUSTEXT (msg 253). severity: 0=EMERG..7=DEBUG"""
        text_bytes = text.encode('utf-8', errors='replace')[:50]
        text_bytes = text_bytes.ljust(50, b'\x00')
        payload = struct.pack('B', severity) + text_bytes
        return self._build_v2(MSG_STATUSTEXT, payload)

    def rc_channels(self, channels=None):
        """Build RC_CHANNELS (msg 65) from link stats.

        Encodes RSSI/LQ as virtual RC channel values for display.
        """
        ch = channels or [0] * 18
        while len(ch) < 18:
            ch.append(0)
        ch = ch[:18]

        payload = struct.pack('<I',
                              int(time.monotonic() * 1000) & 0xFFFFFFFF)
        payload += struct.pack('B', 18)  # chancount
        for v in ch:
            payload += struct.pack('<H', max(0, min(65535, v)))
        payload += struct.pack('B', 255)  # rssi (legacy, 255=unknown)
        return self._build_v2(MSG_RC_CHANNELS, payload)


# ===================================================================
# CRSF-to-MAVLink Translator
# ===================================================================

class CRSFToMAVLink:
    """Translate CRSF telemetry state into MAVLink messages.

    Produces a stream of MAVLink packets based on what CRSF data is
    available, at appropriate rates for QGC consumption.
    """

    def __init__(self, vehicle_type='copter'):
        self.builder = MAVLinkBuilder(sysid=1, compid=1)
        self.vehicle_type = vehicle_type

        # Select mode map based on vehicle type
        if vehicle_type == 'plane':
            self.mode_map = PLANE_MODE_MAP
            self.mav_type = 1   # MAV_TYPE_FIXED_WING
        elif vehicle_type == 'rover':
            self.mode_map = ROVER_MODE_MAP
            self.mav_type = 10  # MAV_TYPE_GROUND_ROVER
        else:
            self.mode_map = COPTER_MODE_MAP
            self.mav_type = 2   # MAV_TYPE_QUADROTOR

        # Timing for periodic messages
        self._next_heartbeat = 0
        self._next_position = 0
        self._next_attitude = 0
        self._next_battery = 0
        self._next_link = 0
        self._next_hud = 0

        # Status text tracking
        self._last_mode_sent = ""
        self._last_link_text_time = 0

    def _mode_to_custom(self, mode_str):
        """Convert CRSF flight mode string to MAVLink custom_mode."""
        mode_upper = mode_str.upper().strip()
        custom = self.mode_map.get(mode_upper)
        if custom is not None:
            return custom
        # Try partial match
        for key, val in self.mode_map.items():
            if mode_upper.startswith(key) or key.startswith(mode_upper):
                return val
        return 0  # fallback to mode 0

    def translate(self, state):
        """Generate MAVLink packets from current CRSF state.

        Returns a bytearray of concatenated MAVLink packets to send.
        Call this at ~10-50 Hz for smooth telemetry updates.
        """
        now = time.monotonic()
        out = bytearray()

        # HEARTBEAT at 1 Hz
        if now >= self._next_heartbeat:
            custom_mode = 0
            base_mode = 0x10  # MAV_MODE_FLAG_CUSTOM_MODE_ENABLED
            system_status = 3  # STANDBY

            if state.flight_mode:
                custom_mode = self._mode_to_custom(state.flight_mode)
                # Assume armed if we're receiving telemetry
                base_mode |= 0x80  # MAV_MODE_FLAG_SAFETY_ARMED
                system_status = 4  # ACTIVE

            out.extend(self.builder.heartbeat(
                custom_mode=custom_mode,
                mav_type=self.mav_type,
                autopilot=3,  # ARDUPILOTMEGA
                base_mode=base_mode,
                system_status=system_status,
            ))

            # Send mode change as status text
            if state.flight_mode and state.flight_mode != self._last_mode_sent:
                out.extend(self.builder.statustext(
                    severity=6,  # INFO
                    text="Mode: %s" % state.flight_mode,
                ))
                self._last_mode_sent = state.flight_mode

            self._next_heartbeat = now + 1.0

        # GPS at 5 Hz
        if now >= self._next_position and state.gps_valid:
            out.extend(self.builder.global_position_int(
                lat=state.gps_lat,
                lon=state.gps_lon,
                alt_msl=state.gps_alt,
                alt_agl=state.gps_alt,  # CRSF doesn't distinguish MSL/AGL
                heading=state.gps_heading,
                gs=state.gps_speed,
            ))
            out.extend(self.builder.gps_raw_int(
                lat=state.gps_lat,
                lon=state.gps_lon,
                alt=state.gps_alt,
                fix_type=3 if state.gps_sats >= 4 else (2 if state.gps_sats >= 3 else 1),
                sats=state.gps_sats,
            ))
            out.extend(self.builder.vfr_hud(
                groundspeed=state.gps_speed,
                airspeed=state.gps_speed,
                heading=int(state.gps_heading),
                alt=state.gps_alt,
            ))
            self._next_position = now + 0.2

        # ATTITUDE at 10 Hz
        if now >= self._next_attitude and state.att_valid:
            out.extend(self.builder.attitude(
                roll=state.att_roll,
                pitch=state.att_pitch,
                yaw=state.att_yaw,
            ))
            self._next_attitude = now + 0.1

        # BATTERY at 1 Hz
        if now >= self._next_battery and state.bat_valid:
            out.extend(self.builder.sys_status(
                voltage=state.bat_voltage,
                current=state.bat_current,
                remaining=state.bat_remaining,
            ))
            self._next_battery = now + 1.0

        # LINK STATS as status text at 5 Hz, RC_CHANNELS with RSSI
        if now >= self._next_link and state.link_valid:
            # Encode link quality into RC_CHANNELS (virtual channel values)
            # Map RSSI (-120..0 dBm) to (0..2000) range
            rssi_ch = max(0, min(2000, int((state.rssi_up + 120) * 2000 / 120)))
            lq_ch = int(state.lq * 20)  # 0-100% -> 0-2000
            snr_ch = max(0, min(2000, int((state.snr + 20) * 2000 / 40)))

            out.extend(self.builder.rc_channels(
                channels=[rssi_ch, lq_ch, snr_ch] + [0] * 15,
            ))

            # Periodic link status text (every 5 seconds)
            if now - self._last_link_text_time >= 5.0:
                out.extend(self.builder.statustext(
                    severity=6,  # INFO
                    text="RSSI:%ddBm LQ:%d%% SNR:%ddB TX:%dmW" % (
                        state.rssi_up, state.lq, state.snr, state.tx_power),
                ))
                self._last_link_text_time = now

            self._next_link = now + 0.2

        return bytes(out)


# ===================================================================
# TCP Server
# ===================================================================

class TCPServer:
    """Multi-client TCP server for GCS connections."""

    def __init__(self, host, port, on_client_data=None):
        self.host = host
        self.port = port
        self.on_client_data = on_client_data
        self.server_sock = None
        self.clients = []
        self.clients_lock = threading.Lock()
        self.running = False
        self.client_count = 0

    def start(self):
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_sock.settimeout(1.0)
        self.server_sock.bind((self.host, self.port))
        self.server_sock.listen(5)
        self.running = True

        t = threading.Thread(target=self._accept_loop, daemon=True,
                             name="tcp-accept")
        t.start()
        log("[tcp] Listening on %s:%d" % (self.host, self.port))

    def stop(self):
        self.running = False
        with self.clients_lock:
            for c in self.clients:
                try:
                    c.close()
                except Exception:
                    pass
            self.clients.clear()
        if self.server_sock:
            try:
                self.server_sock.close()
            except Exception:
                pass

    def send_to_all(self, data):
        if not data:
            return
        with self.clients_lock:
            dead = []
            for c in self.clients:
                try:
                    c.sendall(data)
                except (OSError, BrokenPipeError):
                    dead.append(c)
            for c in dead:
                self._remove_client(c)

    def _accept_loop(self):
        while self.running:
            try:
                client_sock, addr = self.server_sock.accept()
            except socket.timeout:
                continue
            except OSError:
                break

            client_sock.settimeout(0.5)
            try:
                client_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            except Exception:
                pass

            with self.clients_lock:
                self.clients.append(client_sock)
                self.client_count = len(self.clients)

            log("[tcp] Client connected: %s:%d (%d total)" %
                (addr[0], addr[1], self.client_count))

            t = threading.Thread(target=self._client_reader,
                                 args=(client_sock, addr),
                                 daemon=True)
            t.start()

    def _client_reader(self, sock, addr):
        while self.running:
            try:
                data = sock.recv(4096)
                if not data:
                    break
                if self.on_client_data:
                    self.on_client_data(data)
            except socket.timeout:
                continue
            except (OSError, ConnectionResetError):
                break

        self._remove_client(sock)
        log("[tcp] Client disconnected: %s:%d (%d total)" %
            (addr[0], addr[1], self.client_count))

    def _remove_client(self, sock):
        with self.clients_lock:
            if sock in self.clients:
                self.clients.remove(sock)
                self.client_count = len(self.clients)
            try:
                sock.close()
            except Exception:
                pass


# ===================================================================
# Logging
# ===================================================================

_LOG_LOCK = threading.Lock()


def log(msg):
    """Thread-safe logging to stderr."""
    with _LOG_LOCK:
        ts = time.strftime("%H:%M:%S")
        sys.stderr.write("[%s] %s\n" % (ts, msg))
        sys.stderr.flush()


def format_status(state, translator, tcp_server, elapsed):
    """Format a status display string."""
    lines = []
    lines.append("")
    lines.append("=" * 64)
    lines.append("  CRSF-to-MAVLink Bridge  |  RadioMaster AX12")
    lines.append("=" * 64)

    mins, secs = divmod(int(elapsed), 60)
    hrs, mins = divmod(mins, 60)
    lines.append("  Uptime: %02d:%02d:%02d  |  CRSF frames: %d  |  TCP clients: %d" %
                 (hrs, mins, secs, state.frames_parsed, tcp_server.client_count))

    # Frame type breakdown
    if state.frames_by_type:
        parts = []
        for ft, count in sorted(state.frames_by_type.items()):
            name = CRSF_TYPE_NAMES.get(ft, "0x%02X" % ft)
            parts.append("%s:%d" % (name, count))
        lines.append("  Types: %s" % "  ".join(parts))

    lines.append("-" * 64)

    # GPS
    if state.gps_valid:
        age = time.monotonic() - state.gps_time
        lines.append("  GPS: %.6f, %.6f  Alt: %.1fm  Sats: %d  [%.0fs ago]" %
                     (state.gps_lat, state.gps_lon, state.gps_alt,
                      state.gps_sats, age))
        lines.append("       Speed: %.1f m/s  Heading: %.0f deg" %
                     (state.gps_speed, state.gps_heading))
    else:
        lines.append("  GPS: waiting...")

    # Battery
    if state.bat_valid:
        age = time.monotonic() - state.bat_time
        lines.append("  Batt: %.1fV  %.1fA  %d%%  Used: %dmAh  [%.0fs ago]" %
                     (state.bat_voltage, state.bat_current,
                      state.bat_remaining, state.bat_capacity, age))
    else:
        lines.append("  Batt: waiting...")

    # Attitude
    if state.att_valid:
        age = time.monotonic() - state.att_time
        lines.append("  Att: R=%.1f  P=%.1f  Y=%.1f  [%.0fs ago]" %
                     (state.att_roll, state.att_pitch, state.att_yaw, age))

    # Flight mode
    if state.flight_mode:
        lines.append("  Mode: %s" % state.flight_mode)

    # Link
    if state.link_valid:
        age = time.monotonic() - state.link_time
        lines.append("  Link: RSSI=%ddBm  LQ=%d%%  SNR=%ddB  TX=%dmW  [%.0fs ago]" %
                     (state.rssi_up, state.lq, state.snr,
                      state.tx_power, age))

    lines.append("=" * 64)
    return "\n".join(lines)


# ===================================================================
# Demo Mode: Synthetic CRSF Data Generator
# ===================================================================

class DemoGenerator:
    """Generate synthetic CRSF telemetry for testing without a live drone.

    Simulates a quadcopter orbiting a point with realistic sensor values.
    """

    def __init__(self):
        self.t0 = time.monotonic()
        # Kitty Hawk, NC - first-flight field, neutral demo location
        self.center_lat = 36.0646
        self.center_lon = -75.7057
        self.orbit_radius = 0.002  # ~220m
        self.orbit_period = 120.0
        self.base_alt = 50.0

    def update(self, state):
        """Update CRSF state with synthetic data."""
        elapsed = time.monotonic() - self.t0
        angle = (elapsed / self.orbit_period) * 2 * math.pi

        # GPS orbit
        lat = self.center_lat + self.orbit_radius * math.sin(angle)
        lon = self.center_lon + self.orbit_radius * math.cos(angle)
        alt = self.base_alt + 5.0 * math.sin(elapsed / 10.0)
        heading = math.degrees(angle + math.pi / 2) % 360
        speed = 2 * math.pi * self.orbit_radius * 111000 / self.orbit_period
        sats = 14

        state.update_gps(lat, lon, alt, speed, heading, sats)

        # Battery drain
        drain_frac = elapsed / 600.0  # drain over 10 minutes
        voltage = max(10.5, 12.6 - drain_frac * 2.1)
        current = 12.0 + 2.0 * math.sin(elapsed / 15.0)
        capacity = int(drain_frac * 2200)
        remaining = max(0, int(100 - drain_frac * 100))

        state.update_battery(voltage, current, capacity, remaining)

        # Attitude wobble
        roll = 5.0 * math.sin(elapsed / 3.0)
        pitch = 3.0 * math.cos(elapsed / 4.0)
        yaw = heading

        state.update_attitude(pitch, roll, yaw)

        # Flight mode cycling
        modes = ["LOITER", "AUTO", "RTL", "LOITER", "POSHOLD"]
        mode_idx = int(elapsed / 30.0) % len(modes)
        state.update_flight_mode(modes[mode_idx])

        # Link stats
        rssi = -65 + int(10 * math.sin(elapsed / 20.0))
        lq = max(50, min(100, 95 + int(5 * math.cos(elapsed / 8.0))))
        snr = 8 + int(3 * math.sin(elapsed / 12.0))

        state.update_link_stats(
            rssi_up=rssi,
            rssi_down=rssi - 5,
            lq=lq,
            snr=snr,
            rf_mode=4,  # 150 Hz
            tx_power=100,
        )


# ===================================================================
# Live Mode: strace-based CRSF extraction
# ===================================================================

def find_tty_pid():
    """Find the PID of the process holding /dev/ttyS0."""
    import glob as glob_mod

    for fd_dir in glob_mod.glob('/proc/*/fd'):
        try:
            pid = fd_dir.split('/')[2]
            if not pid.isdigit():
                continue
            for fd_link in glob_mod.glob('%s/*' % fd_dir):
                try:
                    target = os.readlink(fd_link)
                    if '/dev/ttyS0' in target:
                        return pid
                except (OSError, PermissionError):
                    continue
        except (OSError, PermissionError):
            continue
    return None


def strace_reader(state, running_flag, verbose=False):
    """Read UMBUS frames from strace and extract CRSF telemetry.

    Runs strace attached to the Flyshark process and parses the
    serial data it reads from /dev/ttyS0.
    """
    # Check root
    if os.geteuid() != 0:
        log("ERROR: Live mode requires root (for strace)")
        log("Run with: su 0 python3 crsf_mavlink.py live")
        running_flag.clear()
        return

    pid = find_tty_pid()
    if not pid:
        log("ERROR: No process found with /dev/ttyS0 open")
        log("Is the FlyShark app running?")
        running_flag.clear()
        return

    log("Found ttyS0 held by PID %s" % pid)

    cmd = ['strace', '-p', pid, '-e', 'trace=read',
           '-e', 'read=3,4,5,6,7,8,9,10', '-s', '256', '-x']

    hex_pattern = re.compile(r'\\x([0-9a-fA-F]{2})')
    decoder = UMBUSDecoder()
    frames_extracted = 0

    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                bufsize=1, universal_newlines=True)

        log("strace attached to PID %s" % pid)

        for line in proc.stderr:
            if not running_flag.is_set():
                break

            if 'read(' not in line and '|' not in line:
                continue

            # Extract hex bytes from strace output
            hex_matches = hex_pattern.findall(line)
            if not hex_matches:
                parts = line.strip().split()
                hex_bytes = []
                for p in parts:
                    if len(p) == 2:
                        try:
                            hex_bytes.append(int(p, 16))
                        except ValueError:
                            continue
                if hex_bytes:
                    raw = bytes(hex_bytes)
                else:
                    continue
            else:
                raw = bytes(int(h, 16) for h in hex_matches)

            # Parse UMBUS frames and extract CRSF
            for frame in decoder.feed(raw):
                if frame.frame_type == FrameType.ELRS_TELEM:
                    if extract_crsf_from_umbus(frame, state):
                        frames_extracted += 1
                        if verbose and frames_extracted % 100 == 0:
                            log("Extracted %d CRSF frames" % frames_extracted)

    except KeyboardInterrupt:
        pass
    except Exception as e:
        log("strace error: %s" % e)
    finally:
        try:
            proc.terminate()
            proc.wait(timeout=2)
        except Exception:
            pass
        log("strace reader stopped (%d CRSF frames extracted)" % frames_extracted)


# ===================================================================
# Main Bridge Loop
# ===================================================================

def run_bridge(mode, args):
    """Main bridge loop: read CRSF, translate to MAVLink, serve on TCP."""
    running = threading.Event()
    running.set()

    state = CRSFTelemetry()
    translator = CRSFToMAVLink(vehicle_type=args.vehicle)
    tcp = TCPServer(args.tcp_host, args.tcp_port)
    demo_gen = None

    def signal_handler(signum, frame):
        log("Signal %d received, shutting down..." % signum)
        running.clear()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Banner
    log("=" * 60)
    log("  CRSF-to-MAVLink Bridge  |  RadioMaster AX12")
    log("  Mode: %s  |  Vehicle: %s" % (mode, args.vehicle))
    log("  TCP: %s:%d" % (args.tcp_host, args.tcp_port))
    log("=" * 60)

    # Start TCP server
    tcp.start()

    if mode == 'demo':
        demo_gen = DemoGenerator()
        log("Demo mode: generating synthetic CRSF telemetry")
        log("Connect QGC to TCP %s:%d" % (args.tcp_host, args.tcp_port))
        if args.duration > 0:
            log("Running for %d seconds" % args.duration)
    elif mode == 'live':
        # Start strace reader in background thread
        reader_thread = threading.Thread(
            target=strace_reader,
            args=(state, running, args.verbose),
            daemon=True,
            name="strace-reader",
        )
        reader_thread.start()
        log("Live mode: snooping CRSF from Flyshark via strace")
        log("Connect QGC to TCP %s:%d" % (args.tcp_host, args.tcp_port))

    t0 = time.monotonic()
    last_display = 0
    translate_interval = 0.02  # 50 Hz translation loop
    next_translate = time.monotonic()

    try:
        while running.is_set():
            now = time.monotonic()
            elapsed = now - t0

            if args.duration > 0 and elapsed >= args.duration:
                log("Duration %ds reached, shutting down" % args.duration)
                break

            # Update synthetic data in demo mode
            if demo_gen:
                demo_gen.update(state)

            # Translate CRSF to MAVLink
            if now >= next_translate:
                mavlink_data = translator.translate(state)
                if mavlink_data:
                    tcp.send_to_all(mavlink_data)
                next_translate = now + translate_interval

            # Periodic status display
            if now - last_display >= args.display:
                status = format_status(state, translator, tcp, elapsed)
                sys.stderr.write(status + "\n")
                sys.stderr.flush()
                last_display = now

            # Sleep to next event
            sleep_time = max(0, next_translate - time.monotonic())
            if sleep_time > 0:
                time.sleep(min(sleep_time, 0.01))

    except KeyboardInterrupt:
        pass
    finally:
        running.clear()
        tcp.stop()
        log("Bridge shutdown. %d CRSF frames processed." % state.frames_parsed)


# ===================================================================
# CLI Entry Point
# ===================================================================

def main():
    parser = argparse.ArgumentParser(
        prog='crsf_mavlink',
        description=(
            'CRSF-to-MAVLink telemetry bridge for RadioMaster AX12.\n'
            'Translates ELRS CRSF telemetry into MAVLink for QGC.'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  # Live mode (requires root for strace):\n"
            "  su 0 python3 crsf_mavlink.py live\n"
            "\n"
            "  # Demo mode (synthetic data, no drone needed):\n"
            "  python3 crsf_mavlink.py --demo\n"
            "  python3 crsf_mavlink.py --demo --duration 30\n"
            "\n"
            "  # Custom TCP port:\n"
            "  python3 crsf_mavlink.py --demo --tcp-port 5761\n"
            "\n"
            "  # Specify vehicle type (affects mode mapping):\n"
            "  python3 crsf_mavlink.py live --vehicle plane\n"
            "\n"
            "QGC Connection:\n"
            "  In QGroundControl, add a TCP comm link:\n"
            "    Host: 127.0.0.1\n"
            "    Port: 5760\n"
        ),
    )

    parser.add_argument('mode', nargs='?', default=None,
                        choices=['live', 'demo'],
                        help='Operating mode: live (strace) or demo (synthetic)')
    parser.add_argument('--demo', action='store_true',
                        help='Shorthand for demo mode')
    parser.add_argument('--tcp-host', default='0.0.0.0',
                        help='TCP listen address (default: 0.0.0.0)')
    parser.add_argument('--tcp-port', type=int, default=5760,
                        help='TCP listen port (default: 5760)')
    parser.add_argument('--vehicle', default='copter',
                        choices=['copter', 'plane', 'rover'],
                        help='Vehicle type for mode mapping (default: copter)')
    parser.add_argument('--duration', type=float, default=0,
                        help='Auto-stop after N seconds (0=run forever)')
    parser.add_argument('--display', type=float, default=2.0,
                        help='Status display interval in seconds (default: 2)')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Verbose logging')

    args = parser.parse_args()

    # Resolve mode
    if args.demo:
        mode = 'demo'
    elif args.mode:
        mode = args.mode
    else:
        parser.print_help()
        sys.exit(1)

    run_bridge(mode, args)


if __name__ == '__main__':
    main()
