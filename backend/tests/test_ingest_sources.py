"""Unit tests for the real-data ingest parsers (Lane A), offline (no network).

Exercises the pure parsing/normalization of OBIS, NWS, and NDBC payloads so CI
never depends on a live endpoint.
"""

from __future__ import annotations

from datetime import timezone

from app.ingest.ndbc import parse_latest
from app.ingest.nws import _KMH_TO_KN, NwsReading, _first_value, _parse_vt
from app.ingest.obis import WHALE_SEASON_MONTHS, filter_months, parse_records


# --- OBIS -----------------------------------------------------------------
def test_obis_filter_months_keeps_only_whale_season():
    """filter_months keeps only Jan-May records for the whale-season replay."""
    raw = [
        {"decimalLongitude": -70.3, "decimalLatitude": 42.1, "eventDate": "2024-03-10", "individualCount": "2"},
        {"decimalLongitude": -70.2, "decimalLatitude": 42.0, "eventDate": "2024-08-10", "individualCount": "1"},
        {"decimalLongitude": -70.1, "decimalLatitude": 42.2, "eventDate": "2024-01-05", "individualCount": "1"},
    ]
    rows = parse_records(raw)
    kept = filter_months(rows, WHALE_SEASON_MONTHS)
    assert {r.observed_at.month for r in kept} == {1, 3}
    assert len(kept) == 2
    # None means no filtering.
    assert len(filter_months(rows, None)) == 3


def test_obis_parse_records_normalizes_and_drops_bad():
    raw = [
        {"decimalLongitude": -70.3, "decimalLatitude": 42.1, "eventDate": "2022-04-04T17:01:46",
         "individualCount": "5", "institutionCode": "NOAA;NMFS;NEFSC"},
        {"decimalLongitude": -70.0, "decimalLatitude": 42.0, "eventDate": "2019-03-01",
         "individualCount": None, "institutionCode": "NEAQ"},
        {"decimalLongitude": None, "decimalLatitude": 42.0, "eventDate": "2019-03-01"},  # dropped
        {"decimalLongitude": -70.0, "decimalLatitude": 42.0, "eventDate": None},          # dropped
    ]
    rows = parse_records(raw)
    assert len(rows) == 2
    assert rows[0].count == 5 and rows[0].source.startswith("OBIS")
    assert rows[1].count == 1  # missing count defaults to 1
    assert all(r.observed_at.tzinfo is not None for r in rows)


def test_obis_parse_handles_date_range():
    rows = parse_records([
        {"decimalLongitude": -70.1, "decimalLatitude": 42.2,
         "eventDate": "2021-03-05T00:00:00Z/2021-03-05T23:59:59Z", "individualCount": "2"},
    ])
    assert len(rows) == 1
    assert rows[0].observed_at.year == 2021 and rows[0].observed_at.month == 3


# --- NWS ------------------------------------------------------------------
def test_nws_first_value_and_vt():
    block = {"values": [{"validTime": "2026-03-15T11:00:00+00:00/PT12H", "value": 1.2192}]}
    val, vt = _first_value(block)
    assert val == 1.2192
    assert _parse_vt(vt).tzinfo is timezone.utc


def test_nws_wind_conversion_constant():
    # 20 km/h should be ~10.8 kn.
    assert round(20 * _KMH_TO_KN, 1) == 10.8


def test_nws_reading_dataclass():
    r = NwsReading(-70.4, 42.3, _parse_vt(None), 1.2, 8.0, "https://api.weather.gov/x")
    assert r.wave_m == 1.2 and r.wind_kn == 8.0


