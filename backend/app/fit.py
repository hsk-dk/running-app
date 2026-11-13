"""Reading a Garmin activity file (a ZIP with one .FIT file in it) into the plain dicts `domain.fitdata` works on."""
from __future__ import annotations

import io
import zipfile
from datetime import datetime, timezone

import fitdecode

SEMICIRCLE_TO_DEGREES = 180.0 / 2**31
MAX_FILE_BYTES = 30 * 1024 * 1024  # a long run is well under 1 MB; this only stops a bad file from filling memory


class FitError(ValueError):
    """The file could not be read as a FIT activity."""


def _utc(value):
    if isinstance(value, datetime):
        return value if value.tzinfo is None else value.astimezone(timezone.utc).replace(tzinfo=None)
    return None


def _num(value):
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def _degrees(semicircles):
    return None if semicircles is None else semicircles * SEMICIRCLE_TO_DEGREES


def fit_bytes_from_zip(content: bytes) -> bytes:
    """The .FIT file inside the ZIP Garmin sends. A bare FIT file is accepted too."""
    if content[8:12] == b".FIT":
        return content
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            names = [n for n in archive.namelist() if n.lower().endswith(".fit")]
            if not names:
                raise FitError("Der er ingen FIT-fil i Garmins download")
            info = archive.getinfo(names[0])
            if info.file_size > MAX_FILE_BYTES:
                raise FitError("FIT-filen er uventet stor")
            return archive.read(names[0])
    except zipfile.BadZipFile as exc:
        raise FitError("Garmins download er ikke en gyldig ZIP-fil") from exc


def parse(content: bytes) -> tuple[list[dict], list[dict]]:
    """(records, laps) from a FIT file or a ZIP that holds one."""
    data = fit_bytes_from_zip(content)
    records: list[dict] = []
    laps: list[dict] = []
    try:
        with fitdecode.FitReader(io.BytesIO(data), check_crc=fitdecode.CrcCheck.WARN) as reader:
            for frame in reader:
                if not isinstance(frame, fitdecode.FitDataMessage):
                    continue
                if frame.name == "record":
                    speed = frame.get_value("enhanced_speed", fallback=None)
                    if speed is None:
                        speed = frame.get_value("speed", fallback=None)
                    altitude = frame.get_value("enhanced_altitude", fallback=None)
                    if altitude is None:
                        altitude = frame.get_value("altitude", fallback=None)
                    cadence = _num(frame.get_value("cadence", fallback=None))
                    fraction = _num(frame.get_value("fractional_cadence", fallback=None)) or 0.0
                    records.append(
                        {
                            "t": _utc(frame.get_value("timestamp", fallback=None)),
                            "lat": _degrees(_num(frame.get_value("position_lat", fallback=None))),
                            "lng": _degrees(_num(frame.get_value("position_long", fallback=None))),
                            "distance": _num(frame.get_value("distance", fallback=None)),
                            "speed": _num(speed),
                            "hr": _num(frame.get_value("heart_rate", fallback=None)),
                            # Garmin counts one leg: steps per minute is twice that.
                            "cadence": None if cadence is None else (cadence + fraction) * 2,
                            "altitude": _num(altitude),
                        }
                    )
                elif frame.name == "lap":
                    avg_speed = frame.get_value("enhanced_avg_speed", fallback=None)
                    if avg_speed is None:
                        avg_speed = frame.get_value("avg_speed", fallback=None)
                    intensity = frame.get_value("intensity", fallback=None)
                    laps.append(
                        {
                            "start": _utc(frame.get_value("start_time", fallback=None)),
                            "elapsed": _num(frame.get_value("total_elapsed_time", fallback=None)),
                            "distance": _num(frame.get_value("total_distance", fallback=None)),
                            "avg_hr": _num(frame.get_value("avg_heart_rate", fallback=None)),
                            "avg_speed": _num(avg_speed),
                            "intensity": None if intensity is None else str(intensity),
                        }
                    )
    except FitError:
        raise
    except Exception as exc:  # fitdecode raises its own error types for damaged files
        raise FitError(f"FIT-filen kunne ikke læses: {exc}") from exc
    if not records:
        raise FitError("FIT-filen har ingen målinger")
    return records, laps
