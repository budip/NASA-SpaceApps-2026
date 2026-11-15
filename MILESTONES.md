# ASTRA Milestones and Activity Log

## Session record

- Date: 2026-11-13
- Time zone: America/Los_Angeles (PST)
- Project: ASTRA — NASA Space Apps 2026
- Raspberry Pi: `pi@192.168.4.191`
- Purpose: prepare the Raspberry Pi, deploy and validate ASTRA, document the API, and evaluate an offline Gemma 3 experiment
- Credential policy: the SSH password and all other secrets are intentionally omitted

## Milestone summary

| Milestone | Status | Evidence |
| --- | --- | --- |
| Establish SSH access | Complete | Interactive login to `pi@192.168.4.191` succeeded. |
| Inventory the Pi and projects | Complete | Hardware, OS, storage, writable locations, and the three ASTRA components were identified. |
| Prepare a deployment location | Complete | `/home/pi/Documents/NASA-SpaceApps-2026` was created and is writable by `pi`. |
| Install a project-safe Python runtime | Complete | Python 3.11.18 and `pip3.11` were installed under `/usr/local` while system Python 3.7.3 was preserved. |
| Deploy ASTRA source | Complete | The repository was transferred with secrets, Git metadata, caches, databases, and build output excluded. |
| Install backend dependencies | Complete | FastAPI 0.162.7, Uvicorn 0.54.0, and their dependencies were installed in the project virtual environment. |
| Validate backend logic | Complete | All 10 unit tests passed on the Pi with Python 3.11.18. |
| Run simulated ASTRA service | Complete for this session | Health and status endpoints returned valid simulated data; baseline reached 300 samples. |
| Validate browser dashboard | Complete | Dashboard, CSS, and JavaScript returned HTTP 200 after correcting the HTML filename. |
| Validate API documentation | Complete | Swagger, ReDoc, and OpenAPI endpoints returned HTTP 200 and were documented. |
| Prepare Gemma 3 benchmark | Paused safely | `llama.cpp` was cloned and configured, but compilation was stopped at about 3% because the Pi entered active undervoltage/throttling. |
| Install Gemma 3 model | Not started | No model file was downloaded. |
| Integrate an LLM into FastAPI | Not started | Decision deferred until a stable-power benchmark demonstrates acceptable latency and memory use. |

## Hardware and operating-system inventory

| Item | Observed value |
| --- | --- |
| Board | Raspberry Pi 3 Model B Plus Rev 1.3 |
| CPU | Four Cortex-A53 cores, up to 1.4 GHz |
| Architecture | `armv7l`, 32-bit `armhf` userland |
| RAM visible to Linux | 744 MiB |
| Swap | 99 MiB |
| OS | Raspbian GNU/Linux 10 (Buster) |
| Kernel | `5.10.103-v7+` |
| Root filesystem | 29 GB total |
| Last checked free space | Approximately 18 GB; 37% used |
| ASTRA project size | Approximately 62 MB, including its virtual environment and runtime data |
| Partial LLM workspace | Approximately 231 MB |

## Detailed activity log

### 1. SSH access and connection documentation

- Connected with `ssh pi@192.168.4.191`.
- Confirmed the host is reachable on SSH port 22.
- Observed a shell-startup warning caused by a malformed `PATH` export. It does not prevent login.
- Saved connection, deployment, runtime, and shutdown instructions in `RASPBERRY_PI_SSH.md`.
- Did not store the SSH password in any file.

### 2. Project and destination inventory

The local repository contains three runnable components:

- `raspberry-pi/`: FastAPI backend, sensor adapters, anomaly analysis, and SQLite storage.
- `central-station/`: browser dashboard served by the backend.
- `wearable/`: ESP32/CYD firmware built and uploaded from a development computer.

No existing NASA or hackathon project directory was found on the Pi. No USB storage was mounted. `/home/pi/Documents` was writable, so the following destination was selected and created:

```text
/home/pi/Documents/NASA-SpaceApps-2026
```

### 3. Python 3.11 installation

