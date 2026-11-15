"""Ground-control dashboard server (VERSION 2 REDESIGN: single-screen dashboard).

Run:   python3 server.py   (or, easier, python3 run_all.py)
Open:  http://localhost:5002   (or http://<this-computer-ip>:5002 from another device)

Each astronaut's Raspberry Pi sends a JSON message to  POST /update  about once a second.
The page (dashboard.html) reads  GET /api/state  once a second and redraws itself.
To change how the page LOOKS, edit dashboard.html (no need to restart the server).
"""
import json
import math
import os
import threading
import time
from collections import deque
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, request

app = Flask(__name__)
HERE = Path(__file__).resolve().parent

PORT = 5002            # Macs reserve 5000. The older "stable" program uses 5001, so v2 uses 5002 and both can exist side by side.
HISTORY_LEN = 600      # keep the last 600 readings per astronaut (10 minutes at 1 per second)
EVENT_LEN = 200        # keep the last 200 alert-log entries
STALE_SECONDS = 5      # no message for this long = NO SIGNAL
MAX_TILT_DEG = 60      # warn if pitch or roll is beyond this (possible fall)

# ---------------------------------------------------------------------------
# THRESHOLDS. "warn" = yellow, "crit" = red. Each is (lowest OK value, highest OK value).
#
# SUIT PRESSURE (hPa) is based on NASA figures (1 psi = 68.95 hPa). Sources (all NASA):
#   nominal EVA pressure 4.3 psi = 296 hPa
#     NASA EMU fact sheet: https://www.nasa.gov/wp-content/uploads/2015/07/2019_07_ea_emu.pdf
#   warn low 4.0 psi = 276 hPa (the EMU emergency oxygen pack starts flowing below 4.0 psi)
#     https://ntrs.nasa.gov/api/citations/19850008613/downloads/19850008613.pdf
#   crit low 3.6 psi = 248 hPa (secondary/emergency setpoint; Shuttle/ISS EMU uses 3.7 psi)
#     https://ntrs.nasa.gov/api/citations/20230007781/downloads/Regulators_ICES2023_Final.pdf
#   warn high 5.3 psi = 365 hPa (maximum nominal pressure, relief-valve setting), crit high
#   6.6 psi = 455 hPa (suit "structural" pressure = 1.5 x nominal)
#     https://ntrs.nasa.gov/api/citations/20160001778/downloads/20160001778.pdf
#     (Another NASA paper gives the relief valve crack pressure as 4.7 psid = 324 hPa:
#      https://ntrs.nasa.gov/api/citations/20150009506/downloads/20150009506.pdf)
#   The yellow and red lines are OUR reading of these design figures, not an official NASA alarm scheme.
#
# SUIT TEMPERATURE (inside-suit air, degrees C) is loosely based on NASA ranges:
#   comfort of suit air: 20-25 C (100% humidity) to 25-30 C (10% humidity)
#     https://ntrs.nasa.gov/api/citations/20150003483/downloads/20150003483.pdf
#   touch temperatures: 15-43 C is non-hazardous; pain/performance problems from 43 C (NASA-STD-3001)
#     https://www.nasa.gov/wp-content/uploads/2023/12/ochmo-tb-009-touch-temperature.pdf
#   xEMU internal low touch-temperature requirement 50 F = 10 C
#     https://ntrs.nasa.gov/api/citations/20240004548/downloads/Ch%20B%20TVAC%20Suit%202%20PGS%20%20Results-213%20final%202.pdf
#   NOTE: 43 C is a SKIN CONTACT limit, used here as a rough upper bound for suit air. NASA does not
#   publish a single "suit air temperature alarm".
#
# HEART RATE: NASA's spacesuit technical brief says performance impairment begins when pulse is
#   above 140 bpm: https://www.nasa.gov/wp-content/uploads/2025/09/ochmo-tb-050-spacesuits.pdf
#   The other heart-rate limits (50, 40, 120) are PLACEHOLDER demo values.
#
# BODY TEMPERATURE, BLOOD PRESSURE, BLOOD OXYGEN, IMPACT: PLACEHOLDER demo values. NOT medical advice.
# ---------------------------------------------------------------------------
LIMITS = {
    "temperature_c": {"label": "Temperature", "warn": (20, 30), "crit": (10, 43)},
    "pressure_hpa": {"label": "Suit pressure", "warn": (276, 365), "crit": (248, 455)},
    "heart_rate_bpm": {"label": "Heart rate", "warn": (50, 120), "crit": (40, 140)},
    # BODY TEMPERATURE and BLOOD PRESSURE are SIMULATED in this demo (no sensor yet) and these
    # limits are PLACEHOLDER demo values, not medical standards.
    "body_temp_c": {"label": "Body temperature", "warn": (35.5, 37.8), "crit": (35.0, 38.5)},
    "bp_systolic": {"label": "Systolic blood pressure", "warn": (90, 140), "crit": (80, 180)},
    "bp_diastolic": {"label": "Diastolic blood pressure", "warn": (60, 90), "crit": (50, 110)},
    "spo2_pct": {"label": "Blood oxygen", "warn": (95, 101), "crit": (90, 101)},   # placeholder; 101 = no upper limit
    # Impact / fall: PLACEHOLDER limits for the Pi's peak acceleration (1 g is just gravity).
    "peak_acceleration_g": {"label": "Impact (peak acceleration)", "warn": (0, 2.0), "crit": (0, 4.0)},
}

