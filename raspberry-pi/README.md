# ASTRA Raspberry Pi Service

This starter runs the ASTRA backend with simulated readings by default. It
stores every evaluated sample in SQLite and exposes the frozen wrist-terminal
contract.

## Requirements

- Python 3.11 or newer;
- Raspberry Pi OS for live Sense HAT mode;
- a Sense HAT and the optional packages in `requirements-pi.txt` for live data.

## Run in simulated mode

```bash
cd raspberry-pi
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
set -a; source .env; set +a
uvicorn app.main:app --host "${ASTRA_HOST:-0.0.0.0}" --port "${ASTRA_PORT:-8000}"
```

Check the service from the Pi or another device on the local network:

```bash
curl http://PI_ADDRESS:8000/health
curl http://PI_ADDRESS:8000/api/v1/status
```

## HTTP interfaces and API documentation

Use `http://PI_ADDRESS:8000` as the base URL. For the current deployment,
`PI_ADDRESS` is `10.0.201.67`.

Team members can follow the step-by-step
[Swagger/API guide](../team/SWAGGER_API_GUIDE.md).

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/` | Redirects to the central-station dashboard. |
| `GET` | `/dashboard` | Opens the browser-based ASTRA Mission Control dashboard. |
| `GET` | `/docs` | Opens the interactive Swagger UI for trying API requests. |
| `GET` | `/redoc` | Opens the alternative ReDoc API reference. |
| `GET` | `/openapi.json` | Returns the machine-readable OpenAPI schema. |
| `GET` | `/health` | Returns service version, sensor mode, sample freshness, baseline progress, failure count, and the latest non-sensitive error. |
| `GET` | `/api/v1/status` | Returns the latest ASTRA state, filtered ambient sensor sample, suit telemetry, derived motion features, quality metadata, simulated biometrics, and simulated tasks. Returns HTTP `503` until the first sample is ready. |
| `GET` | `/api/v1/history?limit=120` | Returns chronological complete status samples. `limit` defaults to `120` and must be between `1` and `300`. |
| `GET` | `/api/v1/crew` | Returns astronaut IDs and display names. |
| `POST` | `/api/v1/messages` | Queues a Central Station message for one astronaut. |
| `GET` | `/api/v1/messages` | Lists the outbox or filters one astronaut's inbox. |
| `POST` | `/api/v1/messages/{id}/ack` | Marks a message delivered after its wearable receives it. |
| `POST` | `/api/v1/chat` | Runs one bounded, single-turn prompt through the Pi's local Gemma model. |
| `GET` | `/api/v1/chat/health` | Reports local model readiness and non-sensitive guardrail limits without loading the model. |

Examples:

```bash
curl http://PI_ADDRESS:8000/health
curl http://PI_ADDRESS:8000/api/v1/status
curl "http://PI_ADDRESS:8000/api/v1/history?limit=20"
curl http://PI_ADDRESS:8000/openapi.json
```

## Central Station to wearable messaging

Messages use a durable local queue:

```text
Central Station -> POST to Pi -> SQLite queue -> wearable poll -> acknowledgement
```

The Pi retains a message while its delivery status is `queued`. The addressed
wearable requests only its own astronaut ID, displays the message, and sends an
acknowledgement. Central Station polls the outbox and changes the status to
`delivered` after that acknowledgement.

Queue a message:

```bash
curl -X POST http://PI_ADDRESS:8000/api/v1/messages \
  -H 'Content-Type: application/json' \
  -d '{
    "recipient_id": "astronaut-1",
    "priority": "CAUTION",
    "text": "Return to the station airlock."
  }'
```

Read the next pending message for a wearable:

```bash
curl 'http://PI_ADDRESS:8000/api/v1/messages?recipient_id=astronaut-1&pending_only=true&limit=1'
```

After showing message `1`, the wearable acknowledges it:

```bash
curl -X POST http://PI_ADDRESS:8000/api/v1/messages/1/ack \
  -H 'Content-Type: application/json' \
  -d '{"recipient_id":"astronaut-1"}'
```

Message text is normalized, must contain 1–240 characters, and is stored in the
same SQLite database as telemetry. The initial roster is `astronaut-1` through
`astronaut-4`; its display names live in `app/main.py`. Priorities are `INFO`,
`ADVISORY`, `CAUTION`, and `ALERT`.

This prototype has no user authentication. Keep it on a trusted private LAN;
do not expose port 8000 directly to the internet.

## Local Gemma chat endpoint

Clients can send one stateless prompt to the locally installed Gemma 3 270M
model. No prompt or response is sent to the internet.

```bash
curl --max-time 130 -X POST http://PI_ADDRESS:8000/api/v1/chat \
  -H 'Content-Type: application/json' \
  -d '{
    "message": "Explain why checking the airlock seal matters.",
    "max_tokens": 24,
    "temperature": 0.2
  }'