Raspbian Buster only offered Python 3.7 through its configured package repositories. The project requires Python 3.11 or newer, so Python 3.11.18 was built from the official source and installed alongside the system runtime.

Actions performed:

1. Detected that the old Buster mirror returned HTTP 404.
2. Backed up `/etc/apt/sources.list` to `/etc/apt/sources.list.pre-python311-backup`.
3. Replaced the obsolete main mirror with `https://legacy.raspbian.org/raspbian/`.
4. Refreshed package metadata.
5. Installed compiler and development headers for SSL, SQLite, compression, readline, curses, Tk, FFI, UUID, and related standard-library modules.
6. Downloaded the Python 3.11.18 source tarball from `python.org`.
7. Verified its published SHA-256 checksum before extraction.
8. Configured and compiled CPython conservatively for the Pi.
9. Installed with `make altinstall`, avoiding replacement of `/usr/bin/python3`.
10. Verified `ssl`, `sqlite3`, `zlib`, `bz2`, `lzma`, `ctypes`, and `venv` imports.
11. Created and tested a temporary Python 3.11 virtual environment.
12. Removed temporary source, build, log, and test-environment files.

Installed commands:

```text
/usr/local/bin/python3.11
/usr/local/bin/pip3.11
```

Preserved operating-system runtime:

```text
/usr/bin/python3 -> Python 3.7.3
```

### 4. Source deployment

The repository was transferred with `rsync`. The upload contained 52 entries and approximately 152 KB of source and documentation before dependency installation.

Excluded from transfer:

- `.git/`
- `.pio/` and other build caches
- Python virtual environments and bytecode
- SQLite databases and logs
- `.env` files other than `.env.example`
- `wearable/include/secrets.h`
- editor and operating-system metadata

### 5. Backend environment and dependencies

Created the backend environment at:

```text
/home/pi/Documents/NASA-SpaceApps-2026/raspberry-pi/.venv
```

Installed from `requirements.txt`:

- FastAPI 0.162.7
- Uvicorn 0.54.0 with standard extras
- Pydantic, Starlette, AnyIO, uvloop, httptools, watchfiles, WebSockets, and supporting packages

Created `.env` from the non-secret `.env.example`. The active configuration selected:

- Host: `0.0.0.0`
- Port: `8000`
- Sensor mode: `simulated`
- Simulation profile: `cycle`
- SQLite path: `data/astra.db`
- Baseline size: 20 samples
- State confirmation: 2 samples
- Baseline restoration: enabled

### 6. Test results

Ran:

```sh
.venv/bin/python -m unittest discover -s tests -v
```

Result:

```text
Ran 10 tests in 2.515s
OK
```

The tests covered baseline learning, normal and anomalous states, missing readings, consecutive-state confirmation, baseline restoration, sampling failure behavior, SQLite persistence, source filtering, and bounded chronological history.

### 7. Service launch and runtime validation

Started Uvicorn as a background process and stored runtime information under `raspberry-pi/data/`:

- PID file: `data/astra.pid`
- Service log: `data/astra.log`
- SQLite database: `data/astra.db`

The PID observed during this session was `19553`; PIDs are transient and must not be assumed after restart.

Last verified health before stopping work:

- Service status: `ok`
- Version: `0.2.0`
- Sensor mode: `simulated`
- Baseline samples: `300`
- Consecutive failures: `0`
- Last error: `null`

The service was launched with `nohup`, not installed as a `systemd` service. It will not automatically restart after a Pi reboot or shutdown.

### 8. Dashboard repair

Initial external checks found:

- `/health`: HTTP 200
- `/api/v1/status`: valid `NORMAL` simulated response
- `/dashboard`: HTTP 500

Root cause:

- The dashboard HTML file was named `central-station/1.html`.
- The backend and documentation expected `central-station/index.html`.

Resolution:

- Renamed the local source file to `central-station/index.html`.
- Synchronized the corrected file to the Pi.
- Retested the dashboard and static assets.

Final results:

- `/dashboard`: HTTP 200
- `/static/dashboard.css`: HTTP 200
- `/static/dashboard.js`: HTTP 200

### 9. API and documentation validation

