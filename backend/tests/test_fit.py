"""Reading a FIT file and boiling it down: route, profile, kilometre splits and laps."""
import io
import zipfile
from datetime import datetime, timedelta

import pytest

from app import fit
from app.domain import fitdata
from tests.fit_builder import build_fit

START = datetime(2026, 11, 12, 16, 5, 13)  # UTC


def treadmill(seconds=1500, speed=2.8, hr=(120, 150)):
    """A run on a belt: distance and speed but no GPS."""
    out = []
    dist = 0.0
    for s in range(seconds + 1):
        out.append({"t": START + timedelta(seconds=s), "lat": None, "lng": None, "altitude": None,
                    "hr": round(hr[0] + (hr[1] - hr[0]) * s / seconds), "cadence": 80, "distance": dist, "speed": speed})
        dist += speed
    return out


def outdoor(seconds=600):
    out = []
    dist = 0.0
    for s in range(seconds + 1):
        out.append({"t": START + timedelta(seconds=s), "lat": 55.676 + s * 1e-5, "lng": 12.568 + s * 5e-6,
                    "altitude": 10 + s * 0.01, "hr": 140, "cadence": 82, "distance": dist, "speed": 3.0})
        dist += 3.0
    return out


def as_zip(content: bytes) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("25056407215_ACTIVITY.fit", content)
    return buf.getvalue()


# ---- the reader (real binary files) ----------------------------------------------------------------

def test_reads_records_from_a_zip_with_scaled_units_and_doubled_cadence():
    records, laps = fit.parse(as_zip(build_fit(treadmill(60))))
    assert len(records) == 61 and laps == []
    r = records[30]
    assert r["t"] == START + timedelta(seconds=30)
    assert r["distance"] == pytest.approx(84.0) and r["speed"] == pytest.approx(2.8)
    assert r["hr"] == 135 and r["cadence"] == 160  # one leg x 2 = steps per minute
    assert r["lat"] is None and r["lng"] is None and r["altitude"] is None


def test_reads_gps_as_degrees_and_altitude_in_metres():
    records, _ = fit.parse(build_fit(outdoor(10)))  # a bare FIT file works too
    assert records[5]["lat"] == pytest.approx(55.676 + 5e-5, abs=1e-6)
    assert records[5]["lng"] == pytest.approx(12.568 + 2.5e-5, abs=1e-6)
    assert records[5]["altitude"] == pytest.approx(10.05, abs=0.2)


def test_reads_laps():
    laps_in = [
        {"start": START, "elapsed": 300, "distance": 800.0, "avg_hr": 125, "avg_speed": 2.6, "intensity": 2},
        {"start": START + timedelta(seconds=300), "elapsed": 90, "distance": 400.0, "avg_hr": 150, "avg_speed": 4.4, "intensity": 0},
    ]
    _, laps = fit.parse(build_fit(treadmill(400), laps_in))
    assert [(round(l["elapsed"]), round(l["distance"]), round(l["avg_hr"])) for l in laps] == [(300, 800, 125), (90, 400, 150)]
    assert laps[1]["avg_speed"] == pytest.approx(4.4) and laps[0]["start"] == START


@pytest.mark.parametrize("junk", [b"", b"not a zip", b"PK\x03\x04broken", as_zip(b"x")[:20]])
def test_a_damaged_file_gives_a_clear_error_not_a_crash(junk):
    with pytest.raises(fit.FitError):
        fit.parse(junk)


def test_a_zip_without_a_fit_file_and_a_fit_file_without_records_are_errors():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("readme.txt", "hi")
    with pytest.raises(fit.FitError, match="ingen FIT"):
        fit.parse(buf.getvalue())
    with pytest.raises(fit.FitError):
        fit.parse(as_zip(build_fit(treadmill(1))[:30]))


# ---- the analysis --------------------------------------------------------------------------------------

def test_a_treadmill_run_has_no_route_but_a_profile_and_splits():
    records, laps = fit.parse(as_zip(build_fit(treadmill(1500))))  # 2.8 m/s for 25 min = 4.2 km
    a = fitdata.analyze(records, laps)
    assert a["route"] is None
    assert a["profile"]["hr"][0] == 120 and a["profile"]["hr"][-1] == 150
    assert len(a["profile"]["t"]) <= fitdata.MAX_PROFILE_SAMPLES and a["profile"]["alt"] is None
    km = a["splits"]
    assert [s["km"] for s in km] == [1, 2, 3, 4, 5]
    assert km[0]["pace_s_per_km"] == pytest.approx(1000 / 2.8, abs=1.5)
    assert km[-1]["partial"] is True and km[-1]["distance_m"] == pytest.approx(200, abs=5)
    assert km[0]["avg_hr"] < km[3]["avg_hr"]  # heart rate climbs through the run