# Short names and units used for the small alert chips on each astronaut card.
SHORT = {"temperature_c": "Suit temp", "pressure_hpa": "Pressure", "heart_rate_bpm": "Heart rate",
         "body_temp_c": "Body temp", "bp_systolic": "Systolic", "bp_diastolic": "Diastolic",
         "spo2_pct": "Blood O\u2082", "peak_acceleration_g": "Impact"}
UNITS = {"temperature_c": "\u00b0C", "pressure_hpa": "hPa", "heart_rate_bpm": "bpm", "body_temp_c": "\u00b0C",
         "bp_systolic": "mmHg", "bp_diastolic": "mmHg", "spo2_pct": "%", "peak_acceleration_g": "g"}
HOLD_SECONDS = 4      # a warning/critical stays on screen this long after the reading returns to normal
                      # (stops a value sitting right on a limit from flickering between colors)

# The Sense HAT pressure sensor is specified to read down to about 260 hPa (check its
# datasheet). NASA's emergency setpoint (248 hPa) is BELOW that, so a reading at or under
# this floor is treated as critical: the true pressure may be lower than shown.
SENSOR_FLOOR_HPA = 262

NUMERIC_KEYS = ["temperature_c", "pressure_hpa", "heart_rate_bpm", "pitch", "roll", "yaw",
                "body_temp_c", "bp_systolic", "bp_diastolic", "spo2_pct",
                "humidity_pct", "peak_acceleration_g", "quality_score"]

# id -> {"data": {...}, "last_seen": time, "history": deque, "last_status": str or None}
astronauts = {}
# Alert log: newest entries are appended at the end
events = deque(maxlen=EVENT_LEN)


def signed_angle(deg):
    """Sense HAT gives 0-360. Convert to -180..180 so 350 means -10."""
    return deg - 360 if deg > 180 else deg


