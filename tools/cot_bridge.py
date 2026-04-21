#!/data/data/com.termux/files/usr/bin/python3
"""
MAVLink → CoT Bridge for ATAK and TAK Servers

Reads MAVLink telemetry from /dev/ttyS1 (ELRS MAVLink passthrough) and
fans out Cursor-on-Target (CoT) XML to one or more sinks:

- Local UDP (default)     — e.g. ATAK on the AX12 itself at 127.0.0.1:4242
- TAK Server over TCP      — newline-framed CoT, persistent with reconnect
- TAK Server over TLS      — same framing, with client-cert mutual TLS

CoT type: a-f-A-M-F-Q (friendly air military fixed-wing UAV) for fixed-wing,
a-f-A-M-H-Q for rotary. One failing sink does not block the others.

Usage:
    su 0 python3 tools/cot_bridge.py              # live serial + local UDP
    su 0 python3 tools/cot_bridge.py --test        # synthetic test data
    su 0 python3 tools/cot_bridge.py --tak-server tak.local:8087
    su 0 python3 tools/cot_bridge.py --tak-server tak.local:8089 --tak-tls \\
         --tak-cert cert.pem --tak-key cert.pem --tak-ca ca.pem

Requires root for serial access. Stdlib only.
"""

import argparse
import os
import queue
import select
import signal
import socket
import ssl
import struct
import sys
import threading
import time
import uuid

try:
    import termios
except ImportError:
    termios = None


# ===================================================================
# MAVLink Constants
# ===================================================================

MAVLINK_V1_START = 0xFE
MAVLINK_V2_START = 0xFD

# Message IDs we care about
MSG_HEARTBEAT = 0
MSG_GLOBAL_POSITION_INT = 33

# MAVLink v1 header: start, payload_len, seq, sysid, compid, msgid
MAVLINK_V1_HEADER_LEN = 6
MAVLINK_V1_CRC_LEN = 2

# MAVLink v2 header: start, payload_len, incompat, compat, seq, sysid, compid, msgid(3B)
MAVLINK_V2_HEADER_LEN = 10
MAVLINK_V2_CRC_LEN = 2

# CRC extra bytes for checksum validation (per message type)
CRC_EXTRA = {
    MSG_HEARTBEAT: 50,
    MSG_GLOBAL_POSITION_INT: 104,
}

# MAVLink flight mode mapping (ArduCopter custom_mode values)
COPTER_MODES = {
    0: "STABILIZE", 1: "ACRO", 2: "ALT_HOLD", 3: "AUTO",
    4: "GUIDED", 5: "LOITER", 6: "RTL", 7: "CIRCLE",
    9: "LAND", 11: "DRIFT", 13: "SPORT", 14: "FLIP",
    15: "AUTOTUNE", 16: "POSHOLD", 17: "BRAKE", 18: "THROW",
    19: "AVOID_ADSB", 20: "GUIDED_NOGPS", 21: "SMART_RTL",
    22: "FLOWHOLD", 23: "FOLLOW", 24: "ZIGZAG", 25: "SYSTEMID",
    26: "AUTOROTATE", 27: "AUTO_RTL",
}

# MAVLink system type for type field mapping
MAV_TYPE_FIXED_WING = 1
MAV_TYPE_QUADROTOR = 2
MAV_TYPE_HEXAROTOR = 13
MAV_TYPE_OCTOROTOR = 14
MAV_TYPE_TRICOPTER = 15

_ROTARY_TYPES = {
    MAV_TYPE_QUADROTOR, MAV_TYPE_HEXAROTOR,
    MAV_TYPE_OCTOROTOR, MAV_TYPE_TRICOPTER,
}


def cot_type_for(mav_type):
    """Map MAV_TYPE → CoT 2525 type. Defaults to friendly air UAV."""
    if mav_type == MAV_TYPE_FIXED_WING:
        return "a-f-A-M-F-Q"   # friendly air military fixed-wing UAV
    if mav_type in _ROTARY_TYPES:
        return "a-f-A-M-H-Q"   # friendly air military rotary-wing UAV
    return "a-f-A-M-F-Q"


