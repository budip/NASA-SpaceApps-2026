"""Runs on YOUR MAC (next to server.py). Pulls data from the Raspberry Pi's web server
and forwards it to the dashboard as one astronaut.

    Pi web server  --(GET every second)-->  this script  --(POST)-->  server.py  -->  dashboard

Step 1, look at what the Pi sends (does not touch the dashboard):
    python3 pi_poller.py --probe
Step 2, run for real (server.py must already be running):
    python3 pi_poller.py

If a value is wrong or missing, change the settings just below. The script guesses which
field in the Pi's reply is temperature, pressure, pitch, roll and yaw by looking at the names.
"""
import json
import math
import sys
import time
import urllib.request

# ------------------------------ SETTINGS ------------------------------
PI_URL = "http://10.0.201.67:8000/api/v1/status"   # the Pi's web server (from your teammate)
DASHBOARD_URL = "http://localhost:5002/update"       # server.py on this Mac
ASTRONAUT_ID = "Astronaut-5"                         # name shown on the dashboard card
INTERVAL_SECONDS = 1.0

PRESSURE_UNIT = "auto"   # "auto", "hPa", "kPa", "Pa", "psi"   (dashboard needs hPa)
TEMP_UNIT = "auto"       # "auto", "C", "F"
TEMP_OFFSET = 0.0        # Sense HAT reads high from Pi heat. Use a negative number to correct.
# Orientation zero point. If the Pi shows a big tilt while it is sitting where you want "upright",
# hold it in that position, read the pitch/roll/yaw from --probe, and enter the NEGATIVE of them here.
PITCH_OFFSET = 0.0
ROLL_OFFSET = 0.0
YAW_OFFSET = 0.0
SIMULATE_VITALS = True   # The Pi has no body-temperature or blood-pressure sensor yet, so we make
                         # up believable values and the dashboard labels them SIMULATED.
                         # Set to False to send nothing for these. If the Pi ever sends real ones,
                         # they are used automatically.

# Only if the guess picks the wrong field: write the exact name from --probe, like "env.temp_c"
FORCE_FIELDS = {
    # "temperature": "env.temp_c",
    # "pressure": "env.pressure",
    # "pitch": "imu.pitch", "roll": "imu.roll", "yaw": "imu.yaw",
    # "heart_rate": "vitals.hr",
}
# ----------------------------------------------------------------------

# Words that identify each value (checked against the lowercase field name).
HINTS = {
    "temperature": (["temp"], ["cpu", "core", "gpu", "humid", "body", "skin"]),   # (must contain, must NOT contain)
    "body_temp": (["body_temp", "bodytemp", "body.temp", "core_temp", "skin_temp"], []),
    "bp_systolic": (["systolic", "bp_sys"], []),
    "bp_diastolic": (["diastolic", "bp_dia"], []),
    "spo2": (["oxygen", "spo2"], []),
    "humidity": (["humid"], []),
    "peak_accel": (["peak_acceleration"], []),
    "pressure": (["press"], ["target", "setpoint", "blood", "bp_"]),
    "pitch": (["pitch"], []),
    "roll": (["roll"], []),
    "yaw": (["yaw", "heading"], []),
    "heart_rate": (["heart", "bpm", "pulse"], []),
}


def flatten(obj, prefix=""):
    """Turns nested JSON into {"a.b.c": value} so we can search it by name."""
    out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.update(flatten(v, f"{prefix}.{k}" if prefix else str(k)))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out.update(flatten(v, f"{prefix}.{i}" if prefix else str(i)))
    else:
        out[prefix] = obj
    return out


def as_number(v):
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        try:
            return float(v.strip().split()[0])
        except (ValueError, IndexError):
            return None
    return None


def find(flat, what):
    """Returns (field_name, number) for the best match, or (None, None)."""
    forced = FORCE_FIELDS.get(what)
    if forced:
        n = as_number(flat.get(forced))
        return (forced, n) if n is not None else (None, None)
    must, never = HINTS[what]
    for name, value in flat.items():
        low = name.lower()
        if any(w in low for w in must) and not any(w in low for w in never):
            n = as_number(value)
            if n is not None:
                return name, n
    return None, None


