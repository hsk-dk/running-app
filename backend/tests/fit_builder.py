"""A very small FIT file writer, only for tests: enough messages to exercise the reader without a real file."""
import struct
from datetime import datetime, timezone

FIT_EPOCH = datetime(1989, 12, 31, tzinfo=timezone.utc)

UINT8, SINT32, UINT16, UINT32, ENUM = 0x02, 0x85, 0x84, 0x86, 0x00
SIZES = {UINT8: 1, SINT32: 4, UINT16: 2, UINT32: 4, ENUM: 1}
FMT = {UINT8: "<B", SINT32: "<i", UINT16: "<H", UINT32: "<I", ENUM: "<B"}


def crc16(data: bytes, crc: int = 0) -> int:
    table = [0x0000, 0xCC01, 0xD801, 0x1400, 0xF001, 0x3C00, 0x2800, 0xE401, 0xA001, 0x6C00, 0x7800, 0xB401, 0x5000, 0x9C01, 0x8801, 0x4400]
    for byte in data:
        tmp = table[crc & 0xF]
        crc = (crc >> 4) & 0x0FFF
        crc = crc ^ tmp ^ table[byte & 0xF]
        tmp = table[crc & 0xF]
        crc = (crc >> 4) & 0x0FFF
        crc = crc ^ tmp ^ table[(byte >> 4) & 0xF]
    return crc


def fit_time(dt: datetime) -> int:
    return int((dt.replace(tzinfo=timezone.utc) - FIT_EPOCH).total_seconds())


class Message:
    def __init__(self, local: int, global_num: int, fields):
        """fields: [(field_number, base_type)]"""
        self.local, self.global_num, self.fields = local, global_num, fields

    def definition(self) -> bytes:
        out = struct.pack("<BBBHB", 0x40 | self.local, 0, 0, self.global_num, len(self.fields))
        for number, base in self.fields:
            out += struct.pack("<BBB", number, SIZES[base], base)
        return out

    def data(self, values) -> bytes:
        out = struct.pack("<B", self.local)
        for (number, base), value in zip(self.fields, values):
            out += struct.pack(FMT[base], value)
        return out


RECORD = Message(1, 20, [(253, UINT32), (0, SINT32), (1, SINT32), (2, UINT16), (3, UINT8), (4, UINT8), (5, UINT32), (6, UINT16)])
LAP = Message(2, 19, [(253, UINT32), (2, UINT32), (7, UINT32), (9, UINT32), (15, UINT8), (13, UINT16), (23, ENUM)])
FILE_ID = Message(0, 0, [(0, ENUM), (1, UINT16), (4, UINT32)])
INVALID = {UINT8: 0xFF, SINT32: 0x7FFFFFFF, UINT16: 0xFFFF, UINT32: 0xFFFFFFFF}


def semicircles(degrees):
    return INVALID[SINT32] if degrees is None else round(degrees * 2**31 / 180.0)


def build_fit(records, laps=()):
    """records: dicts with t (datetime), lat, lng, altitude (m), hr, cadence (one leg), distance (m), speed (m/s).
    laps: dicts with start, elapsed (s), distance (m), avg_hr, avg_speed (m/s), intensity (int)."""
    body = FILE_ID.definition() + FILE_ID.data([4, 1, fit_time(records[0]["t"])])
    body += RECORD.definition()
    for r in records:
        alt = INVALID[UINT16] if r.get("altitude") is None else round((r["altitude"] + 500) * 5)
        body += RECORD.data([
            fit_time(r["t"]), semicircles(r.get("lat")), semicircles(r.get("lng")), alt,
            INVALID[UINT8] if r.get("hr") is None else r["hr"],
            INVALID[UINT8] if r.get("cadence") is None else r["cadence"],
            INVALID[UINT32] if r.get("distance") is None else round(r["distance"] * 100),
            INVALID[UINT16] if r.get("speed") is None else round(r["speed"] * 1000),
        ])
    if laps:
        body += LAP.definition()
        for lap in laps:
            body += LAP.data([
                fit_time(lap["start"]) + int(lap["elapsed"]), fit_time(lap["start"]), round(lap["elapsed"] * 1000),
                round(lap["distance"] * 100), lap["avg_hr"], round(lap["avg_speed"] * 1000), lap.get("intensity", 0),
            ])
    header = struct.pack("<BBHI4s", 14, 0x20, 2100, len(body), b".FIT")
    header += struct.pack("<H", crc16(header))
    return header + body + struct.pack("<H", crc16(header + body))