# ===================================================================
# MAVLink CRC (X.25 / CCITT)
# ===================================================================

def _crc_accumulate(byte: int, crc: int) -> int:
    tmp = (byte ^ (crc & 0xFF)) & 0xFF
    tmp = (tmp ^ (tmp << 4)) & 0xFF
    return ((crc >> 8) ^ (tmp << 8) ^ (tmp << 3) ^ (tmp >> 4)) & 0xFFFF


def mavlink_crc(data: bytes, crc_extra: int) -> int:
    """X.25 CRC over the frame (excluding start byte), seeded with crc_extra."""
    crc = 0xFFFF
    for b in data:
        crc = _crc_accumulate(b, crc)
    return _crc_accumulate(crc_extra, crc)


# ===================================================================
# MAVLink Parser
# ===================================================================

class MAVLinkFrame:
    """Parsed MAVLink frame."""

    __slots__ = ('version', 'msg_id', 'sysid', 'compid', 'payload')

    def __init__(self, version: int, msg_id: int, sysid: int,
                 compid: int, payload: bytes):
        self.version = version
        self.msg_id = msg_id
        self.sysid = sysid
        self.compid = compid
        self.payload = payload


class MAVLinkParser:
    """Incremental MAVLink v1/v2 frame parser.

    Feed raw bytes via feed(). Yields complete MAVLinkFrame objects.
    Handles stream synchronization and resync on corruption.
    """

    def __init__(self):
        self._buf = bytearray()

    def feed(self, data: bytes):
        """Feed raw bytes; yield parsed MAVLinkFrame objects."""
        self._buf.extend(data)

        while True:
            # Find next start byte
            v1_pos = self._find_byte(MAVLINK_V1_START)
            v2_pos = self._find_byte(MAVLINK_V2_START)

            if v1_pos < 0 and v2_pos < 0:
                # No start bytes — discard buffer except last byte
                if len(self._buf) > 1:
                    self._buf = self._buf[-1:]
                return

            # Pick whichever start byte comes first
            if v1_pos < 0:
                start_pos = v2_pos
            elif v2_pos < 0:
                start_pos = v1_pos
            else:
                start_pos = min(v1_pos, v2_pos)

            # Discard bytes before start
            if start_pos > 0:
                del self._buf[:start_pos]

            start_byte = self._buf[0]

            if start_byte == MAVLINK_V1_START:
                frame = self._try_parse_v1()
            else:
                frame = self._try_parse_v2()

            if frame is None:
                return  # Need more data
            if frame is False:
                # Bad CRC or unknown msg — skip this start byte and resync.
                del self._buf[:1]
                continue
            yield frame

    def _find_byte(self, byte: int) -> int:
        try:
            return self._buf.index(byte)
        except ValueError:
            return -1

    def _try_parse_v1(self):
        """Try to parse a MAVLink v1 frame from buffer start.

        Returns a frame on success, False on bad CRC / unknown msg (caller
        should advance 1 byte and resync), or None if more data is needed.
        """
        if len(self._buf) < MAVLINK_V1_HEADER_LEN:
            return None

        payload_len = self._buf[1]
        frame_len = MAVLINK_V1_HEADER_LEN + payload_len + MAVLINK_V1_CRC_LEN

        if len(self._buf) < frame_len:
            return None

        raw = bytes(self._buf[:frame_len])
        msg_id = raw[5]
        crc_extra = CRC_EXTRA.get(msg_id)
        if crc_extra is None:
            return False  # can't validate unknown msg; resync

        expected = mavlink_crc(raw[1:MAVLINK_V1_HEADER_LEN + payload_len], crc_extra)
        actual = raw[-2] | (raw[-1] << 8)
        if expected != actual:
            return False

        del self._buf[:frame_len]
        payload = raw[MAVLINK_V1_HEADER_LEN:MAVLINK_V1_HEADER_LEN + payload_len]
        return MAVLinkFrame(
            version=1,
            msg_id=msg_id,
            sysid=raw[3],
            compid=raw[4],
            payload=payload,
        )

    def _try_parse_v2(self):
        """Try to parse a MAVLink v2 frame from buffer start.

        Same return protocol as _try_parse_v1. Signed v2 frames (incompat
        flag 0x01) are consumed and dropped — we don't verify signatures.
        """
        if len(self._buf) < MAVLINK_V2_HEADER_LEN:
            return None

        payload_len = self._buf[1]
        incompat = self._buf[2]
        sig_len = 13 if (incompat & 0x01) else 0
        frame_len = MAVLINK_V2_HEADER_LEN + payload_len + MAVLINK_V2_CRC_LEN + sig_len

        if len(self._buf) < frame_len:
            return None

        raw = bytes(self._buf[:frame_len])
        msg_id = raw[7] | (raw[8] << 8) | (raw[9] << 16)

        crc_extra = CRC_EXTRA.get(msg_id)
        if crc_extra is None:
            return False

        crc_end = MAVLINK_V2_HEADER_LEN + payload_len
        expected = mavlink_crc(raw[1:crc_end], crc_extra)
        actual = raw[crc_end] | (raw[crc_end + 1] << 8)
        if expected != actual:
            return False

        del self._buf[:frame_len]
        payload = raw[MAVLINK_V2_HEADER_LEN:crc_end]
        return MAVLinkFrame(
            version=2,
            msg_id=msg_id,
            sysid=raw[5],
            compid=raw[6],
            payload=payload,
        )