The following local-network URLs were verified and documented:

| Interface | URL |
| --- | --- |
| Dashboard | `http://192.168.4.191:8000/dashboard` |
| Swagger UI | `http://192.168.4.191:8000/docs` |
| ReDoc | `http://192.168.4.191:8000/redoc` |
| OpenAPI schema | `http://192.168.4.191:8000/openapi.json` |
| Health | `http://192.168.4.191:8000/health` |
| Latest status | `http://192.168.4.191:8000/api/v1/status` |
| History | `http://192.168.4.191:8000/api/v1/history?limit=120` |

Swagger, ReDoc, and OpenAPI each returned HTTP 200. The endpoint table, request methods, history limit, startup `503` behavior, and curl examples were added to `raspberry-pi/README.md` and synchronized to the Pi.

### 10. Gemma 3 feasibility and benchmark preparation

The only practical Gemma candidate for this 1 GB-class Pi is Gemma 3 270M Instruct with a small Q4 GGUF quantization, short context, short responses, and one request at a time. Gemma 3 1B and Gemma 3n were rejected for this hardware because their model and runtime memory requirements leave insufficient headroom for the OS and ASTRA.

Prepared an isolated workspace:

```text
/home/pi/llm-benchmark
```

Downloaded and configured `llama.cpp`:

- Git revision: `61dbf49228c8a96b72e40c89d93cb7c003411f8c`
- CMake recognized `armv7l` and the Cortex-A53's ARMv8 instruction capability.
- OpenMP support was detected.
- The generated text-completion target is `llama-completion`.
- A first attempt to build the older `llama-cli` target exited immediately because that target no longer exists in this revision; no files were damaged.

The intended safe benchmark configuration is:

- Model: Gemma 3 270M Instruct
- Quantization: Q4 GGUF, approximately 250 MB
- Context: 256 and 512 tokens
- Output: 32 and 64 tokens
- Concurrency: one request
- Build priority: low (`nice`)
- Runtime priority: low, with a deterministic ASTRA explanation fallback

No Gemma model file was downloaded.

### 11. Power-delivery blocker

The Pi initially reported:

```text
vcgencmd get_throttled -> 0xd0000
```

This indicated historical undervoltage/throttling events but no active warning in the low status bits.

During a two-worker low-priority compile:

- Temperature: approximately 56.9°C
- Status: `0xd0005`
- Interpretation: active undervoltage and active throttling
- ASTRA health: still `ok`

The two-worker build was stopped. After the warning cleared, compilation resumed with one low-priority worker. A single worker also produced `0xd0005`, so the build was stopped again to avoid instability or filesystem corruption.

After stopping:

- Temperature: approximately 53.7°C
- Status returned to historical-only `0xd0000`
- Available memory returned to approximately 589 MiB
- ASTRA remained healthy with fresh samples
- Partial build progress: approximately 3%
- Partial workspace size: approximately 231 MB

The unfinished build was intentionally preserved for an incremental resume.

### 12. End-of-day state

- API documentation was completed locally and synchronized to the Pi.
- The last verified ASTRA state was healthy in simulated mode.
- The Gemma model was not installed or downloaded.
- The `llama.cpp` build is paused and preserved.
- The final SSH connection closed from the remote side before a last snapshot could be captured. The Pi's final power state was not rechecked, in keeping with the decision to stop work until tomorrow.

## Tomorrow's resume checklist

### A. Correct power delivery

1. Connect a known-good Raspberry Pi power supply and a short, high-quality micro-USB cable.
2. Cold-boot the Pi.
3. Reconnect:

   ```sh
   ssh pi@192.168.4.191
   ```

4. Confirm a clean power state:

   ```sh
   vcgencmd measure_temp
   vcgencmd get_throttled
   ```

   Ideal after a cold boot:

   ```text
   throttled=0x0
   ```

### B. Restore or verify ASTRA

Because ASTRA is not yet a `systemd` service, check whether it is running:

```sh
curl -fsS http://127.0.0.1:8000/health
```

If it is not running:

