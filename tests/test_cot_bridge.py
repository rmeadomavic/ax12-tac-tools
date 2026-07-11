#!/usr/bin/env python3
"""Unit tests for the MAVLink parse -> CoT path in tools/cot_bridge.py.

Pure stdlib unittest. No hardware, no serial, no sockets. Every frame fed to
the parser is built here with cot_bridge's own CRC (mavlink_crc + CRC_EXTRA),
so a byte-for-byte round trip proves the parser, the CRC-16/MCRF4XX check, and
each message decoder agree. The CoT tests parse the emitted XML back with
ElementTree and assert the wire fields ATAK actually reads.

Run: python3 tests/test_cot_bridge.py
"""

import os
import struct
import sys
import unittest
import xml.etree.ElementTree as ET

sys.path.insert(
    0,
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"),
)

import cot_bridge  # noqa: E402  (sys.path insert must precede the import)


# ---------------------------------------------------------------------------
# Frame builders — use cot_bridge's OWN crc so the parser must accept them
# ---------------------------------------------------------------------------


def build_frame_v2(msg_id, payload, seq=0, sysid=1, compid=1):
    """Build a MAVLink v2 frame with a valid CRC via cot_bridge.mavlink_crc."""
    header = struct.pack("<BBBBBBB", 0xFD, len(payload), 0, 0, seq, sysid, compid)
    msgid = struct.pack("<I", msg_id)[:3]  # 24-bit little-endian message id
    body = header + msgid + payload
    crc = cot_bridge.mavlink_crc(body[1:], cot_bridge.CRC_EXTRA[msg_id])
    return body + struct.pack("<H", crc)


def build_frame_v1(msg_id, payload, seq=0, sysid=1, compid=1):
    """Build a MAVLink v1 frame with a valid CRC via cot_bridge.mavlink_crc."""
    header = struct.pack("<BBBBBB", 0xFE, len(payload), seq, sysid, compid, msg_id)
    body = header + payload
    crc = cot_bridge.mavlink_crc(body[1:], cot_bridge.CRC_EXTRA[msg_id])
    return body + struct.pack("<H", crc)


def gpi_payload(lat, lon, alt_m, rel_alt_m, vx_cms, vy_cms, vz_cms, hdg_cdeg):
    """GLOBAL_POSITION_INT (msg 33) payload, 28 bytes."""
    return struct.pack(
        "<IiiiihhhH",
        1234,  # time_boot_ms
        int(round(lat * 1e7)),
        int(round(lon * 1e7)),
        int(round(alt_m * 1000)),
        int(round(rel_alt_m * 1000)),
        vx_cms,
        vy_cms,
        vz_cms,
        hdg_cdeg,
    )


def heartbeat_payload(custom_mode, mav_type, base_mode):
    """HEARTBEAT (msg 0) payload, 9 bytes."""
    return struct.pack("<IBBBBB", custom_mode, mav_type, 3, base_mode, 4, 3)


def sys_status_payload(voltage_v, current_a, remaining_pct):
    """SYS_STATUS (msg 1) payload in true MAVLink wire order, 31 bytes.

    Fields are size-sorted on the wire: three u32 sensor masks, then all eight
    u16s (load, voltage, drop_rate_comm, errors_comm, errors_count1..4), then
    current_battery (i16), then battery_remaining (i8).
    """
    return struct.pack(
        "<IIIHHHHHHHHhb",
        0x0003FFFF,
        0x0003FFFF,
        0x0003FFFF,  # sensors present / enabled / health
        50,  # load, 5.0%
        int(round(voltage_v * 1000)),  # voltage_battery mV
        0,  # drop_rate_comm
        0,  # errors_comm
        0,
        0,
        0,
        0,  # errors_count1..4
        int(round(current_a * 100)),  # current_battery cA
        remaining_pct,  # battery_remaining %
    )


# ---------------------------------------------------------------------------
# Parser + decoder tests
# ---------------------------------------------------------------------------


