# Calling the ASTRA API with Swagger

Use this guide from a laptop or phone connected to the same local network as
the Raspberry Pi. The current Pi address is `10.0.201.67`, but DHCP may assign
a different address after a reboot or network change.

## Quick start

1. Confirm the Pi is powered on and ASTRA is running.
2. Connect your device to the same Wi-Fi or LAN as the Pi.
3. Open this URL in a browser:

   ```text
   http://10.0.201.67:8000/docs
   ```

4. Expand `GET /health`.
5. Select **Try it out**, then **Execute**.
6. A working service returns HTTP `200` and JSON containing:

   ```json
   {
     "status": "ok",
     "sensor_mode": "sense-hat"
   }
   ```

7. Repeat with `GET /api/v1/status` to see the newest live ambient sensor
   sample, simulated suit environment, derived features, quality score,
   simulated biometrics, and mission tasks.
8. For history, expand `GET /api/v1/history`, select **Try it out**, enter a
   `limit` from `1` to `300`, and select **Execute**.

No API key or username is currently required. Telemetry routes use `GET`; the
two messaging operations use `POST` with a JSON request body.

## Interfaces

Use `http://10.0.201.67:8000` as the current base URL.

| Interface | Path | Use |
| --- | --- | --- |
| Swagger UI | `/docs` | Interactively execute and inspect API calls. |
| ReDoc | `/redoc` | Read-only API reference. |
| OpenAPI JSON | `/openapi.json` | Machine-readable schema for tools and code generation. |
| Health | `/health` | Service, sensor mode, freshness, and error state. |
| Latest status | `/api/v1/status` | Newest ASTRA state, sensors, features, quality, demo biometrics, and task. |
| History | `/api/v1/history?limit=120` | Oldest-to-newest complete recent samples. |
| Crew roster | `/api/v1/crew` | Astronaut IDs accepted by the message API. |
| Send message | `POST /api/v1/messages` | Queue a message for one astronaut's wearable. |
| Message outbox/inbox | `/api/v1/messages` | Inspect queued and delivered messages. |
| Acknowledge | `POST /api/v1/messages/{id}/ack` | Confirm that the addressed wearable received a message. |
| Local LLM chat | `POST /api/v1/chat` | Send one bounded prompt to Gemma running on the Pi. |
| Local LLM readiness | `GET /api/v1/chat/health` | Confirm the model and guardrail configuration are ready before the demo. |
| Dashboard | `/dashboard` | Browser mission-control display. |

Swagger's page assets are loaded from a public CDN by FastAPI's default UI, so
the browser needs internet access to render `/docs`. The API itself remains
local. ReDoc also uses a CDN asset. If either documentation UI does not render,
use `/openapi.json`, `curl`, or the dashboard.

## Sensor fields and units

The `sensors` object in status and history responses contains:

| Field | Meaning | Unit |
| --- | --- | --- |
| `temperature_c` | Sense HAT temperature | degrees Celsius |
| `humidity_pct` | Relative humidity | percent |
| `pressure_hpa` | Barometric pressure | hectopascals |
| `acceleration_g.x/y/z` | Filtered 3-axis acceleration | g |
| `gyroscope_rps.x/y/z` | Filtered 3-axis angular velocity | radians per second |
| `magnetic_uT.x/y/z` | Filtered 3-axis magnetic field | microteslas |
| `orientation_deg.pitch/roll/yaw` | Filtered fused orientation | degrees |

A sensor that cannot provide a valid reading returns `null`; it is never
silently replaced with zero. The Sense HAT joystick is an event input and the
LED matrix is an output, so neither is part of periodic telemetry. This board
does not have the optional TCS34725 color sensor.

The Sense HAT's `pressure_hpa` is ambient barometric pressure, commonly near
900–1020 hPa on Earth. It is not spacesuit pressure. Clients must use the
separate `suit_pressure.pressure_hpa` field for the simulated suit value.

## Suit fields and prototype thresholds

The service adds two independently sourced objects without renaming any
existing fields:

| Field | Meaning |
| --- | --- |
| `suit_pressure.pressure_hpa` | Simulated suit pressure in hPa. |
| `suit_pressure.pressure_psi` | The same simulated pressure in psi. |
| `suit_pressure.status` | `CRITICAL_LOW`, `WARN_LOW`, `NOMINAL`, `WARN_HIGH`, `CRITICAL_HIGH`, or `UNAVAILABLE`. |
| `suit_temperature.temperature_c` | Simulated suit-air temperature in Celsius. |
| `suit_temperature.status` | `CRITICAL_LOW`, `WARN_LOW`, `COMFORT`, `WARN_HIGH`, `CRITICAL_HIGH`, or `UNAVAILABLE`. |
| `source` | `simulated` by default; always inspect this field. |
| `thresholds` | Machine-readable copy of the demo boundaries. |
| `flags` | Simulation and standards-interpretation warnings. |