```sh
cd /home/pi/Documents/NASA-SpaceApps-2026/raspberry-pi
mkdir -p data
nohup bash -c 'set -a; source .env; set +a; exec .venv/bin/uvicorn app.main:app --host "${ASTRA_HOST:-0.0.0.0}" --port "${ASTRA_PORT:-8000}"' > data/astra.log 2>&1 < /dev/null &
echo "$!" > data/astra.pid
```

Then verify `/health`, `/api/v1/status`, `/dashboard`, and `/docs` from another computer.

### C. Resume the incremental LLM build

Use one low-priority worker:

```sh
cd /home/pi/llm-benchmark/llama.cpp
nice -n 15 cmake --build build --target llama-completion -- -j1
```

Monitor power and temperature from a second SSH session:

```sh
watch -n 2 'vcgencmd measure_temp; vcgencmd get_throttled; free -h'
```

Stop immediately if the low status bits become non-zero under load.

### D. Download and benchmark only after a stable build

1. Select a reputable Gemma 3 270M Instruct Q4 GGUF artifact and record its source revision.
2. Download it to `/home/pi/llm-benchmark/models/`.
3. Record its SHA-256 digest.
4. Run short 256- and 512-token-context benchmarks at low priority.
5. Record model-load time, prompt-processing speed, generation speed, peak RSS, swap use, temperature, throttling state, and ASTRA sample freshness.
6. Decide whether to integrate, keep as an optional demo, or retain the current deterministic local explanation.

## Graceful shutdown

When finished:

```sh
sudo shutdown -h now
```

Wait until the green activity LED stops flashing before removing power.

## Related documentation

- `README.md`: mission, architecture, ownership, timeline, and definition of done.
- `RASPBERRY_PI_SSH.md`: SSH, Python, deployment, service management, and benchmark resume commands.
- `raspberry-pi/README.md`: backend setup, API reference, Sense HAT mode, tests, and restart behavior.
- `central-station/README.md`: dashboard usage and same-origin requirements.
- `wearable/README.md`: CYD configuration, build, upload, and expected states.

---

## Follow-up session — 2026-11-14

### Current milestone summary

| Milestone | Status | Evidence |
| --- | --- | --- |
| Reconnect on a different network | Complete | SSH succeeded at `pi@10.0.201.67`; the old address remains historical documentation. |
| Finish `llama.cpp` | Complete | `llama-completion` built as a 32-bit ARM executable after adding the GCC 8 link libraries. |
| Install and test Gemma 3 | Complete as an experiment | A 241 MiB Gemma 3 270M Q4_K_M model was checksummed and produced a valid on-device response. |
| Read the physical Sense HAT | Complete | Environment, accelerometer, gyroscope, magnetometer, and fused orientation all returned live values. |
| Feed all continuous sensors to FastAPI | Complete | Live `/api/v1/status` and SQLite history include all sensor groups with explicit units and nullable failure behavior. |
| Display the IMU in Mission Control | Complete | The Pi-hosted dashboard now renders live acceleration, gyroscope, magnetic-field, and orientation cards. |
| Validate backend changes | Complete | All 12 tests passed on the Pi with Python 3.11.18. |
| Validate live API and documentation | Complete | `/health`, status, history, Swagger, and OpenAPI returned HTTP 200 in live Sense HAT mode. |
| Write a teammate Swagger guide | Complete | `team/SWAGGER_API_GUIDE.md` contains browser, curl, JavaScript, Python, IP discovery, and troubleshooting steps. |

### Reconnection and system state

- New network address: `10.0.201.67`
- Board identity reconfirmed: Raspberry Pi 3 Model B Plus Rev 1.3
- Architecture: 32-bit `armv7l`
- RAM visible to Linux: approximately 744 MiB
- Root storage: approximately 18 GB free before the new model download
- ASTRA was not running after the reboot; the prior PID file was stale.
- Undervoltage/throttling flags remained present under load. The experiment
  continued at the user's direction, without disabling Raspberry Pi firmware
  protections.

### `llama.cpp` and Gemma completion

The source revision remained:

```text
61dbf49228c8a96b72e40c89d93cb7c003411f8c
```