def evaluate(data):
    """Return (status, alert messages, abnormal items) for one astronaut's latest data.
    Each abnormal item is a dict the dashboard turns into a chip on the astronaut's card."""
    alerts = []
    items = {}

    def add(key, label, value, unit, level, direction, limit):
        old = items.get(key)
        if old is None or (level == "crit" and old["level"] == "warn"):
            items[key] = {"key": key, "short": label, "value": round(value, 2), "unit": unit,
                          "level": level, "dir": direction, "limit": limit}

    for key, rule in LIMITS.items():
        value = data.get(key)
        if value is None:
            continue
        lo_c, hi_c = rule["crit"]
        lo_w, hi_w = rule["warn"]
        if value < lo_c or value > hi_c:
            alerts.append(f"{rule['label']} critical: {value:g}")
            add(key, SHORT[key], value, UNITS[key], "crit", "low" if value < lo_c else "high", lo_c if value < lo_c else hi_c)
        elif value < lo_w or value > hi_w:
            alerts.append(f"{rule['label']} out of range: {value:g}")
            add(key, SHORT[key], value, UNITS[key], "warn", "low" if value < lo_w else "high", lo_w if value < lo_w else hi_w)

    pressure = data.get("pressure_hpa")
    if pressure is not None and pressure <= SENSOR_FLOOR_HPA:
        alerts.append("Pressure at sensor floor: true value may be lower")
        add("pressure_hpa", SHORT["pressure_hpa"], pressure, "hPa", "crit", "low", SENSOR_FLOOR_HPA)

    pitch, roll = data.get("pitch"), data.get("roll")
    if pitch is not None and roll is not None:
        worst = max(abs(signed_angle(pitch)), abs(signed_angle(roll)))
        if worst > MAX_TILT_DEG:
            alerts.append("Unusual body orientation")
            add("tilt", "Tilt", worst, "\u00b0", "warn", "high", MAX_TILT_DEG)

    status = "OK"
    if any(i["level"] == "crit" for i in items.values()):
        status = "CRITICAL"
    elif items:
        status = "WARNING"
    return status, alerts, list(items.values())


def clean(raw):
    """Keep only the fields we know, and make sure numbers really are numbers."""
    data = {"astronaut_id": str(raw["astronaut_id"])[:40]}
    for key in NUMERIC_KEYS:
        if key in raw:
            try:
                data[key] = float(raw[key])
            except (TypeError, ValueError):
                pass
    if isinstance(raw.get("tasks"), list):     # advisories sent by the Pi: keep a few, short, text only
        data["tasks"] = [{k: str(t.get(k, ""))[:200] for k in ("id", "priority", "category", "text", "source")}
                         for t in raw["tasks"][:8] if isinstance(t, dict)]
    if "vitals_simulated" in raw:          # True while body temp / blood pressure are made up
        data["vitals_simulated"] = bool(raw["vitals_simulated"])
    if "data_source" in raw:               # "pi" = the real Raspberry Pi, "sim" = made-up demo astronaut
        data["data_source"] = str(raw["data_source"])[:12]
    return data


def current_status(entry, now):
    """Status right now, including the case where the Pi has gone quiet.
    Returns (status, alert messages, abnormal items). Call this while holding log_lock."""
    if now - entry["last_seen"] > STALE_SECONDS:
        entry["active"] = {}
        return "NO SIGNAL", [f"No data for {int(now - entry['last_seen'])} s"], []
    _, alerts, items = evaluate(entry["data"])
    # Hold each warning/critical for a few seconds after it clears, so the display does not flicker.
    active = entry.setdefault("active", {})
    fresh = {i["key"]: i for i in items}
    for key, item in fresh.items():
        held = active.get(key)
        if held and held["item"]["level"] == "crit" and item["level"] == "warn" and now - held["seen"] <= HOLD_SECONDS:
            held["item"] = dict(held["item"], value=item["value"])      # keep the red, update the number
        else:
            active[key] = {"item": item, "seen": now}
    for key in list(active):
        if key not in fresh:
            if now - active[key]["seen"] > HOLD_SECONDS:
                del active[key]
            else:
                value = entry["data"].get(key)
                if value is not None:
                    active[key]["item"] = dict(active[key]["item"], value=round(value, 2))
    kept = [a["item"] for a in active.values()]
    if not kept:
        return "OK", [], []
    if not alerts:                                       # all current readings are fine, so show held ones only
        alerts = [f"{i['short']} {'critical' if i['level'] == 'crit' else 'out of range'}: {i['value']:g}" for i in kept]
    status = "CRITICAL" if any(i["level"] == "crit" for i in kept) else "WARNING"
    return status, alerts, kept