class ParserTests(unittest.TestCase):
    def _parse_one(self, frame):
        parser = cot_bridge.MAVLinkParser()
        frames = list(parser.feed(frame))
        self.assertEqual(len(frames), 1, "expected exactly one parsed frame")
        return frames[0]

    def test_global_position_int_v2(self):
        payload = gpi_payload(
            lat=35.1234567,
            lon=-79.0064000,
            alt_m=100.0,
            rel_alt_m=50.0,
            vx_cms=500,
            vy_cms=0,
            vz_cms=-25,
            hdg_cdeg=9000,
        )
        frame = self._parse_one(
            build_frame_v2(cot_bridge.MSG_GLOBAL_POSITION_INT, payload)
        )
        self.assertEqual(frame.version, 2)
        self.assertEqual(frame.msg_id, cot_bridge.MSG_GLOBAL_POSITION_INT)

        pos = cot_bridge.decode_global_position_int(frame.payload)
        self.assertAlmostEqual(pos["lat"], 35.1234567, places=6)
        self.assertAlmostEqual(pos["lon"], -79.0064000, places=6)
        self.assertAlmostEqual(pos["alt_msl"], 100.0, places=3)
        self.assertAlmostEqual(pos["alt_agl"], 50.0, places=3)
        self.assertAlmostEqual(pos["groundspeed"], 5.0, places=3)  # 500 cm/s
        self.assertAlmostEqual(pos["heading"], 90.0, places=3)

    def test_global_position_int_v1(self):
        payload = gpi_payload(
            lat=1.0,
            lon=2.0,
            alt_m=10.0,
            rel_alt_m=10.0,
            vx_cms=0,
            vy_cms=300,
            vz_cms=0,
            hdg_cdeg=18000,
        )
        frame = self._parse_one(
            build_frame_v1(cot_bridge.MSG_GLOBAL_POSITION_INT, payload)
        )
        self.assertEqual(frame.version, 1)
        pos = cot_bridge.decode_global_position_int(frame.payload)
        self.assertAlmostEqual(pos["lon"], 2.0, places=6)
        self.assertAlmostEqual(pos["groundspeed"], 3.0, places=3)  # 300 cm/s
        self.assertAlmostEqual(pos["heading"], 180.0, places=3)

    def test_heartbeat_armed(self):
        payload = heartbeat_payload(
            custom_mode=5,  # LOITER in the copter table
            mav_type=cot_bridge.MAV_TYPE_QUADROTOR,
            base_mode=0x80 | 0x10,  # MAV_MODE_FLAG_SAFETY_ARMED set
        )
        frame = self._parse_one(build_frame_v2(cot_bridge.MSG_HEARTBEAT, payload))
        hb = cot_bridge.decode_heartbeat(frame.payload)
        self.assertEqual(hb["mav_type"], cot_bridge.MAV_TYPE_QUADROTOR)
        self.assertTrue(hb["armed"])
        self.assertEqual(hb["flight_mode"], "LOITER")
        self.assertEqual(hb["system_status"], 4)

    def test_heartbeat_disarmed(self):
        payload = heartbeat_payload(
            custom_mode=0,
            mav_type=cot_bridge.MAV_TYPE_FIXED_WING,
            base_mode=0x00,
        )
        frame = self._parse_one(build_frame_v2(cot_bridge.MSG_HEARTBEAT, payload))
        hb = cot_bridge.decode_heartbeat(frame.payload)
        self.assertFalse(hb["armed"])
        self.assertEqual(hb["mav_type"], cot_bridge.MAV_TYPE_FIXED_WING)

    def test_sys_status(self):
        payload = sys_status_payload(voltage_v=12.6, current_a=5.0, remaining_pct=75)
        frame = self._parse_one(build_frame_v2(cot_bridge.MSG_SYS_STATUS, payload))
        self.assertEqual(frame.msg_id, cot_bridge.MSG_SYS_STATUS)
        ss = cot_bridge.decode_sys_status(frame.payload)
        self.assertAlmostEqual(ss["voltage"], 12.6, places=2)
        self.assertAlmostEqual(ss["current"], 5.0, places=2)
        self.assertEqual(ss["battery_remaining"], 75)

    def test_bad_crc_is_rejected(self):
        payload = heartbeat_payload(0, cot_bridge.MAV_TYPE_QUADROTOR, 0x80)
        frame = bytearray(build_frame_v2(cot_bridge.MSG_HEARTBEAT, payload))
        frame[-1] ^= 0xFF  # corrupt the CRC high byte
        parser = cot_bridge.MAVLinkParser()
        self.assertEqual(
            list(parser.feed(bytes(frame))),
            [],
            "a frame with a bad CRC must not parse",
        )

    def test_resync_after_leading_garbage(self):
        payload = gpi_payload(35.0, -79.0, 100.0, 50.0, 0, 0, 0, 0)
        good = build_frame_v2(cot_bridge.MSG_GLOBAL_POSITION_INT, payload)
        stream = b"\x00\x11\x22 garbage bytes " + good
        frames = list(cot_bridge.MAVLinkParser().feed(stream))
        self.assertEqual(len(frames), 1)
        self.assertEqual(frames[0].msg_id, cot_bridge.MSG_GLOBAL_POSITION_INT)