The build reached 98% before GCC 8 failed to link symbols from
`std::filesystem` and 64-bit atomics on the 32-bit toolchain. CMake was
reconfigured with:

```text
-DCMAKE_CXX_STANDARD_LIBRARIES=-lstdc++fs -latomic
```

The incremental rebuild then completed successfully. The executable is:

```text
/home/pi/llm-benchmark/llama.cpp/build/bin/llama-completion
```

Model artifact:

```text
/home/pi/llm-benchmark/models/gemma-3-270m-it-Q4_K_M.gguf
```

- Exact size: 253,114,880 bytes
- Displayed size: approximately 241 MiB
- SHA-256: `57bbce8f2095939bde118bafbb65279c6e36ee8bcb09ee258f7f5d6a7b8e7f39`
- First response: a valid one-sentence interpretation of an ASTRA environment
  prompt
- First interactive wall time: approximately 79 seconds, including cold model
  load, prompt work, generation, and interactive CLI overhead

A final non-interactive 16-token benchmark produced clean performance metrics:

```text
model load: 7.12 seconds
prompt processing: 1.42 tokens/second
generation: 0.63 tokens/second
internal total: 32.95 seconds
shell wall time: 48.46 seconds
```

ASTRA stayed healthy in live Sense HAT mode during and after that load, with a
fresh sample, zero consecutive failures, approximately 607 MiB available RAM,
27 MiB swap in use, and a Pi temperature near 48.9 C.

This proves local inference is possible, but it is too slow for the primary
alert path on this Pi. ASTRA continues to use its deterministic offline summary.
The model remains available for optional experiments.

### Sense HAT hardware verification

I2C devices appeared at the expected bus addresses, including the environmental
and IMU components. Repeated reads returned plausible live values for:

- temperature in degrees Celsius;
- relative humidity in percent;
- barometric pressure in hectopascals;
- acceleration on x/y/z in g;
- angular velocity on x/y/z in radians per second;
- magnetic field on x/y/z in microteslas;
- fused pitch, roll, and yaw in degrees.

The first pressure read briefly returned `0`; later reads stabilized near
`982.6 hPa`. The adapter now rejects invalid pressure values and returns `null`
instead of publishing a believable zero. The driver reported that the optional
TCS34725 color sensor is not present on this board. The joystick is an event
input and the LED matrix is an output, so neither is periodic telemetry.

### Python runtime compatibility and sensor bridge

The Buster system Sense HAT package works under `/usr/bin/python3` (Python
3.7.3). A current Python 3.11 NumPy wheel from piwheels required a newer glibc
than Buster provides. Rather than replace the OS or system interpreter, ASTRA
now uses a persistent local JSON-lines bridge:

```text
FastAPI / Python 3.11 -> local pipe -> Sense HAT driver / system Python 3.7
```

The bridge stays entirely on the Pi and is selected with:

```text
ASTRA_SENSOR_MODE=sense-hat
ASTRA_SENSE_HAT_PYTHON=/usr/bin/python3
```

### API and persistence changes

The original environmental fields remain unchanged for CYD compatibility. The
following nested fields were added:

```json
{
  "acceleration_g": {"x": 0.0, "y": 0.82, "z": -0.62},
  "gyroscope_rps": {"x": 0.01, "y": 0.0, "z": 0.0},
  "magnetic_uT": {"x": -1.4, "y": 47.2, "z": -40.9},
  "orientation_deg": {"pitch": 359.5, "roll": 127.7, "yaw": 248.1}
}
```

SQLite initialization performs a backward-compatible migration that adds 12
motion/orientation scalar columns to an existing database. Tests cover live
normalization and database round trips. The simulated adapter also emits the
same complete schema so frontend work does not require the HAT.

### Live deployment validation

ASTRA was restarted with the final synchronized code as PID `4711`. The final
verification showed:

```text
health status: ok
sensor mode: sense-hat
source: live
consecutive failures: 0
Swagger: HTTP 200
OpenAPI: HTTP 200
Pi temperature: approximately 48.3 C
power flags: 0x50005
```