log_lock = threading.Lock()


def log_if_changed(astro_id, entry, now):
    """Compare status to the last one we saw. If it changed, add a line to the alert log."""
    with log_lock:
        status, alerts, items = current_status(entry, now)
        previous = entry["last_status"]
        if status != previous:
            detail = "; ".join(alerts)
            if status == "NO SIGNAL":
                message = "Signal lost"
            elif previous is None:
                message = "Connected" if status == "OK" else "Connected: " + detail
            elif previous == "NO SIGNAL":
                message = "Signal restored" if status == "OK" else "Signal restored: " + detail
            elif status == "OK":
                message = "Back to normal"
            else:
                message = detail
            events.append({"time": now, "id": astro_id, "status": status, "message": message})
            entry["last_status"] = status
        return status, alerts, items


def watch_signals():
    """Runs in the background so 'Signal lost' is logged even if nobody has the page open."""
    while True:
        now = time.time()
        for astro_id, entry in list(astronauts.items()):
            log_if_changed(astro_id, entry, now)
        time.sleep(1)



# ---------------------------------------------------------------------------
# TIME-TO-LIMIT estimates. Looks at the last few seconds of readings, fits a straight line,
# and says how long until the next limit IF the trend simply continued. It is a rough
# estimate, not a prediction of what will really happen.
# ---------------------------------------------------------------------------
FORECAST_WINDOW_S = 20      # use readings from the last 20 seconds
FORECAST_MIN_POINTS = 8     # need at least this many readings
FORECAST_MAX_ETA_S = 3600   # do not show estimates further away than one hour
# Smallest change per minute worth reporting (smaller changes are treated as steady/noise)
FORECAST_MIN_RATE = {"pressure_hpa": 1.0, "temperature_c": 0.3, "heart_rate_bpm": 4.0,
                     "body_temp_c": 0.1, "bp_systolic": 4.0}
FORECAST_UNITS = {"pressure_hpa": "hPa", "temperature_c": "\u00b0C", "heart_rate_bpm": "bpm",
                  "body_temp_c": "\u00b0C", "bp_systolic": "mmHg"}


def slope_of(points):
    """Slope (units per second) of the best straight line through (time, value) points."""
    n = len(points)
    mean_t = sum(t for t, _ in points) / n
    mean_v = sum(v for _, v in points) / n
    var_t = sum((t - mean_t) ** 2 for t, _ in points)
    if var_t == 0:
        return None
    return sum((t - mean_t) * (v - mean_v) for t, v in points) / var_t