```

Example response shape:

```json
{
  "reply": "A secure airlock seal prevents pressure loss.",
  "model": "gemma-3-270m-it-Q4_K_M",
  "generated_at": "2026-11-14T23:30:00Z",
  "latency_seconds": 34.2,
  "local": true,
  "response_type": "model",
  "safety_notice": "Prototype assistant; not medical, emergency, or flight-certified guidance."
}
```

Limits and behavior:

- `message` is required and limited to 400 characters;
- `max_tokens` defaults to 24 and must be between 1 and 32;
- `temperature` defaults to `0.2`; clients may request up to `1.0`, but the
  server caps actual inference at `ASTRA_LLM_MAX_TEMPERATURE=0.4`;
- the endpoint is single-turn and does not store conversation history;
- control characters and chat-template injection tokens are rejected or
  intercepted;
- prompt injection, credential extraction, hazardous-operation requests, and
  medical/emergency direction receive an immediate deterministic guardrail
  response without launching the model;
- model output has ANSI/control text removed, role markers removed, whitespace
  normalized, and length capped before it is returned;
- empty, prompt-leaking, secret-like, or false action-claim output is replaced
  by deterministic safe fallback text instead of returning an empty answer;
- `response_type` truthfully identifies `model`, `guardrail`, or `fallback`;
- only one generation runs at a time so LLM load cannot multiply;
- the llama context is bounded to 1024 tokens and standard input is closed;
- inference runs in a worker thread and does not block the sensor sampler;
- expected latency is tens of seconds on this Raspberry Pi 3;
- HTTP `429` means another generation is active;
- HTTP `503` means the binary or model is unavailable or disabled;
- HTTP `504` means the local generation exceeded its timeout.

The endpoint is experimental. Do not use its generated text as a medical,
flight-safety, or emergency-control decision. Deterministic sensor alerts remain
the primary safety path.

Before a demo, check readiness without loading Gemma:

```bash
curl http://PI_ADDRESS:8000/api/v1/chat/health
```

Expected `status` is `ready`. The response reports model name, input/output
limits, timeout, maximum temperature, and guardrail version, but never exposes
runtime file paths, credentials, prompts, or environment variables.

Open the central-station dashboard from a laptop on the same private LAN:

```text
http://PI_ADDRESS:8000/dashboard
```

The dashboard source lives independently in `../central-station/`, while the Pi
serves it locally so the laptop needs only a modern browser and no internet
connection. It shows current state, sensor readings, service health, baseline
progress, bounded trend history, and recent telemetry. The CYD continues to use
the same compact `/api/v1/status` response.

`/health` reports sample freshness, restored baseline size, consecutive sampling
failures, and a non-sensitive error class. It becomes `degraded` if sampling is
stale or the sensor/storage path fails.

`/api/v1/history?limit=120` returns chronological status samples for the local
dashboard. The limit is constrained to 1–300 rows to keep Pi memory and response
size bounded.

`ASTRA_SIMULATION_PROFILE=normal` stays near room conditions. `cycle` produces
a short, clearly simulated deviation after the baseline has learned. Simulation
is always returned with `"source": "simulated"`.

## Run with a Sense HAT

Install the Raspberry Pi OS driver and select the live adapter:

```bash
sudo apt-get install sense-hat
export ASTRA_SENSOR_MODE=sense-hat
export ASTRA_SENSE_HAT_PYTHON=/usr/bin/python3
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Raspbian Buster's working Sense HAT bindings belong to its system Python 3.7,
while FastAPI runs in the project's Python 3.11 environment. ASTRA maintains a
persistent local JSON-lines bridge between those runtimes. It never sends
sensor data to the internet. The service exits with a clear error if Sense HAT
mode is selected but its library or hardware is unavailable.

The API exposes all continuous Sense HAT measurements:

| API field | Unit |
| --- | --- |
| `temperature_c` | degrees Celsius |
| `humidity_pct` | percent relative humidity |
| `pressure_hpa` | hectopascals |
| `acceleration_g.x/y/z` | g |
| `gyroscope_rps.x/y/z` | radians per second |
| `magnetic_uT.x/y/z` | microteslas |
| `orientation_deg.pitch/roll/yaw` | degrees |

Sensor failures and invalid startup readings become `null`; they are never
replaced with believable zeros. The joystick is an event input and the LED
matrix is an output, not periodic telemetry. The tested board does not contain
the optional TCS34725 color sensor.

## Edge filtering, features, and data quality

ASTRA samples acceleration and gyroscope data at approximately 20 Hz inside
each API interval. Environmental spikes are reduced with median and
exponential smoothing, vectors are smoothed, and orientation angles use a
circular filter so the `359` to `0` degree boundary is handled correctly. All
processing stays on the Pi; it does not require the internet or an LLM.

The original `sensors` field names remain intact. Two additive objects describe
what the Pi derived from the sample window:

| Object/field | Meaning |
| --- | --- |
| `features.acceleration_magnitude_g` | Magnitude of the latest acceleration vector. |
| `features.motion_rms_g` | RMS motion around the window's mean acceleration. |
| `features.peak_acceleration_g` | Largest acceleration magnitude in the window. |
| `features.rotation_rms_rps` | RMS angular velocity in the window. |
| `features.orientation_change_deg` | Change between the first and last orientation in the window. |
| `quality.overall_score` | Normalized `0.0` to `1.0` sample-quality score. |
| `quality.sample_count` | Valid high-rate IMU samples used. |
| `quality.expected_sample_count` | Expected samples for the configured interval. |
| `quality.valid_ratio` | Ratio of valid readings to expected readings. |
| `quality.filtered` | Confirms that the edge filter was applied. |
| `quality.flags` | Machine-readable reasons for reduced quality. |