Both `/api/v1/status` and `/api/v1/history?limit=1` returned all environmental,
motion, magnetic, and orientation fields. The API is currently reachable at:

```text
http://10.0.201.67:8000/docs
```

### New and updated documentation

- `team/SWAGGER_API_GUIDE.md`: teammate-facing Swagger and API runbook.
- `raspberry-pi/README.md`: complete sensor contract, units, bridge setup, and
  current address.
- `RASPBERRY_PI_SSH.md`: current connection, live service start command,
  successful Gemma build, checksum, and benchmark result.
- `README.md`: complete API example and link to the Swagger guide.
- `MILESTONES.md`: this follow-up activity record.

### Central-station IMU integration

After the live API was stable, the central-station dashboard was extended with
a responsive Sense HAT IMU panel. It shows:

- acceleration x/y/z in g;
- gyroscope x/y/z in radians per second;
- magnetic field x/y/z in microteslas;
- pitch, roll, and yaw in degrees.

The panel changes between `LIVE`, `UNAVAILABLE`, and `STALE` without inventing
missing values. Sensor-link detection now examines nested sensor objects rather
than only the three environmental scalars. The existing environmental cards,
trend chart, telemetry table, and CYD-facing API fields remain unchanged.

Validation results:

```text
JavaScript syntax: valid
HTML static IDs referenced by JavaScript: all present
Pi-hosted dashboard IMU markup: present
Pi-hosted dashboard JavaScript: updated
Pi-hosted dashboard CSS: updated
API health during deployment: ok
live IMU groups present: 4/4
```

The in-product browser preview surface was unavailable for a screenshot-based
check, so verification used source validation plus the actual assets and live
API served by the Pi.

### API outage and automatic recovery service

At approximately 12:17 PST, the user reported that ASTRA was not responding.
SSH still accepted a new connection at `10.0.201.67`, but the old PID `4711`
no longer existed and nothing was listening on port `8000`. The previous log
ended without a Python traceback. Pi temperature, memory, swap, filesystem
space, I2C hardware, and the network address showed no resource failure.

The fragile `nohup` process was replaced with the versioned unit:

```text
raspberry-pi/systemd/astra.service
```

The service now:

- starts automatically at multi-user boot;
- runs as the unprivileged `pi` account;
- reads the existing private `.env` configuration;
- starts both FastAPI and its persistent system-Python Sense HAT bridge;
- waits for networking;
- restarts five seconds after an unexpected exit;
- records logs in the system journal.

Installation and recovery verification:

```text
systemd unit verification: passed
enabled at boot: yes
initial service state: active
initial API health: HTTP 200 / ok
forced old PID: 1137
automatic replacement PID: 1185
state after forced exit: active
health after restart: HTTP 200 / ok
dashboard after restart: HTTP 200
Swagger after restart: HTTP 200
laptop-to-Pi health check: HTTP 200
```

This closes the startup/recovery gap that caused the reported outage. Service
operations and journal commands are documented in `RASPBERRY_PI_SSH.md` and
`raspberry-pi/README.md`.

### Edge filtering, randomized biometrics, and mission tasks

The live Sense HAT adapter now samples acceleration and gyroscope readings near
20 Hz during each API interval. A deterministic edge-processing layer filters
noise, preserves motion features, handles circular orientation angles, and
attaches explicit data-quality metadata. This path runs locally and does not
depend on Gemma or internet access.

Live post-deployment observations:

```text
IMU sample count: 21 to 28 per API interval
expected sample count: 20
quality score: 1.0
quality flags: none
sensor source: live
```

The response contract was extended additively with `features`, `quality`,
`biometrics`, and `tasks`; all original environmental and IMU fields remain
unchanged. SQLite migration and history round trips cover the new objects.

Biometrics are bounded, smoothly varying randomized demonstration values for
heart rate, blood pressure, oxygen saturation, and body temperature. Every
record is marked `source: simulated` and `simulated_biometrics`; the values are
not measured by the Sense HAT and are not medical data.