# ===================================================================
# MAVLink Message Decoders
# ===================================================================

def decode_global_position_int(payload: bytes) -> dict:
    """Decode GLOBAL_POSITION_INT (msg 33).

    Payload layout (28 bytes):
        uint32 time_boot_ms
        int32  lat          (degE7)
        int32  lon          (degE7)
        int32  alt          (mm, MSL)
        int32  relative_alt (mm, AGL)
        int16  vx           (cm/s, north)
        int16  vy           (cm/s, east)
        int16  vz           (cm/s, down)
        uint16 hdg          (cdeg, 0-35999, UINT16_MAX if unknown)
    """
    if len(payload) < 28:
        return {}

    fields = struct.unpack('<IiiiihhhH', payload[:28])
    time_boot_ms, lat, lon, alt, rel_alt, vx, vy, vz, hdg = fields

    groundspeed = (vx ** 2 + vy ** 2) ** 0.5 / 100.0  # m/s

    return {
        'lat': lat / 1e7,
        'lon': lon / 1e7,
        'alt_msl': alt / 1000.0,
        'alt_agl': rel_alt / 1000.0,
        'groundspeed': groundspeed,
        'heading': hdg / 100.0 if hdg != 0xFFFF else 0.0,
        'vz': vz / 100.0,
    }


def decode_heartbeat(payload: bytes) -> dict:
    """Decode HEARTBEAT (msg 0).

    Payload layout (9 bytes):
        uint32 custom_mode
        uint8  type
        uint8  autopilot
        uint8  base_mode
        uint8  system_status
        uint8  mavlink_version
    """
    if len(payload) < 9:
        return {}

    custom_mode, mav_type, autopilot, base_mode, status, _ = \
        struct.unpack('<IBBBBB', payload[:9])

    armed = bool(base_mode & 0x80)
    mode_name = COPTER_MODES.get(custom_mode, f"MODE_{custom_mode}")

    return {
        'mav_type': mav_type,
        'armed': armed,
        'flight_mode': mode_name,
        'system_status': status,
    }


# ===================================================================
# CoT XML Formatter
# ===================================================================