# --- NDBC -----------------------------------------------------------------
NDBC_SAMPLE = """#YY  MM DD hh mm WDIR WSPD GST  WVHT   DPD   APD MWD   PRES  ATMP  WTMP  DEWP  VIS PTDY  TIDE
#yr  mo dy hr mn degT m/s  m/s     m   sec   sec degT   hPa  degC  degC  degC  nmi  hPa    ft
2026 10 24 16 30 290  2.0  3.0    MM    MM    MM  MM 1033.6   9.8  13.6   5.6   MM   MM    MM
2026 10 24 16 20 280  2.0  4.0   1.5    11   7.1  80 1033.7   9.9  13.6   5.6   MM   MM    MM
"""


def test_ndbc_parse_latest_skips_missing_wave_row():
    """The 16:30 row has MM wave; parser returns the 16:20 complete row."""
    obs = parse_latest(NDBC_SAMPLE, "44013")
    assert obs is not None
    assert obs.wave_m == 1.5
    assert obs.wind_kn == round(2.0 * 1.9438445, 1)
    assert obs.sst_c == 13.6
    assert obs.time.hour == 16 and obs.time.minute == 20


# --- background refresh throttle (task 6) --------------------------------
def test_background_refresh_is_noop_in_demo_mode(monkeypatch):
    import app.ingest.conditions as cond

    monkeypatch.setenv("FATHOM_DEMO_MODE", "true")
    assert cond.maybe_background_refresh() is False


def test_background_refresh_throttles(monkeypatch):
    """Not in demo mode: at most one refresh per interval; failures fall back."""
    import app.ingest.conditions as cond

    monkeypatch.setenv("FATHOM_DEMO_MODE", "false")
    monkeypatch.setattr(cond, "_last_refresh_ts", 0.0)

    calls = {"n": 0}

    def boom(_timeout):
        calls["n"] += 1
        raise RuntimeError("network down")

    monkeypatch.setattr(cond, "_fetch_live_conditions", boom)
    # Clock well past the interval so the first call is allowed to attempt,
    # the second (same instant) is throttled.
    clock = lambda: float(cond.REFRESH_INTERVAL_S + 100)  # noqa: E731
    assert cond.maybe_background_refresh(now_fn=clock) is False  # attempts, fails -> cache
    assert cond.maybe_background_refresh(now_fn=clock) is False  # throttled, no attempt
    assert calls["n"] == 1


# --- eMOLT bottom-temperature ingest (offline parsing) --------------------
def test_emolt_parse_erddap_table_normalizes():
    from app.ingest.emolt import parse_erddap_table

    table = {
        "columnNames": ["time", "latitude", "longitude", "depth", "temperature"],
        "columnUnits": ["UTC", "degrees_north", "degrees_east", "m", "degree_C"],
        "rows": [
            ["2026-10-24T18:52:10Z", 41.9389, -70.3049, 3.37, 13.887],
            ["2026-10-24T16:59:03Z", 43.4643, -70.19, 13.55, 11.915],
            ["bad", None, -70.0, 10.0, 9.0],  # dropped (bad time + lat)
        ],
    }
    rows = parse_erddap_table(table)
    assert len(rows) == 2
    assert rows[0].bottom_temp_c == 13.887 and rows[0].depth_m == 3.37
    assert all(r.observed_at.tzinfo is not None for r in rows)
    assert rows[0].source.startswith("eMOLT")


def test_emolt_most_recent_per_station():
    from datetime import datetime, timezone

    from app.ingest.emolt import EmoltReading, most_recent_per_station

    older = EmoltReading(-70.30, 41.94, datetime(2026, 10, 20, tzinfo=timezone.utc), 3.0, 12.0, "eMOLT")
    newer = EmoltReading(-70.302, 41.939, datetime(2026, 10, 24, tzinfo=timezone.utc), 3.0, 13.0, "eMOLT")
    other = EmoltReading(-69.50, 42.50, datetime(2026, 10, 22, tzinfo=timezone.utc), 5.0, 11.0, "eMOLT")
    kept = most_recent_per_station([older, newer, other], round_deg=2)
    # The two near-identical stations collapse to the newer one.
    assert len(kept) == 2
    assert newer in kept and older not in kept