Mission tasks are randomly selected from
`raspberry-pi/app/data/task_messages.txt`, a separate catalog containing exactly
200 messages across ten categories. A task has an ID, priority, category, text,
issue time, and simulated source. The default rotation interval is 15 seconds.
Live verification observed a change from `TASK-082` to `TASK-154` while the
sensor and quality fields continued updating.

Final validation:

```text
Pi unit tests: 22 passed
systemd service: active
health endpoint: ok
live data quality: 1.0
history biometric round trip: passed
history task round trip: passed
existing sensor keys retained: 7/7
```

### Central Station crew messaging

ASTRA version `0.3.0` adds a persistent Central Station-to-wearable message
handoff. The dashboard now provides an astronaut selector, priority selector,
240-character composer, send feedback, and recent outbox. It labels every
message `QUEUED` until the addressed wearable acknowledges receipt, then shows
`DELIVERED`.

The Pi exposes these additive routes:

```text
GET  /api/v1/crew
POST /api/v1/messages
GET  /api/v1/messages
POST /api/v1/messages/{message_id}/ack
```

Messages are stored in the existing SQLite database. Inbox queries are isolated
by astronaut ID, pending messages survive a disconnected wearable, and an
acknowledgement must contain the matching recipient ID. The initial roster is
`astronaut-1` through `astronaut-4`.

Wearable firmware now has an `ASTRA_ASTRONAUT_ID` setting. It polls only that
astronaut's pending inbox, displays a received message full-screen for ten
seconds, acknowledges it, and returns to the normal sensor/status screen.

Validation evidence:

```text
backend tests on development computer: 27 passed
backend tests on Raspberry Pi: 27 passed
dashboard JavaScript syntax: valid
dashboard JavaScript/HTML IDs: all matched
ESP32 firmware build: passed
ESP32 RAM: 47,272 bytes / 327,680 bytes (14.4%)
ESP32 flash: 963,777 bytes / 1,310,720 bytes (73.5%)
live Pi service version: 0.3.0
live message #1: queued -> pending inbox -> delivered
dashboard, JavaScript, CSS, and Swagger from laptop: HTTP 200
```

No CYD serial device was attached during this implementation session, so the
compiled firmware was not flashed to physical hardware. The Pi, API, database,
dashboard, and firmware source are ready; physical display/acknowledgement
validation is the remaining hardware step.

### Five-minute mission-task batches

The simulated task generator was adjusted from one task every 15 seconds to a
random batch of one to three unique tasks every five minutes. The API contract
remains additive and unchanged: consumers still receive a `tasks` array. The
batch is stable during the full five-minute window, including in SQLite
history, and every task remains explicitly marked `source: simulated`.

Central Station now renders every task in the batch, up to three responsive
cards, and uses the highest task priority for the section accent. The task
catalog remains the same separate 200-message text file.

### Local Gemma chat API

ASTRA version `0.4.0` adds `POST /api/v1/chat` for clients that need a short
single-turn response from the Gemma 3 270M model installed on the Pi. The
endpoint launches the existing `llama-completion` binary without a shell,
passes the prompt through the model's chat template, and returns only cleaned
answer text plus model, timestamp, latency, and local-execution metadata.

The chat path is isolated from sensor processing with a worker thread and a
single-generation lock. Input is limited to 400 characters, output to 32
tokens, and execution to 120 seconds. Concurrent callers receive HTTP `429`;
missing runtime artifacts return `503`; timeouts return `504`. Sensor alerts
remain deterministic and do not depend on Gemma.

Initial command validation produced `READY` from a four-token prompt. The run
took approximately 29 seconds end-to-end on the Raspberry Pi 3, confirming that
chat is feasible but intentionally slow.

Live FastAPI validation after deployment:

```text
service version: 0.4.0
POST /api/v1/chat: HTTP 200
reply: READY
reported endpoint latency: 51.081 seconds
simultaneous second request: HTTP 429
health checks during generation: 5/5 ok
sensor sample age during generation: approximately 0.2 to 1.0 seconds
sensor failures during generation: 0
backend tests on Raspberry Pi: 33 passed
laptop-to-Pi chat request: HTTP 200 / OK in 49.749 seconds
```