def format_cot_xml(lat: float, lon: float, alt: float, heading: float,
                   speed: float, flight_mode: str, armed: bool,
                   uid: str = "ELRS-Drone-1",
                   cot_type: str = "a-f-A-M-F-Q",
                   stale_seconds: int = 10) -> str:
    """Build a CoT event XML string for ATAK.

    CoT type breakdown: a-f-A-M-F-Q
        a = atom (concrete entity)
        f = friend
        A = Air
        M = Military
        F = Fixed-wing (generic air vehicle)
        Q = UAV/drone

    Args:
        lat: Latitude in decimal degrees (WGS84).
        lon: Longitude in decimal degrees (WGS84).
        alt: Altitude in meters (HAE / MSL).
        heading: Heading in degrees (0-360).
        speed: Ground speed in m/s.
        flight_mode: Current autopilot flight mode string.
        armed: Whether the vehicle is armed.
        uid: CoT UID string for this entity.
        cot_type: CoT 2525C type string.
        stale_seconds: Seconds until the track goes stale on the map.
    """
    now = time.time()
    time_str = _iso8601(now)
    stale_str = _iso8601(now + stale_seconds)

    # ce/le = circular/linear error in meters (95% confidence)
    ce = "10.0"
    le = "10.0"

    status = "Armed" if armed else "Disarmed"
    remarks = f"{flight_mode} | {status} | {speed:.1f}m/s | {alt:.0f}m MSL"

    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<event version="2.0" uid="{uid}" type="{cot_type}" '
        f'time="{time_str}" start="{time_str}" stale="{stale_str}" '
        f'how="m-g">'
        f'<point lat="{lat:.7f}" lon="{lon:.7f}" hae="{alt:.1f}" '
        f'ce="{ce}" le="{le}"/>'
        f'<detail>'
        f'<track course="{heading:.1f}" speed="{speed:.2f}"/>'
        f'<remarks>{remarks}</remarks>'
        f'<contact callsign="{uid}"/>'
        f'<__group name="Cyan" role="Team Member"/>'
        f'</detail>'
        f'</event>'
    )
    return xml


def _iso8601(timestamp: float) -> str:
    """Format a Unix timestamp as ISO 8601 UTC string for CoT."""
    t = time.gmtime(timestamp)
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", t)


# ===================================================================
# Serial Port Setup
# ===================================================================

def open_serial(port: str, baudrate: int) -> int:
    """Open a serial port using raw termios. Returns file descriptor.

    Configures 8N1, no flow control, raw mode (no line discipline).
    """
    if termios is None:
        raise RuntimeError("termios not available on this platform")

    fd = os.open(port, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)

    # Map baudrate to termios constant
    baud_map = {
        9600: termios.B9600,
        19200: termios.B19200,
        38400: termios.B38400,
        57600: termios.B57600,
        115200: termios.B115200,
        230400: termios.B230400,
        460800: termios.B460800,
        921600: termios.B921600,
    }

    speed = baud_map.get(baudrate)
    if speed is None:
        os.close(fd)
        raise ValueError(f"Unsupported baudrate: {baudrate}")

    attrs = termios.tcgetattr(fd)

    # Input flags: no parity, no flow control, no CR translation
    attrs[0] = 0  # iflag
    # Output flags: raw
    attrs[1] = 0  # oflag
    # Control flags: 8N1, enable receiver, local mode
    attrs[2] = termios.CS8 | termios.CREAD | termios.CLOCAL | speed
    # Local flags: raw (no echo, no signals, no canonical)
    attrs[3] = 0  # lflag
    # Control characters
    attrs[6][termios.VMIN] = 0
    attrs[6][termios.VTIME] = 1  # 100ms timeout

    # Set input and output speed
    attrs[4] = speed  # ispeed
    attrs[5] = speed  # ospeed

    termios.tcsetattr(fd, termios.TCSANOW, attrs)
    termios.tcflush(fd, termios.TCIOFLUSH)

    return fd


# ===================================================================
# Synthetic Test Data Generator
# ===================================================================