def test_an_outdoor_run_has_a_route_that_decodes_and_an_elevation_per_kilometre():
    records, _ = fit.parse(build_fit(outdoor(600)))  # 1800 m
    a = fitdata.analyze(records, [])
    assert a["route"]
    # the polyline decodes back to the track (check start and end)
    pts = decode(a["route"])
    assert pts[0] == pytest.approx((55.676, 12.568), abs=1e-4) and pts[-1] == pytest.approx((55.682, 12.571), abs=1e-4)
    assert a["splits"][0]["elevation_m"] == pytest.approx(3.33, abs=0.6)
    assert len(a["profile"]["alt"]) == len(a["profile"]["t"])


def decode(s):
    pts, i, lat, lng = [], 0, 0, 0
    while i < len(s):
        for axis in (0, 1):
            shift = res = 0
            while True:
                b = ord(s[i]) - 63
                i += 1
                res |= (b & 0x1F) << shift
                shift += 5
                if b < 0x20:
                    break
            d = ~(res >> 1) if res & 1 else res >> 1
            if axis == 0:
                lat += d
            else:
                lng += d
        pts.append((lat / 1e5, lng / 1e5))
    return pts


def test_the_polyline_encoder_matches_googles_own_example():
    assert fitdata.encode_polyline([(38.5, -120.2), (40.7, -120.95), (43.252, -126.453)]) == "_p~iF~ps|U_ulLnnqC_mqNvxq`@"


def test_a_long_route_is_thinned_but_keeps_both_ends():
    pts = [(55 + i * 1e-5, 12 + i * 1e-5) for i in range(5000)]
    rows = [{"t": START + timedelta(seconds=i), "lat": p[0], "lng": p[1]} for i, p in enumerate(pts)]
    decoded = decode(fitdata.route_polyline(rows))
    assert len(decoded) == fitdata.MAX_ROUTE_POINTS
    assert decoded[0] == pytest.approx(pts[0], abs=1e-5) and decoded[-1] == pytest.approx(pts[-1], abs=1e-5)


def test_laps_become_the_steps_of_an_interval_workout():
    laps_in = [
        {"start": START, "elapsed": 300, "distance": 800.0, "avg_hr": 125, "avg_speed": 2.667, "intensity": 2},
        {"start": START + timedelta(seconds=300), "elapsed": 90, "distance": 400.0, "avg_hr": 150, "avg_speed": 4.444, "intensity": 0},
    ]
    records, laps = fit.parse(build_fit(treadmill(400), laps_in))
    out = fitdata.laps(laps, records)
    assert [l["start_s"] for l in out] == [0, 300] and out[1]["duration_s"] == 90
    assert out[1]["pace_s_per_km"] == pytest.approx(225, abs=1) and out[0]["avg_hr"] == 125


def test_a_pause_is_not_counted_as_running_time():
    rows = treadmill(120)
    paused = rows[:60] + [dict(r, t=r["t"] + timedelta(seconds=300), distance=rows[59]["distance"]) for r in rows[60:]]
    for r in paused[60:]:
        r["distance"] = rows[59]["distance"] + (r["distance"] - rows[60]["distance"])
    a = fitdata.profile(paused)
    assert a["t"][-1] == pytest.approx(120, abs=2)  # 300 s standing still is left out


def test_distance_falls_back_to_speed_then_to_gps_and_never_goes_backwards():
    no_dist = [{"t": START + timedelta(seconds=s), "speed": 3.0} for s in range(0, 401)]
    assert fitdata.km_splits(no_dist)[0]["pace_s_per_km"] == pytest.approx(333, abs=2)
    gps = [{"t": START + timedelta(seconds=s), "lat": 55 + s * 2.7e-5, "lng": 12.0} for s in range(0, 401)]  # about 3 m/s
    assert 300 < fitdata.km_splits(gps)[0]["pace_s_per_km"] < 360
    wobble = [{"t": START + timedelta(seconds=s), "distance": d} for s, d in enumerate([0, 10, 8, 20, 30])]
    assert fitdata.profile(wobble)["d"] == [0.0, 10.0, 10.0, 20.0, 30.0]


@pytest.mark.parametrize("records", [[], [{"t": START}], [{"t": "x"}], [{"t": START, "distance": 0}, {"t": START + timedelta(seconds=5), "distance": 0}]])
def test_too_little_data_gives_nothing_rather_than_nonsense(records):
    a = fitdata.analyze(records, [])
    assert a == {"route": None, "profile": None, "splits": [], "laps": []}