### NASA-aligned suit telemetry thresholds

ASTRA version `0.5.0` separates suit telemetry from the Sense HAT's real
ambient readings. The original `sensors.temperature_c` and
`sensors.pressure_hpa` fields remain intact. Two additive, persisted objects
now expose explicitly simulated suit pressure and suit-air temperature with
machine-readable thresholds, status, source, and limitation flags.

The pressure demo uses nominal `296 hPa`, warning bounds `276/365 hPa`, and
critical bounds `248/455 hPa`. Suit-air temperature uses a `20–30 °C` comfort
band, critical-low below `10 °C`, and critical-high above `43 °C`. Documentation
states that these are prototype interpretations: the high/low temperature
limits are adapted from internal touch-temperature requirements and are not a
certified suit-air alarm scheme.

Simulated biometrics now attach heart-rate status and publish warning and
critical thresholds of `120` and `140 bpm`. The existing randomized heart-rate,
blood-pressure, oxygen-saturation, and body-temperature values and all
pre-existing API fields remain compatible.

Deployment validation:

```text
backend tests on development computer: 39 passed
backend tests on Raspberry Pi: 39 passed
live Pi service version: 0.5.0
live service state: active / health ok
live Sense HAT ambient pressure: approximately 982 hPa
simulated suit pressure: approximately 294–295 hPa / NOMINAL
simulated suit-air temperature: approximately 24 °C / COMFORT
history round trip: NOMINAL / COMFORT / heart rate NOMINAL
OpenAPI StatusResponse: suit_pressure and suit_temperature present
laptop-to-Pi status request: HTTP 200
Pi-hosted dashboard and wearable UI: intentionally unchanged
```

The copy-ready integration brief for the separately maintained site is stored
in `team/EXTERNAL_SITE_SUIT_TELEMETRY_PROMPT.md`. It requires a server-side
proxy when necessary to avoid browser CORS and HTTPS mixed-content failures,
keeps the Pi on the trusted private LAN, and prevents ambient Sense HAT values
from being mislabeled as suit telemetry.

### Demo-hardened local Gemma chat

ASTRA version `0.6.0` hardens `POST /api/v1/chat` without changing its request
body or coupling it to sensor decisions. The server now treats user prompts and
model output as untrusted. Deterministic preflight rules intercept prompt
injection, credential extraction, hazardous-operation instructions, and
medical/emergency direction before Gemma is launched. Control characters and
chat-template delimiters cannot silently alter the conversation structure.

Normal questions still run through Gemma with the existing single-generation
lock, timeout, fixed seed, and token cap. Additional resource limits cap actual
temperature at `0.4`, bound context to 1024 tokens, and close process standard
input. Output has ANSI/control text and role prefixes removed, whitespace and
length normalized, and unsafe or empty output replaced with deterministic safe
fallback text. Responses add `response_type` (`model`, `guardrail`, or
`fallback`) and a prototype safety notice.

`GET /api/v1/chat/health` provides a non-sensitive demo readiness check. It
reports `ready`, `busy`, or `unavailable` plus model name and configured limits,
but does not load Gemma or expose runtime paths, prompts, credentials, or
environment variables.

Validation evidence:

```text
backend tests on development computer: 45 passed
backend tests on Raspberry Pi: 45 passed
live Pi service version: 0.6.0
live service state: active / sensor health ok
chat readiness from Pi and laptop: ready / guardrails 1.0
prompt-injection request: deterministic guardrail in 0.0 seconds
hazardous oxygen-alarm request: deterministic guardrail in 0.0 seconds
ordinary airlock-seal question: validated Gemma response / HTTP 200
real Gemma response type: model
real Gemma latency on Pi 3: 84.735 seconds
chat readiness during inference: busy
sensor health during inference: 5/5 ok
sensor sample age during inference: 0.156 to 1.979 seconds
chat readiness after inference: ready
```

Known boundary: chat remains unauthenticated and therefore stays restricted to
the trusted private LAN. It is explanatory only; deterministic sensor status,
approved procedures, and mission control remain authoritative.