# ---------------------------------------------------------------------------
# CoT XML tests
# ---------------------------------------------------------------------------


class CoTTests(unittest.TestCase):
    def test_format_cot_xml_wellformed(self):
        xml = cot_bridge.format_cot_xml(
            lat=35.1234567,
            lon=-79.0064000,
            alt=123.4,
            heading=270.0,
            speed=12.5,
            flight_mode="AUTO",
            armed=True,
            uid="TEST-UAV-9",
            cot_type="a-f-A-M-F-Q",
        )
        root = ET.fromstring(xml)  # raises on malformed XML
        self.assertEqual(root.tag, "event")
        self.assertEqual(root.get("uid"), "TEST-UAV-9")
        self.assertEqual(root.get("type"), "a-f-A-M-F-Q")

        point = root.find("point")
        self.assertIsNotNone(point)
        self.assertAlmostEqual(float(point.get("lat")), 35.1234567, places=6)
        self.assertAlmostEqual(float(point.get("lon")), -79.0064000, places=6)
        self.assertAlmostEqual(float(point.get("hae")), 123.4, places=1)

    def test_cot_type_mapping(self):
        self.assertEqual(
            cot_bridge.cot_type_for(cot_bridge.MAV_TYPE_FIXED_WING), "a-f-A-M-F-Q"
        )
        self.assertEqual(
            cot_bridge.cot_type_for(cot_bridge.MAV_TYPE_QUADROTOR), "a-f-A-M-H-Q"
        )

    def test_battery_appended_to_remarks(self):
        xml = cot_bridge.format_cot_xml(
            lat=0.0,
            lon=0.0,
            alt=0.0,
            heading=0.0,
            speed=0.0,
            flight_mode="LOITER",
            armed=False,
            battery=12.6,
        )
        remarks = ET.fromstring(xml).find("detail/remarks").text
        self.assertIn("12.6V", remarks)

    def test_parse_to_cot_end_to_end(self):
        """Raw GLOBAL_POSITION_INT bytes -> parse -> decode -> CoT XML point."""
        payload = gpi_payload(35.5, -79.5, 200.0, 150.0, 400, 300, 0, 4500)
        frame = list(
            cot_bridge.MAVLinkParser().feed(
                build_frame_v2(cot_bridge.MSG_GLOBAL_POSITION_INT, payload)
            )
        )[0]
        pos = cot_bridge.decode_global_position_int(frame.payload)
        self.assertAlmostEqual(pos["groundspeed"], 5.0, places=3)  # 3-4-5 triangle

        xml = cot_bridge.format_cot_xml(
            lat=pos["lat"],
            lon=pos["lon"],
            alt=pos["alt_msl"],
            heading=pos["heading"],
            speed=pos["groundspeed"],
            flight_mode="GUIDED",
            armed=True,
            uid="ELRS-Drone-1",
        )
        point = ET.fromstring(xml).find("point")
        self.assertAlmostEqual(float(point.get("lat")), 35.5, places=6)
        self.assertAlmostEqual(float(point.get("lon")), -79.5, places=6)


if __name__ == "__main__":
    unittest.main(verbosity=2)