def forecast_for(history, key, now):
    """Return a dict describing the trend toward the next limit, or None if steady/not enough data."""
    points = [(p["t"], p[key]) for p in history if p.get(key) is not None and now - p["t"] <= FORECAST_WINDOW_S]
    # only use the stretch since the last gap in the signal
    for i in range(len(points) - 1, 0, -1):
        if points[i][0] - points[i - 1][0] > 3:
            points = points[i:]
            break
    if len(points) < FORECAST_MIN_POINTS or points[-1][0] - points[0][0] < 6:
        return None
    n = len(points)
    long_points = [(p["t"], p[key]) for p in history if p.get(key) is not None and now - p["t"] <= 60]
    if len(long_points) >= 30 and long_points[-1][0] - long_points[0][0] >= 30:
        # The trend must also hold over the longer view. This ignores slow ups and downs that just
        # happen to point toward a limit for a few seconds.
        long_slope = slope_of(long_points)
        slope_now = slope_of(points)
        if long_slope is None or long_slope * slope_now <= 0 or abs(long_slope) < 0.3 * abs(slope_now):
            return None
    mean_t = sum(t for t, _ in points) / n
    mean_v = sum(v for _, v in points) / n
    var_t = sum((t - mean_t) ** 2 for t, _ in points)
    if var_t == 0:
        return None
    slope = sum((t - mean_t) * (v - mean_v) for t, v in points) / var_t        # units per second
    resid = math.sqrt(sum((v - (mean_v + slope * (t - mean_t))) ** 2 for t, v in points) / n)
    span = points[-1][0] - points[0][0]
    rate_min = slope * 60
    if abs(rate_min) < FORECAST_MIN_RATE[key] or abs(slope * span) < 3 * resid:
        return None                                                              # steady or just noise
    value = points[-1][1]
    rule = LIMITS[key]
    # A reading that is already past a warning limit and moving back toward normal is recovering,
    # not heading for the opposite limit, so no forecast for it.
    if (slope < 0 and points[0][1] > rule["warn"][1]) or (slope > 0 and points[0][1] < rule["warn"][0]):
        return None
    if slope < 0:
        candidates = [("warning", rule["warn"][0]), ("critical", rule["crit"][0])]
        ahead = [(name, lim) for name, lim in candidates if value > lim]
    else:
        candidates = [("warning", rule["warn"][1]), ("critical", rule["crit"][1])]
        ahead = [(name, lim) for name, lim in candidates if value < lim]
    if not ahead:
        return None                                                              # already past every limit
    name, lim = ahead[0]
    eta = (lim - value) / slope
    if eta <= 0 or eta > FORECAST_MAX_ETA_S:
        return None
    return {"key": key, "label": rule["label"], "unit": FORECAST_UNITS[key],
            "rate_per_min": round(rate_min, 1), "limit_name": name, "limit_value": lim,
            "eta_seconds": round(eta)}


def forecasts(entry, now):
    history = list(entry["history"])[-60:]
    out = []
    for key in FORECAST_MIN_RATE:
        item = forecast_for(history, key, now)
        if item:
            out.append(item)
    return out


@app.route("/update", methods=["POST"])
def update():
    raw = request.get_json(silent=True)
    if not isinstance(raw, dict) or "astronaut_id" not in raw:
        return jsonify({"error": "JSON body with astronaut_id is required"}), 400

    now = time.time()
    data = clean(raw)
    astro_id = data["astronaut_id"]
    entry = astronauts.get(astro_id)
    if entry is None:
        entry = {"history": deque(maxlen=HISTORY_LEN), "last_status": None}
        astronauts[astro_id] = entry
    entry["data"] = data
    entry["last_seen"] = now
    entry["history"].append({
        "t": now,
        "temperature_c": data.get("temperature_c"),
        "pressure_hpa": data.get("pressure_hpa"),
        "heart_rate_bpm": data.get("heart_rate_bpm"),
        "body_temp_c": data.get("body_temp_c"),
        "bp_systolic": data.get("bp_systolic"),
        "bp_diastolic": data.get("bp_diastolic"),
    })
    log_if_changed(astro_id, entry, now)
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# SPACE WEATHER panel.
# Reads the snapshot file written by astra_space_weather.py (same folder). If that file
# does not exist, the panel shows clearly labeled SIMULATED values instead.
# Set WEATHER_MODE = "simulated" to force simulated values (for example, no internet at the demo).
# Storm scales below are NOAA's published S (radiation) and G (geomagnetic) scales.
# Check them at swpc.noaa.gov before quoting them in your pitch.
# ---------------------------------------------------------------------------
WEATHER_MODE = "auto"            # "auto" or "simulated"
WEATHER_FILE = Path(os.getenv("ASTRA_WEATHER_FILE", str(HERE / "astra_space_weather.json")))
WEATHER_STALE_SECONDS = 300      # a snapshot older than this is labeled STALE
S_SCALE = [(100000, 5), (10000, 4), (1000, 3), (100, 2), (10, 1)]   # proton flux (pfu) at >=10 MeV

_weather_cache = {"mtime": None, "data": None}