class SyntheticSource:
    """Generate synthetic MAVLink-like position data for testing.

    Produces a slow orbit around (0, 0) — null island — so ATAK
    displays a moving track without needing a real receiver.
    """

    def __init__(self):
        self.t0 = time.monotonic()
        self.armed = True
        self.flight_mode = "LOITER"

    def get_position(self) -> dict:
        """Return a synthetic position dict matching decode_global_position_int output."""
        elapsed = time.monotonic() - self.t0

        # Orbit: 0.001 degree radius (~111m) at null island, period ~60s
        import math
        angle = (elapsed / 60.0) * 2 * math.pi
        lat = 0.001 * math.sin(angle)
        lon = 0.001 * math.cos(angle)
        alt = 100.0 + 10.0 * math.sin(elapsed / 15.0)

        return {
            'lat': lat,
            'lon': lon,
            'alt_msl': alt,
            'alt_agl': alt,
            'groundspeed': 5.0,
            'heading': (angle * 180.0 / math.pi + 90.0) % 360.0,
            'vz': 0.0,
        }

    def get_heartbeat(self) -> dict:
        return {
            'mav_type': MAV_TYPE_QUADROTOR,
            'armed': self.armed,
            'flight_mode': self.flight_mode,
            'system_status': 4,  # MAV_STATE_ACTIVE
        }


# ===================================================================
# Sinks — destinations for CoT datagrams
# ===================================================================
#
# The bridge fans out each CoT event to every configured sink. A failure
# in one sink never blocks or drops delivery to the others. Transport
# details (datagram vs stream, framing, TLS, reconnect) are encapsulated
# here so the bridge loop stays simple.


class Sink:
    """Abstract CoT destination. Subclasses implement send/close."""

    name = "sink"

    def send(self, xml_bytes: bytes) -> None:
        raise NotImplementedError

    def close(self) -> None:
        pass


class UdpSink(Sink):
    """UDP datagram to a local/multicast ATAK listener. Stateless."""

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.name = f"udp://{host}:{port}"
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def send(self, xml_bytes: bytes) -> None:
        self._sock.sendto(xml_bytes, (self.host, self.port))

    def close(self) -> None:
        try:
            self._sock.close()
        except OSError:
            pass


class TcpSink(Sink):
    """Persistent TCP connection to a TAK Server.

    A background daemon thread owns the socket. Callers of send() put bytes
    on a bounded queue and return immediately — the bridge loop is never
    blocked by a slow upstream. The worker drains the queue, writes each
    event with a trailing newline (TAK Server framing), and reconnects
    with exponential backoff on any socket error.
    """

    QUEUE_MAX = 64
    BACKOFF_MIN = 1.0
    BACKOFF_MAX = 30.0
    CONNECT_TIMEOUT = 10.0

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.name = f"tcp://{host}:{port}"
        self._queue: queue.Queue = queue.Queue(maxsize=self.QUEUE_MAX)
        self._stop = threading.Event()
        self._thread = threading.Thread(
            target=self._worker, daemon=True,
            name=f"sink-{self.name}")
        self._thread.start()

    def send(self, xml_bytes: bytes) -> None:
        # Drop oldest if the queue is full. The bridge keeps running even if
        # the TAK server is unreachable; old positions are stale anyway.
        try:
            self._queue.put_nowait(xml_bytes)
        except queue.Full:
            try:
                self._queue.get_nowait()
            except queue.Empty:
                pass
            try:
                self._queue.put_nowait(xml_bytes)
            except queue.Full:
                pass

    def close(self) -> None:
        self._stop.set()
        # Wake the worker if it's blocked on queue.get
        try:
            self._queue.put_nowait(b'')
        except queue.Full:
            pass

    def _connect(self) -> socket.socket:
        """Open a fresh TCP socket. Override for TLS."""
        sock = socket.create_connection(
            (self.host, self.port), timeout=self.CONNECT_TIMEOUT)
        sock.settimeout(None)
        return sock

    def _worker(self):
        backoff = self.BACKOFF_MIN
        sock = None
        while not self._stop.is_set():
            if sock is None:
                try:
                    print(f"[cot_bridge] {self.name} connecting...")
                    sock = self._connect()
                    print(f"[cot_bridge] {self.name} connected")
                    backoff = self.BACKOFF_MIN
                except (OSError, ssl.SSLError) as e:
                    print(f"[cot_bridge] {self.name} connect failed: {e}; "
                          f"retry in {backoff:.0f}s")
                    if self._stop.wait(backoff):
                        break
                    backoff = min(backoff * 2, self.BACKOFF_MAX)
                    continue

            try:
                payload = self._queue.get(timeout=1.0)
            except queue.Empty:
                continue
            if not payload or self._stop.is_set():
                break

            try:
                sock.sendall(payload + b'\n')
            except (OSError, ssl.SSLError) as e:
                print(f"[cot_bridge] {self.name} send failed: {e}; reconnecting")
                try:
                    sock.close()
                except OSError:
                    pass
                sock = None
                # Keep the frame if there's room; otherwise drop it. The next
                # periodic send will carry a fresh position anyway.
                try:
                    self._queue.put_nowait(payload)
                except queue.Full:
                    pass

        if sock is not None:
            try:
                sock.close()
            except OSError:
                pass


