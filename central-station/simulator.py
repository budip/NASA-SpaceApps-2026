"""Nine fake astronauts for the dashboard (the 10th, Astronaut-5, is the real Raspberry Pi).

Run (while server.py is running):   python3 simulator.py      (run_all.py starts it for you)

Everything here is SIMULATED demo data. The IDs skip Astronaut-5 because that one is the real Pi.
Over a repeating 60-second loop, a few astronauts have a problem so you can see how the dashboard reacts:
  Astronaut-1 : slow suit-pressure leak (45-58 s)
  Astronaut-2 : suit temperature climbs, body temperature follows (whole loop)
  Astronaut-3 : loses signal (20-35 s)
  Astronaut-4 : heart rate and blood pressure spike (40-50 s)
  Astronaut-8 : blood oxygen dips into warning (30-45 s)
  Astronaut-10: blood pressure drifts high into warning (15-30 s)
  Astronaut-6, 7, 9: stay normal (small natural wobble)
Body temperature, blood pressure and blood oxygen are SIMULATED for everyone: the project has no
sensor for them yet, and the dashboard labels them as simulated.
"""
import json
import math
import random
import sys
import time
import urllib.request

SERVER = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5002"
IDS = [1, 2, 3, 4, 6, 7, 8, 9, 10]
random.seed(7)
# each fake astronaut has its own slightly different "normal" so the wall of numbers looks natural
BASE = {i: {"temp": random.uniform(21.8, 24.6), "press": random.uniform(293, 299),
            "hr": random.uniform(66, 82), "body": random.uniform(36.6, 37.0),
            "sys": random.uniform(112, 124), "dia": random.uniform(72, 80),
            "phase": random.uniform(0, 6.28)} for i in IDS}


def ramp(t, start, end, rise=5.0, fall=8.0):
    """0 before `start`, rises smoothly to 1 over `rise` s, holds until `end`, then falls to 0 over `fall` s.
    Real readings change gradually, so the demo problems build up and fade instead of jumping."""
    if t < start or t > end + fall:
        return 0.0
    if t < start + rise:
        x = (t - start) / rise
    elif t <= end:
        return 1.0
    else:
        x = 1 - (t - end) / fall
    return x * x * (3 - 2 * x)


def send(payload):
    req = urllib.request.Request(
        SERVER + "/update",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        urllib.request.urlopen(req, timeout=2).read()
    except Exception as e:
        print("send failed:", e)


def make(n, t, temp=None, pressure=None, heart=None, body=None, systolic=None, diastolic=None, spo2=97.6):
    b = BASE[n]
    wave = math.sin(t / 5.5 + b["phase"]) * 0.6 + math.sin(t / 2.3 + b["phase"]) * 0.4   # gentle natural wobble so lines look alive
    heart = b["hr"] + 2.2 * wave if heart is None else heart
    return {
        "astronaut_id": f"Astronaut-{n}",
        "data_source": "sim",
        "temperature_c": round((b["temp"] if temp is None else temp) + random.uniform(-0.15, 0.15), 1),
        "pressure_hpa": round((b["press"] if pressure is None else pressure) + random.uniform(-0.8, 0.8), 1),
        "heart_rate_bpm": round(heart + random.uniform(-1.5, 1.5)),
        "pitch": round(random.uniform(-6, 6) % 360, 1),
        "roll": round(random.uniform(-6, 6) % 360, 1),
        "yaw": round(random.uniform(0, 360), 1),
        # SIMULATED vitals (no real sensor yet)
        "body_temp_c": round((b["body"] if body is None else body) + random.uniform(-0.04, 0.04), 2),
        "bp_systolic": round((b["sys"] if systolic is None else systolic) + random.uniform(-1.5, 1.5)),
        "bp_diastolic": round((b["dia"] if diastolic is None else diastolic) + random.uniform(-1.5, 1.5)),
        "spo2_pct": round(spo2 + random.uniform(-0.4, 0.4), 1),
        "vitals_simulated": True,
    }


start = time.time()
print("Sending 9 simulated astronauts to", SERVER, "(Ctrl+C to stop)")
while True:
    t = (time.time() - start) % 60
    now = time.time()

    # Astronaut-1: slow suit leak from 45 s to 58 s (about 296 hPa falling toward 270)
    send(make(1, now, pressure=BASE[1]["press"] - (t - 45) * 2 if 45 < t < 58 else None))

    # Astronaut-2: suit temperature climbs; body temperature follows once the suit gets hot
    temp2 = 23 + t * 0.35
    send(make(2, now, temp=temp2, body=36.8 + max(0, temp2 - 28) * 0.15, systolic=124, diastolic=80, heart=85))

    # Astronaut-3: goes silent from 20 s to 35 s
    if not (20 < t < 35):
        send(make(3, now))

    # Astronaut-4: heart rate and blood pressure spike
    k = ramp(t, 38, 50)
    send(make(4, now, heart=BASE[4]["hr"] + k * (132 - BASE[4]["hr"]), systolic=BASE[4]["sys"] + k * 32,
              diastolic=BASE[4]["dia"] + k * 18))

    send(make(6, now))
    send(make(7, now))

    # Astronaut-8: blood oxygen dips into the warning range
    send(make(8, now, spo2=97.6 - ramp(t, 28, 45) * 4.6))

    send(make(9, now))

    # Astronaut-10: blood pressure drifts high
    send(make(10, now, systolic=BASE[10]["sys"] + ramp(t, 12, 30) * 30))

    time.sleep(1)