def pressure_to_hpa(name, value):
    unit = PRESSURE_UNIT
    low = (name or "").lower()
    if unit == "auto":
        if "kpa" in low:
            unit = "kPa"
        elif "hpa" in low or "mbar" in low:
            unit = "hPa"
        elif "psi" in low:
            unit = "psi"
        elif low.endswith("_pa") or low.endswith(".pa"):
            unit = "Pa"
        elif value > 150:
            unit = "hPa"      # suit range is about 250-1100 in hPa
        elif value > 20:
            unit = "kPa"      # 20-150 looks like kPa
        else:
            unit = "psi"      # under 20 looks like psi
    factor = {"hPa": 1.0, "kPa": 10.0, "Pa": 0.01, "psi": 68.9476}[unit]
    return value * factor, unit


def temp_to_c(name, value, flat=None):
    unit = TEMP_UNIT
    low = (name or "").lower()
    if unit == "auto":
        unit = "F" if (low.endswith("_f") or "fahrenheit" in low) else "C"
        for k, v in (flat or {}).items():      # e.g. a separate "temperature_unit": "F" field
            if "temp" in k.lower() and "unit" in k.lower() and str(v).strip().upper().startswith(("F", "\u00b0F")):
                unit = "F"
    return ((value - 32) * 5 / 9 if unit == "F" else value), unit


def fetch_pi():
    req = urllib.request.Request(PI_URL, headers={"accept": "*/*"})
    with urllib.request.urlopen(req, timeout=3) as r:
        return r.read().decode("utf-8", "replace")


def build_payload(text):
    """Returns (payload, notes). payload has only the fields we could find."""
    data = json.loads(text)
    flat = flatten(data)
    payload = {"astronaut_id": ASTRONAUT_ID, "data_source": "pi"}   # "pi" marks the one real astronaut
    notes = []

    name, v = find(flat, "temperature")
    if v is not None:
        c, unit = temp_to_c(name, v, flat)
        payload["temperature_c"] = round(c + TEMP_OFFSET, 1)
        notes.append(f"temperature <- {name} = {v} ({unit})")
    name, v = find(flat, "pressure")
    if v is not None:
        hpa, unit = pressure_to_hpa(name, v)
        payload["pressure_hpa"] = round(hpa, 1)
        notes.append(f"pressure    <- {name} = {v} (read as {unit}, sent as {round(hpa, 1)} hPa)")
    offsets = {"pitch": PITCH_OFFSET, "roll": ROLL_OFFSET, "yaw": YAW_OFFSET}
    for what, key in (("pitch", "pitch"), ("roll", "roll"), ("yaw", "yaw"),
                      ("heart_rate", "heart_rate_bpm")):
        name, v = find(flat, what)
        if v is not None:
            if what in offsets:
                v = (v + offsets[what]) % 360
            payload[key] = round(v, 1)
            notes.append(f"{what:<11} <- {name} = {v}")

    # Extra sensor readings (real, from the Sense HAT)
    for what, key in (("humidity", "humidity_pct"), ("peak_accel", "peak_acceleration_g")):
        name, v = find(flat, what)
        if v is not None:
            payload[key] = round(v, 2)
            notes.append(f"{what:<11} <- {name} = {v}")
    q = as_number(flat.get("quality.overall_score"))
    if q is not None:
        payload["quality_score"] = round(q, 2)
        notes.append(f"quality     <- quality.overall_score = {q}")

    # Advisories / tasks the Pi sends
    if isinstance(data, dict) and isinstance(data.get("tasks"), list):
        tasks = []
        for t in data["tasks"][:8]:
            if isinstance(t, dict):
                tasks.append({k: str(t.get(k, ""))[:200] for k in ("id", "priority", "category", "text", "source")})
        payload["tasks"] = tasks
        notes.append(f"tasks       <- tasks ({len(tasks)} items)")

    # Body temperature, blood pressure, blood oxygen. The Pi may send these, but it labels them
    # "simulated" in its own data. We pass that label along so the dashboard never shows made-up
    # numbers as real.
    real = {}
    where = {}
    for what, key in (("body_temp", "body_temp_c"), ("bp_systolic", "bp_systolic"),
                      ("bp_diastolic", "bp_diastolic"), ("spo2", "spo2_pct")):
        name, v = find(flat, what)
        if v is not None:
            real[key] = round(v, 2 if what in ("body_temp",) else 1 if what == "spo2" else 0)
            where[what] = name
            notes.append(f"{what:<11} <- {name} = {v}")
    if all(k in real for k in ("body_temp_c", "bp_systolic", "bp_diastolic")):
        payload.update(real)
        parent = where["body_temp"].rsplit(".", 1)[0] if "." in where["body_temp"] else ""
        label = str(flat.get(parent + ".source", "")).lower() if parent else ""
        flagged = any("simulated" in str(v).lower() for k, v in flat.items()
                      if parent and k.startswith(parent + ".") and ("flags" in k or k.endswith(".source")))
        pi_says_simulated = "simulated" in label or flagged
        payload["vitals_simulated"] = bool(pi_says_simulated)
        if pi_says_simulated:
            notes.append("vitals: the Pi labels these SIMULATED, so the dashboard will too")
    elif SIMULATE_VITALS:
        payload.update(simulated_vitals())
        notes.append("body temp / blood pressure: SIMULATED (Pi has no sensor for them)")
    return payload, notes