class TlsSink(TcpSink):
    """TCP with TLS (PEM cert/key). Same framing and reconnect as TcpSink.

    Convert a TAK mission-package .p12 to PEM with:
        openssl pkcs12 -in mp.p12 -out cert.pem -nodes
    Then pass --tak-cert cert.pem --tak-key cert.pem.
    """

    def __init__(self, host: str, port: int,
                 certfile: str, keyfile: str, cafile=None):
        self.certfile = certfile
        self.keyfile = keyfile
        self.cafile = cafile
        super().__init__(host, port)
        self.name = f"tls://{host}:{port}"

    def _connect(self) -> socket.socket:
        ctx = ssl.create_default_context(cafile=self.cafile)
        ctx.load_cert_chain(certfile=self.certfile, keyfile=self.keyfile)
        raw = socket.create_connection(
            (self.host, self.port), timeout=self.CONNECT_TIMEOUT)
        try:
            sock = ctx.wrap_socket(raw, server_hostname=self.host)
        except (OSError, ssl.SSLError):
            raw.close()
            raise
        sock.settimeout(None)
        return sock


# ===================================================================
# Main Bridge Loop
# ===================================================================

class CoTBridge:
    """Bridges MAVLink telemetry to ATAK CoT over UDP.

    Reads MAVLink frames from serial (or synthetic source in test mode),
    maintains current vehicle state, and emits CoT XML at a fixed rate.
    """

    def __init__(self, serial_port: str, baudrate: int, sinks,
                 uid: str, send_interval: float, test_mode: bool):
        self.serial_port = serial_port
        self.baudrate = baudrate
        self.sinks = list(sinks)
        self.uid = uid
        self.send_interval = send_interval
        self.test_mode = test_mode

        self.running = False
        self.serial_fd = -1
        self.parser = MAVLinkParser()

        # Current vehicle state
        self.position = None  # dict from decode_global_position_int
        self.heartbeat = None  # dict from decode_heartbeat
        self.last_position_time = 0.0
        self.last_send_time = 0.0
        self.frames_parsed = 0

        # Fallback: synthetic source activates after timeout with no serial data
        self.synthetic = SyntheticSource()
        self.serial_timeout = 5.0  # seconds before falling back to synthetic

    def run(self):
        """Main loop. Blocks until shutdown."""
        self.running = True
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        sinks_desc = ", ".join(s.name for s in self.sinks) or "none"
        if self.test_mode:
            print(f"[cot_bridge] TEST MODE — sending synthetic data to {sinks_desc}")
            self._run_test_mode()
            self._close_sinks()
            return

        # Open serial port
        try:
            self.serial_fd = open_serial(self.serial_port, self.baudrate)
            print(f"[cot_bridge] Opened {self.serial_port} at {self.baudrate} baud")
        except (OSError, RuntimeError) as e:
            print(f"[cot_bridge] Serial open failed: {e}")
            print(f"[cot_bridge] Falling back to synthetic data")
            self._run_test_mode()
            self._close_sinks()
            return

        print(f"[cot_bridge] Sending CoT to {sinks_desc} every {self.send_interval}s")
        print(f"[cot_bridge] UID: {self.uid}")
        print(f"[cot_bridge] Ctrl+C to stop")

        try:
            self._run_serial_mode()
        finally:
            if self.serial_fd >= 0:
                os.close(self.serial_fd)
                print(f"[cot_bridge] Closed {self.serial_port}")
            self._close_sinks()
            print(f"[cot_bridge] Shutdown complete ({self.frames_parsed} frames parsed)")

    def _close_sinks(self):
        for sink in self.sinks:
            try:
                sink.close()
            except Exception as e:
                print(f"[cot_bridge] error closing {sink.name}: {e}")

    def _run_serial_mode(self):
        """Read serial data and send CoT."""
        while self.running:
            # Poll serial with 200ms timeout
            try:
                readable, _, _ = select.select([self.serial_fd], [], [], 0.2)
            except (OSError, ValueError):
                break

            if readable:
                try:
                    data = os.read(self.serial_fd, 512)
                except OSError:
                    data = b''

                if data:
                    for frame in self.parser.feed(data):
                        self._handle_mavlink_frame(frame)

            # Send CoT at the configured interval
            now = time.monotonic()
            if now - self.last_send_time >= self.send_interval:
                self._send_cot()
                self.last_send_time = now

    def _run_test_mode(self):
        """Send synthetic CoT data."""
        while self.running:
            self.position = self.synthetic.get_position()
            self.heartbeat = self.synthetic.get_heartbeat()
            self._send_cot()
            self.last_send_time = time.monotonic()

            # Sleep in small increments so Ctrl+C is responsive
            deadline = time.monotonic() + self.send_interval
            while self.running and time.monotonic() < deadline:
                time.sleep(0.1)

    def _handle_mavlink_frame(self, frame: MAVLinkFrame):
        """Process a parsed MAVLink frame."""
        self.frames_parsed += 1

        if frame.msg_id == MSG_GLOBAL_POSITION_INT:
            pos = decode_global_position_int(frame.payload)
            if pos:
                self.position = pos
                self.last_position_time = time.monotonic()

        elif frame.msg_id == MSG_HEARTBEAT:
            hb = decode_heartbeat(frame.payload)
            if hb and hb.get('mav_type', 0) != 6:  # skip GCS heartbeats (type 6)
                self.heartbeat = hb

    def _send_cot(self):
        """Build and send a CoT datagram if we have position data."""
        now = time.monotonic()

        # Use live data, or fall back to synthetic if serial is stale
        pos = self.position
        hb = self.heartbeat

        if pos is None or (not self.test_mode and
                           now - self.last_position_time > self.serial_timeout):
            # Fallback to synthetic
            pos = self.synthetic.get_position()
            if hb is None:
                hb = self.synthetic.get_heartbeat()
            if not self.test_mode:
                suffix = " (synthetic fallback)"
            else:
                suffix = ""
        else:
            suffix = ""

        if hb is None:
            hb = {'armed': False, 'flight_mode': 'UNKNOWN'}

        xml = format_cot_xml(
            lat=pos['lat'],
            lon=pos['lon'],
            alt=pos['alt_msl'],
            heading=pos.get('heading', 0.0),
            speed=pos.get('groundspeed', 0.0),
            flight_mode=hb.get('flight_mode', 'UNKNOWN'),
            armed=hb.get('armed', False),
            uid=self.uid,
            cot_type=cot_type_for(hb.get('mav_type')),
        )

        xml_bytes = xml.encode('utf-8')
        failures = []
        for sink in self.sinks:
            try:
                sink.send(xml_bytes)
            except Exception as e:
                failures.append(f"{sink.name}: {e}")

        lat_s = f"{pos['lat']:.5f}"
        lon_s = f"{pos['lon']:.5f}"
        alt_s = f"{pos['alt_msl']:.0f}m"
        mode = hb.get('flight_mode', '?')
        print(f"[cot_bridge] CoT sent: {lat_s},{lon_s} {alt_s} "
              f"{mode}{suffix}")
        for msg in failures:
            print(f"[cot_bridge] sink error: {msg}")

    def _signal_handler(self, signum, frame):
        print(f"\n[cot_bridge] Signal {signum} received, shutting down...")
        self.running = False