Pressure uses nominal `296 hPa`, warning bounds `276/365 hPa`, and critical
bounds `248/455 hPa`. Suit-air temperature uses a `20–30 °C` comfort band,
warning zones from `10–20 °C` and above `30–43 °C`, and critical values below
`10 °C` or above `43 °C`.

These are hackathon prototype interpretations, not certified NASA alarms. In
particular, the temperature outer limits are adapted from internal surface
touch-temperature material, not a validated suit-air alarm standard.

## Derived features and quality

The Pi processes a high-rate IMU window locally before publishing it. The
`features` object contains motion magnitude, motion RMS, peak acceleration,
rotation RMS, and orientation change. The `quality` object reports:

| Field | Use |
| --- | --- |
| `overall_score` | `0.0` to `1.0`; higher means a more complete sample window. |
| `sample_count` | Number of valid IMU readings used. |
| `expected_sample_count` | Target reading count for the interval. |
| `valid_ratio` | Valid readings divided by expected readings. |
| `filtered` | Whether edge filtering was applied. |
| `flags` | Reasons the score was reduced, or an empty array. |

Consumers should inspect `quality.overall_score` and `quality.flags` before
using motion features. This deterministic processing runs directly on the Pi
and does not wait for the local language model.

## Demo biometrics and tasks

The current biometric values are randomized for the hackathon demonstration.
They are not measured by the Sense HAT and are not medical data. Check
`biometrics.source`, which is always `simulated` in this mode.

| Field | Unit or meaning |
| --- | --- |
| `biometrics.heart_rate_bpm` | Beats per minute. |
| `biometrics.heart_rate_status` | Warn-high at 120 bpm; critical-high at 140 bpm. |
| `biometrics.heart_rate_thresholds` | Machine-readable demo thresholds. |
| `biometrics.blood_pressure.systolic_mm_hg` | Simulated systolic pressure in mmHg. |
| `biometrics.blood_pressure.diastolic_mm_hg` | Simulated diastolic pressure in mmHg. |
| `biometrics.oxygen_saturation_pct` | Simulated SpO2 percentage. |
| `biometrics.body_temperature_c` | Simulated body temperature in Celsius. |
| `biometrics.quality.flags` | Contains `simulated_biometrics`. |

`tasks` is an array. The demo returns a random batch of one to three unique
messages from a separate 200-message catalog. The batch stays stable for five
minutes before it is replaced. A task has `id`, `priority`, `category`, `text`,
`issued_at`, and `source`. The task source is explicitly `simulated`.
Priorities are `INFO`, `ADVISORY`, `CAUTION`, and `ALERT`.

Example excerpt:

```json
{
  "quality": {
    "overall_score": 1.0,
    "sample_count": 21,
    "expected_sample_count": 20,
    "valid_ratio": 1.0,
    "filtered": true,
    "flags": []
  },
  "biometrics": {
    "heart_rate_bpm": 74.0,
    "heart_rate_status": "NOMINAL",
    "blood_pressure": {
      "systolic_mm_hg": 118.0,
      "diastolic_mm_hg": 77.0
    },
    "oxygen_saturation_pct": 98.6,
    "body_temperature_c": 36.76,
    "source": "simulated"
  },
  "suit_pressure": {
    "pressure_hpa": 296.0,
    "pressure_psi": 4.29,
    "status": "NOMINAL",
    "source": "simulated"
  },
  "suit_temperature": {
    "temperature_c": 24.0,
    "status": "COMFORT",
    "source": "simulated"
  },
  "tasks": [
    {
      "id": "TASK-154",
      "priority": "CAUTION",
      "category": "logistics",
      "text": "A required tool is outside the marked safe area.",
      "source": "simulated"
    }
  ]
}
```

## Chat with local Gemma in Swagger

1. Expand `GET /api/v1/chat/health` and execute it. Continue when `status` is
   `ready`.
2. Expand `POST /api/v1/chat` and select **Try it out**.
3. Use a request body such as:

   ```json
   {
     "message": "Explain the current warning in plain language.",
     "max_tokens": 24,
     "temperature": 0.2
   }
   ```

4. Select **Execute** and wait. Gemma runs entirely on the Raspberry Pi 3, so a
   short answer normally takes tens of seconds.