def simulated_vitals():
    """Smooth, believable made-up values that drift slowly."""
    t = time.time()
    return {
        "body_temp_c": round(36.8 + 0.08 * math.sin(t / 40), 2),
        "bp_systolic": round(118 + 4 * math.sin(t / 25)),
        "bp_diastolic": round(76 + 3 * math.sin(t / 31)),
        "spo2_pct": round(97.5 + 0.5 * math.sin(t / 50), 1),
        "vitals_simulated": True,
    }


def probe():
    print(f"Asking {PI_URL} ...\n")
    text = fetch_pi()
    print("RAW REPLY FROM THE PI:")
    print(text[:3000])
    print("\nWHAT THIS SCRIPT UNDERSTOOD:")
    try:
        payload, notes = build_payload(text)
    except json.JSONDecodeError:
        print("  The reply is not JSON, so it can't be read yet. Check the RAW REPLY above and the PI_URL setting.")
        return
    for n in notes:
        print("  ", n)
    missing = [k for k in ("temperature_c", "pressure_hpa", "pitch", "roll", "yaw") if k not in payload]
    if missing:
        print("   NOT FOUND:", ", ".join(missing), "(check the RAW REPLY above against the field names this script looks for)")
    print("\nThis would be sent to the dashboard:\n  ", json.dumps(payload))


def run():
    print(f"Pulling from {PI_URL}\nSending to  {DASHBOARD_URL} as {ASTRONAUT_ID}\nCtrl+C to stop.\n")
    last_note = ""
    last_print = 0.0
    while True:
        started = time.monotonic()
        try:
            payload, notes = build_payload(fetch_pi())
            if not any(k in payload for k in ("temperature_c", "pressure_hpa", "pitch", "roll", "yaw")):
                msg = "Pi replied but no sensor values were recognised. Run: python3 pi_poller.py --probe"
            else:
                req = urllib.request.Request(DASHBOARD_URL, data=json.dumps(payload).encode(),
                                             headers={"Content-Type": "application/json"})
                urllib.request.urlopen(req, timeout=3).read()
                msg = "OK  " + json.dumps({k: v for k, v in payload.items() if k != "astronaut_id"})
            if "\n".join(notes) != last_note:
                last_note = "\n".join(notes)
                print("Field mapping:\n  " + "\n  ".join(notes) + "\n")
        except Exception as e:
            msg = f"problem: {e}"
        if msg.startswith("OK") is False or time.monotonic() - last_print > 5:
            print(msg)
            last_print = time.monotonic()
        time.sleep(max(0.0, INTERVAL_SECONDS - (time.monotonic() - started)))


if __name__ == "__main__":
    try:
        probe() if "--probe" in sys.argv else run()
    except KeyboardInterrupt:
        print("\nStopped.")
    except Exception as e:
        print("Could not reach the Pi:", e)
        print("Check: same Wi-Fi as the Pi? Pi's web server running? Address correct?")