# ===================================================================
# CLI
# ===================================================================

def _parse_host_port(value: str, flag: str):
    """Parse HOST:PORT, returning (host, port_int). Raises ValueError on malformed input."""
    host, sep, port_str = value.rpartition(':')
    if not sep or not host or not port_str:
        raise ValueError(f"{flag} must be HOST:PORT (got {value!r})")
    try:
        port = int(port_str)
    except ValueError as e:
        raise ValueError(f"{flag} port must be an integer (got {port_str!r})") from e
    if not (0 < port < 65536):
        raise ValueError(f"{flag} port out of range: {port}")
    return host, port


def main():
    parser = argparse.ArgumentParser(
        description="MAVLink → CoT bridge for ATAK and TAK servers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  su 0 python3 tools/cot_bridge.py              # live serial, local UDP\n"
            "  su 0 python3 tools/cot_bridge.py --test        # synthetic data\n"
            "  su 0 python3 tools/cot_bridge.py --uid MyDrone # custom callsign\n"
            "  su 0 python3 tools/cot_bridge.py --tak-server tak.example:8087\n"
            "  su 0 python3 tools/cot_bridge.py --tak-server tak.example:8089 \\\n"
            "        --tak-tls --tak-cert cert.pem --tak-key cert.pem --tak-ca ca.pem\n"
        ),
    )
    parser.add_argument('--port', default='/dev/ttyS1',
                        help='Serial port path (default: /dev/ttyS1)')
    parser.add_argument('--baud', type=int, default=460800,
                        help='Serial baud rate (default: 460800)')
    parser.add_argument('--atak-host', default='127.0.0.1',
                        help='ATAK UDP host (default: 127.0.0.1)')
    parser.add_argument('--atak-port', type=int, default=4242,
                        help='ATAK UDP port (default: 4242)')
    parser.add_argument('--no-local-udp', action='store_true',
                        help='Skip the local UDP sink (TAK server only)')
    parser.add_argument('--tak-server', default=None, metavar='HOST:PORT',
                        help='TAK server upstream (TCP; add --tak-tls for TLS)')
    parser.add_argument('--tak-tls', action='store_true',
                        help='Wrap --tak-server with TLS (requires --tak-cert, --tak-key)')
    parser.add_argument('--tak-cert', default=None,
                        help='TLS client certificate PEM path')
    parser.add_argument('--tak-key', default=None,
                        help='TLS client private key PEM path')
    parser.add_argument('--tak-ca', default=None,
                        help='TLS CA bundle PEM path (default: system trust store)')
    parser.add_argument('--uid', default='ELRS-Drone-1',
                        help='CoT UID / callsign (default: ELRS-Drone-1)')
    parser.add_argument('--interval', type=float, default=2.0,
                        help='CoT send interval in seconds (default: 2.0)')
    parser.add_argument('--test', action='store_true',
                        help='Use synthetic test data instead of serial')
    args = parser.parse_args()

    sinks = []
    if not args.no_local_udp:
        sinks.append(UdpSink(args.atak_host, args.atak_port))

    if args.tak_server:
        try:
            host, port = _parse_host_port(args.tak_server, '--tak-server')
        except ValueError as e:
            parser.error(str(e))
        if args.tak_tls:
            if not args.tak_cert or not args.tak_key:
                parser.error("--tak-tls requires --tak-cert and --tak-key")
            sinks.append(TlsSink(host, port, args.tak_cert, args.tak_key, args.tak_ca))
        else:
            sinks.append(TcpSink(host, port))
    elif args.tak_tls or args.tak_cert or args.tak_key or args.tak_ca:
        parser.error("--tak-tls / --tak-cert / --tak-key / --tak-ca require --tak-server")

    if not sinks:
        parser.error("No sinks configured: drop --no-local-udp or pass --tak-server")

    bridge = CoTBridge(
        serial_port=args.port,
        baudrate=args.baud,
        sinks=sinks,
        uid=args.uid,
        send_interval=args.interval,
        test_mode=args.test,
    )
    bridge.run()


if __name__ == '__main__':
    main()