def to_float(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def read_weather_file():
    """Load the snapshot, re-reading only when the file has changed (it can be several MB)."""
    try:
        mtime = WEATHER_FILE.stat().st_mtime
    except OSError:
        return None
    if _weather_cache["mtime"] != mtime:
        try:
            data = json.loads(WEATHER_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return _weather_cache["data"]
        _weather_cache["data"] = data if isinstance(data, dict) else None
        _weather_cache["mtime"] = mtime
    return _weather_cache["data"]


def parse_time(text):
    try:
        return datetime.fromisoformat(str(text)).timestamp()
    except ValueError:
        return None


def feed_data(snapshot, name):
    feed = (snapshot.get("feeds") or {}).get(name)
    data = feed.get("data") if isinstance(feed, dict) else None
    return data if isinstance(data, list) else None


def flare_rank(class_type):
    """'M1.2' becomes a sortable number (A < B < C < M < X)."""
    text = str(class_type or "").strip().upper()
    if not text or text[0] not in "ABCMX":
        return None
    return "ABCMX".index(text[0]) * 1000 + (to_float(text[1:]) or 0)


def parse_snapshot(snapshot):
    """Pull the few values we show out of the raw feeds. Anything missing stays None."""
    vals = {}

    records = [r for r in (feed_data(snapshot, "proton_flux") or []) if isinstance(r, dict)]
    ten_mev = [r for r in records if str(r.get("energy", "")).replace(" ", "").lower() == ">=10mev"]
    pool = ten_mev or records
    if pool:
        latest = max(pool, key=lambda r: str(r.get("time_tag", "")))
        vals["flux"] = to_float(latest.get("flux"))
        vals["flux_energy"] = latest.get("energy")

    for record in reversed(feed_data(snapshot, "solar_wind") or []):
        if isinstance(record, dict) and to_float(record.get("proton_speed")) is not None:
            vals["speed"] = to_float(record["proton_speed"])
            vals["density"] = to_float(record.get("proton_density"))
            break

    kp_feed = (snapshot.get("feeds") or {}).get("geomagnetic_kp")
    latest_kp = kp_feed.get("latest") if isinstance(kp_feed, dict) else None
    if not isinstance(latest_kp, dict):
        # Fall back to reading the raw rows ourselves (list of records, or a header row + rows).
        rows = feed_data(snapshot, "geomagnetic_kp") or []
        if rows and isinstance(rows[-1], dict):
            latest_kp = rows[-1]
        elif len(rows) > 1 and isinstance(rows[0], list):
            latest_kp = dict(zip(rows[0], rows[-1]))
    if isinstance(latest_kp, dict):
        low = {str(k).lower(): v for k, v in latest_kp.items()}
        vals["kp"] = to_float(low.get("kp", low.get("kp_index")))

    flares = feed_data(snapshot, "solar_flares")
    if flares is not None:
        flares = [r for r in flares if isinstance(r, dict)]
        vals["flare_count"] = len(flares)
        ranked = [r for r in flares if flare_rank(r.get("classType")) is not None]
        if ranked:
            vals["flare_best"] = max(ranked, key=lambda r: flare_rank(r["classType"]))["classType"]

    cmes = feed_data(snapshot, "cmes")
    if cmes is not None:
        vals["cme_count"] = len([r for r in cmes if isinstance(r, dict)])

    return vals


def simulated_values(now):
    """Made-up values that drift slowly, with a 'storm' every two minutes so the colors change."""
    storm = 0.6 < (now % 120) / 120 < 0.85
    return {
        "kp": round(2.3 + 0.7 * math.sin(now / 17) + (3.3 if storm else 0), 1),
        "flux": 0.2 * (1 + 0.3 * math.sin(now / 11)) + (30 if storm else 0),
        "flux_energy": ">=10 MeV",
        "speed": 410 + 30 * math.sin(now / 23) + (180 if storm else 0),
        "density": 5 + 1.5 * math.sin(now / 13),
        "flare_best": "M3.1" if storm else "C2.4",
        "flare_count": 9,
        "cme_count": 3,
    }


def build_items(vals, simulated=False):
    """Turn values into display tiles: label, value, unit, detail, color level, data source."""
    def source(name):
        return "SIMULATED" if simulated else name

    items = []

    kp = vals.get("kp")
    if kp is None:
        text, level, detail = "-", "none", "no data"
    else:
        g = min(5, int(kp) - 4) if kp >= 5 else 0
        level = "crit" if kp >= 7 else "warn" if kp >= 5 else "ok"
        text = f"{kp:.1f}"
        detail = f"Geomagnetic storm scale G{g}" if g else "Below storm level (G1 starts at Kp 5)"
    items.append({"label": "GEOMAGNETIC Kp", "value": text, "unit": "/ 9", "detail": detail,
                  "level": level, "source": source("NOAA SWPC")})

    flux = vals.get("flux")
    if flux is None:
        text, level, detail = "-", "none", "no data"
    else:
        s = next((n for limit, n in S_SCALE if flux >= limit), 0)
        level = "crit" if s >= 3 else "warn" if s >= 1 else "ok"
        text = f"{flux:.2f}" if flux < 10 else f"{flux:.0f}"
        energy = vals.get("flux_energy") or ">=10 MeV"
        detail = f"{energy} protons, radiation storm S{s}" if s else f"{energy} protons, below S1 (S1 starts at 10)"
    items.append({"label": "PROTON FLUX", "value": text, "unit": "pfu", "detail": detail,
                  "level": level, "source": source("NOAA SWPC")})

    speed = vals.get("speed")
    if speed is None:
        text, level, detail = "-", "none", "no data"
    else:
        level = "crit" if speed >= 800 else "warn" if speed >= 500 else "ok"
        text = f"{speed:.0f}"
        density = vals.get("density")
        detail = f"density {density:.1f} p/cm3" if density is not None else "solar wind speed"
    items.append({"label": "SOLAR WIND", "value": text, "unit": "km/s", "detail": detail,
                  "level": level, "source": source("NOAA SWPC")})

    count = vals.get("flare_count")
    best = vals.get("flare_best")
    if count is None:
        text, level, detail = "-", "none", "no data"
    else:
        text = best or "none"
        level = "crit" if str(best).upper().startswith("X") else "warn" if str(best).upper().startswith("M") else "ok"
        detail = f"{count} flares in the last 7 days"
    items.append({"label": "STRONGEST FLARE", "value": text, "unit": "7 days", "detail": detail,
                  "level": level, "source": source("NASA DONKI")})

    count = vals.get("cme_count")
    items.append({"label": "CORONAL MASS EJECTIONS", "value": "-" if count is None else str(count),
                  "unit": "7 days", "detail": "no data" if count is None else "events logged in the last 7 days",
                  "level": "none" if count is None else "ok", "source": source("NASA DONKI")})
    return items


def make_advisory(vals, simulated=False, stale=False):
    """A banner message when radiation (S) or geomagnetic (G) storm levels are reached.
    Informational only. The scale levels are NOAA's. This is not medical or operational advice."""
    flux, kp = vals.get("flux"), vals.get("kp")
    s_level = next((n for limit, n in S_SCALE if flux is not None and flux >= limit), 0)
    g_level = min(5, int(kp) - 4) if kp is not None and kp >= 5 else 0
    if not s_level and not g_level:
        return None
    parts = []
    if s_level:
        parts.append(f"Solar radiation storm S{s_level}")
    if g_level:
        parts.append(f"Geomagnetic storm G{g_level}")
    level = "crit" if (s_level >= 3 or g_level >= 4) else "warn"
    note = "Ground team: review crew radiation exposure and planned outside-vehicle activity."
    if simulated:
        note = "SIMULATED demo values. " + note
    elif stale:
        note = "Based on the last data received, which is out of date. " + note
    return {"level": level, "title": " and ".join(parts) + " (NOAA scale)", "text": note}


def space_weather_state(now):
    snapshot = None if WEATHER_MODE == "simulated" else read_weather_file()
    if snapshot is None:
        vals = simulated_values(now)
        return {"mode": "SIMULATED", "age_seconds": None, "feeds_ok": None, "feeds_total": None,
                "items": build_items(vals, simulated=True),
                "advisory": make_advisory(vals, simulated=True)}
    polled = parse_time(snapshot.get("polled_at_utc"))
    age = None if polled is None else max(0.0, now - polled)
    feeds = snapshot.get("feeds") if isinstance(snapshot.get("feeds"), dict) else {}
    vals = parse_snapshot(snapshot)
    fresh = age is not None and age <= WEATHER_STALE_SECONDS
    feeds_ok = sum(1 for f in feeds.values() if isinstance(f, dict) and f.get("status") == "ok")
    # LIVE only if the snapshot is recent AND every feed answered. Partly working = PARTIAL.
    # A recent snapshot where no feed answered (for example, no internet) is OFFLINE, not LIVE.
    if not fresh:
        mode = "STALE"
    elif feeds_ok == 0:
        mode = "OFFLINE"
    elif feeds_ok < len(feeds):
        mode = "PARTIAL"
    else:
        mode = "LIVE"
    live = fresh and feeds_ok > 0
    return {
        "mode": mode,
        "age_seconds": None if age is None else round(age),
        "feeds_ok": feeds_ok,
        "feeds_total": len(feeds),
        "items": build_items(vals),
        "advisory": make_advisory(vals, stale=not live),
    }


def safe_space_weather(now):
    """The weather panel must never break the astronaut cards, so catch any error here."""
    try:
        return space_weather_state(now)
    except Exception as exc:
        print("space weather error:", exc)
        return {"mode": "ERROR", "age_seconds": None, "feeds_ok": None, "feeds_total": None, "items": []}


def natural_key(text):
    """Sort 'Astronaut-2' before 'Astronaut-10' so card positions stay in a sensible, fixed order."""
    import re
    return [int(p) if p.isdigit() else p.lower() for p in re.split(r"(\d+)", text)]


@app.route("/api/state")
def api_state():
    now = time.time()
    result = []
    for astro_id, entry in sorted(list(astronauts.items()), key=lambda kv: natural_key(kv[0])):
        status, alerts, items = log_if_changed(astro_id, entry, now)
        result.append({
            "id": astro_id,
            "data": entry["data"],
            "status": status,
            "alerts": alerts,
            "abnormal": items,
            "age_seconds": round(now - entry["last_seen"], 1),
            "trend": [{k: (round(v, 2) if isinstance(v, float) else v) for k, v in p.items()}
                      for p in list(entry["history"])[-60:]],   # last 60 readings for the small graphs
            "forecasts": [] if status == "NO SIGNAL" else forecasts(entry, now),
        })
    return jsonify({
        "astronauts": result,
        "events": list(events)[-50:][::-1],           # newest first
        "limits": LIMITS,
        "space_weather": safe_space_weather(now),
        "server_time": now,
    })


@app.route("/api/history/<astro_id>")
def api_history(astro_id):
    entry = astronauts.get(astro_id)
    if entry is None:
        return jsonify({"error": "unknown astronaut"}), 404
    return jsonify(list(entry["history"]))


@app.route("/")
def index():
    # Read the file on every visit, so edits to dashboard.html show up after a browser refresh.
    return (HERE / "dashboard.html").read_text(encoding="utf-8")


@app.route("/favicon.ico")
def favicon():
    return "", 204


if __name__ == "__main__":
    threading.Thread(target=watch_signals, daemon=True).start()
    # host 0.0.0.0 lets other devices on the Wi-Fi (the Pis) reach this server.
    app.run(host="0.0.0.0", port=PORT)