The live deployment normally collects roughly 20 or more IMU readings per API
sample. Configure the target with `ASTRA_IMU_SAMPLE_HZ=20`.

## Simulated biometrics

The `biometrics` object provides randomized demo values for heart rate, blood
pressure, oxygen saturation, and body temperature. The values move gradually
within bounded plausible ranges instead of jumping independently on every
sample. They are **not measured by the Sense HAT, are not medical data, and
must not be used for diagnosis or safety decisions**.

Every generated object is explicitly labeled with `"source": "simulated"` and
the quality flag `"simulated_biometrics"`. Set
`ASTRA_BIOMETRICS_MODE=disabled` to return null biometric values while
preserving the JSON shape.

Heart rate includes `heart_rate_status` plus `heart_rate_thresholds`. The demo
uses `120 bpm` as warn-high and `140 bpm` as critical-high. The 140 bpm value is
adapted from NASA's suited heat-storage rationale, which says performance
impairment begins when pulse exceeds 140 bpm; it is not a personal medical
diagnosis threshold.

## Simulated suit environment

`suit_pressure` and `suit_temperature` are additive objects in status and
history responses. They are randomized, smoothly changing demo values and are
never inferred from Sense HAT ambient readings.

| Object | Normal demo value | Status boundaries |
| --- | --- | --- |
| `suit_pressure` | about `296 hPa` / `4.29 psi` | critical low `<=248`; warn low `<=276`; warn high `>=365`; critical high `>=455 hPa` |
| `suit_temperature` | about `24 °C` | critical low `<10`; warn low `<20`; comfort `20–30`; warn high `>30`; critical high `>43 °C` |

Every object has `timestamp`, `status`, `source`, `thresholds`, and `flags`.
The default source is `simulated`; set `ASTRA_SUIT_TELEMETRY_MODE=disabled` to
return the same JSON shape with unavailable values.

The pressure thresholds are prototype interpretations of published EMU design
numbers, not a NASA alarm scheme. The temperature comfort band combines NASA
suit-air comfort material; the 10/43 °C outer limits are adapted from internal
touch-temperature requirements and are not validated suit-air alarm limits.
The Sense HAT pressure sensor's approximately 260 hPa lower range also means it
is not suitable for directly proving the 248 hPa critical-low boundary.

## Simulated mission tasks

`tasks` is an additive array in every status and history response. The demo
publishes a randomly sized batch of one to three unique mission messages. The
batch remains unchanged for five minutes, then the Pi selects a new batch. Each
task includes an ID, priority, category, text, issue time, and
`"source": "simulated"`.

The separate catalog is [`app/data/task_messages.txt`](app/data/task_messages.txt).
It contains exactly 200 editable messages in this format:

```text
PRIORITY|category|Message text
```

Valid priorities are `INFO`, `ADVISORY`, `CAUTION`, and `ALERT`. The catalog
includes navigation, weather, station, equipment, communications, crew,
science, logistics, safety, and EVA messages. Configure rotation with
`ASTRA_TASK_INTERVAL_SECONDS=300.0`. Restart `astra.service` after editing the
catalog so it is reloaded.

## Test

The core analyzer and SQLite tests use Python's standard library:

```bash
python -m unittest discover -s tests -v
```

The anomaly detector is a transparent prototype, not a medical or
flight-certified safety system. Its defaults learn 20 samples, use per-sensor
dispersion floors, and require two consecutive samples to confirm state
changes.

## Restart behavior

By default, startup restores up to 300 baseline-eligible rows from SQLite. It
only restores rows matching the active source, so simulated data never seeds a
live Sense HAT baseline. Samples with anomaly-level scores are excluded even if
state stabilization had not yet changed the displayed state.

Set `ASTRA_RESTORE_BASELINE=false` to force a new learning window. To discard
history completely, stop the service and move `data/astra.db` to a backup
location before restarting.

## Run automatically with systemd

The deployed Pi uses the included `systemd/astra.service` unit. Install or
refresh it with:

```bash
sudo cp systemd/astra.service /etc/systemd/system/astra.service
sudo systemctl daemon-reload
sudo systemctl enable --now astra.service
```

Operate and inspect it with:

```bash
systemctl status astra.service --no-pager
sudo systemctl restart astra.service
journalctl -u astra.service -n 100 --no-pager
```

The unit starts ASTRA after networking, reads the private `.env` file, runs as
the unprivileged `pi` user, and automatically restarts after an unexpected
exit. `systemctl stop astra.service` remains an intentional stop and does not
trigger a restart.

## Prototype limitations

- OpenAI explanations are intentionally absent from this first offline
  milestone; the optional chat route uses local Gemma and every sensor summary
  remains deterministic.
- Sense HAT temperature is affected by heat from the Pi and is not a certified
  cabin or physiological measurement.