This endpoint is stateless: each request is a new single-turn conversation.
Messages are limited to 400 characters and output is limited to 32 tokens. Only
one request can generate at a time. Actual temperature is server-capped at
`0.4` and context is bounded to 1024 tokens. HTTP `429` means the model is busy,
`503` means the local binary or model is unavailable, and `504` means generation
timed out. Client HTTP timeouts should be at least 120 seconds.

Every success includes `response_type`: `model` means Gemma produced validated
text, `guardrail` means a deterministic safety rule answered without launching
Gemma, and `fallback` means model text was empty or failed validation and was
replaced safely. Prompt injection, credential requests, hazardous operations,
and medical/emergency direction are handled by deterministic guardrails. The
endpoint never changes sensor state or executes a requested operation.

Gemma output is experimental and must not replace deterministic sensor alerts,
medical judgment, or emergency procedures. The endpoint currently has no
authentication and must stay on the trusted private LAN.

## Send a message in Swagger

1. Expand `GET /api/v1/crew` and execute it to find the astronaut ID.
2. Expand `POST /api/v1/messages` and select **Try it out**.
3. Replace the request body with:

   ```json
   {
     "recipient_id": "astronaut-1",
     "priority": "CAUTION",
     "text": "Return to the station airlock."
   }
   ```

4. Select **Execute**. HTTP `201` means the Pi stored the message. Its status is
   `queued` until the wearable acknowledges it.
5. Execute `GET /api/v1/messages` to inspect the outbox. A successfully received
   message has `status: "delivered"` and a non-null `delivered_at`.

For wearable testing, execute `GET /api/v1/messages` with
`recipient_id=astronaut-1`, `pending_only=true`, and `limit=1`. Then call
`POST /api/v1/messages/{id}/ack` with the returned ID and this body:

```json
{
  "recipient_id": "astronaut-1"
}
```

The API accepts messages of 1–240 characters and rejects unknown astronaut
IDs. This hackathon endpoint has no authentication, so it belongs only on the
trusted private LAN.

## Command-line equivalents

Replace `PI_ADDRESS` if the Pi changes networks:

```sh
PI_ADDRESS=10.0.201.67
curl "http://${PI_ADDRESS}:8000/health"
curl "http://${PI_ADDRESS}:8000/api/v1/status"
curl "http://${PI_ADDRESS}:8000/api/v1/history?limit=10"
curl "http://${PI_ADDRESS}:8000/openapi.json"
curl "http://${PI_ADDRESS}:8000/api/v1/chat/health"
```

JavaScript example:

```js
const response = await fetch("http://10.0.201.67:8000/api/v1/status");
if (!response.ok) throw new Error(`ASTRA returned ${response.status}`);
const astra = await response.json();
console.log({
  status: astra.status,
  suitPressureHpa: astra.suit_pressure.pressure_hpa,
  suitPressureStatus: astra.suit_pressure.status,
  suitAirTemperatureC: astra.suit_temperature.temperature_c,
  suitTemperatureStatus: astra.suit_temperature.status,
  heartRateStatus: astra.biometrics.heart_rate_status,
});
```

Python example:

```python
import json
from urllib.request import urlopen

with urlopen("http://10.0.201.67:8000/api/v1/status", timeout=5) as response:
    astra = json.load(response)

print(astra["status"])
print(astra["suit_pressure"]["pressure_hpa"], "hPa")
print(astra["suit_temperature"]["temperature_c"], "C")
print(astra["biometrics"]["heart_rate_status"])
```

## Find the Pi address

On the Pi, run:

```sh
hostname -I
```

Use the private LAN address from the output. Then open
`http://NEW_ADDRESS:8000/docs`. You can also connect by hostname if the network
supports mDNS:

```text
http://raspberrypi.local:8000/docs
```

## Troubleshooting

- **Connection timed out:** confirm both devices are on the same network and
  recheck `hostname -I` on the Pi.
- **Connection refused:** ASTRA is not listening on port `8000`; use the start
  and log commands in `RASPBERRY_PI_SSH.md`.
- **Swagger or ReDoc opens but stays blank:** the UI's CDN assets are
  unavailable; call the endpoint with `curl` or inspect `/openapi.json`.
- **HTTP 503 from status:** startup has not produced its first sensor sample.
  Wait up to one minute for the Buster Sense HAT bridge, then retry.
- **Health says `degraded`:** inspect `consecutive_failures`, `last_error`, and
  `sample_age_seconds`, then run
  `journalctl -u astra.service -n 100 --no-pager` on the Pi.
- **A field is `null`:** the read was invalid or unavailable. Check HAT seating
  and I2C devices rather than substituting zero.

Do not put the Pi account password or any future API keys in source code,
Swagger screenshots, issue trackers, or chat messages.
