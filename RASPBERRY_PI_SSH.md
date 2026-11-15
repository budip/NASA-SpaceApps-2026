# Raspberry Pi SSH Connection

## Connection details

- Current host: `10.0.201.67`
- Previous network address: `192.168.4.191`
- User: `pi`
- SSH port: `22` (default)
- Command: `ssh pi@10.0.201.67`

## Steps

1. Make sure the computer is connected to the same local network as the Raspberry Pi.
2. Open a terminal.
3. Run:

   ```sh
   ssh pi@10.0.201.67
   ```

4. If SSH asks whether to trust the host key, verify it is the intended Pi, then answer `yes`.
5. Enter the `pi` account password when prompted. The password is intentionally not stored in this file.
6. A successful connection shows a prompt similar to:

   ```text
   pi@raspberrypi:~ $
   ```

## Observed system details

- Hostname: `raspberrypi`
- OS: Raspbian GNU/Linux 10 (Buster), 32-bit `armhf`
- Kernel: `5.10.103-v7+`
- Architecture: `armv7l`

## ASTRA upload location

The project destination has been created and is owned by `pi`:

```text
/home/pi/Documents/NASA-SpaceApps-2026
```

The Pi has approximately 18 GB free on its root filesystem.

## Python runtime

Python 3.11.18 was installed alongside the operating system's Python:

```sh
python3.11 --version
pip3.11 --version
```

- Project interpreter: `/usr/local/bin/python3.11`
- Project pip: `/usr/local/bin/pip3.11`
- OS interpreter preserved at `/usr/bin/python3` (Python 3.7.3)
- Create the project virtual environment with `python3.11 -m venv .venv`.

Do not change `/usr/bin/python3` or repoint it to Python 3.11; Raspbian Buster system tools depend on its packaged Python 3.7 runtime.

The obsolete Buster package source was changed from `raspbian.raspberrypi.org` to `legacy.raspbian.org`. The previous source list is backed up at `/etc/apt/sources.list.pre-python311-backup`.

## ASTRA deployment

The repository is deployed to the upload location above. The FastAPI backend uses this virtual environment:

```text
/home/pi/Documents/NASA-SpaceApps-2026/raspberry-pi/.venv
```

The live Sense HAT service is available on the local network:

```text
Dashboard: http://10.0.201.67:8000/dashboard
Swagger:   http://10.0.201.67:8000/docs
ReDoc:     http://10.0.201.67:8000/redoc
OpenAPI:   http://10.0.201.67:8000/openapi.json
Health:    http://10.0.201.67:8000/health
Status:    http://10.0.201.67:8000/api/v1/status
History:   http://10.0.201.67:8000/api/v1/history?limit=120
```

All API routes use `GET`. The history `limit` defaults to `120` and accepts values from `1` through `300`. `/api/v1/status` may return HTTP `503` during startup before the first sensor sample is ready.

Runtime state:

- Service: `astra.service`
- Logs: the system journal for `astra.service`
- SQLite data: `raspberry-pi/data/astra.db`
- The old `data/astra.pid` and `data/astra.log` files are historical artifacts
  from the superseded `nohup` launch method.

Check the running service:

```sh
cd /home/pi/Documents/NASA-SpaceApps-2026/raspberry-pi
systemctl status astra.service --no-pager
journalctl -u astra.service -n 100 --no-pager
curl http://127.0.0.1:8000/health
```

Start, stop, or restart the service:

```sh
sudo systemctl start astra.service
sudo systemctl stop astra.service
sudo systemctl restart astra.service
```

The service is enabled at boot and automatically restarts after an unexpected
process exit. Its source unit is versioned at
`raspberry-pi/systemd/astra.service`.

The deployment test suite passed all 12 tests with Python 3.11.18. Live status
and SQLite history were then verified with temperature, humidity, pressure,
acceleration, gyroscope, magnetometer, and fused orientation values.

Raspbian Buster's packaged Sense HAT driver runs under `/usr/bin/python3`
(Python 3.7). The FastAPI adapter keeps a persistent local JSON-lines bridge to
that driver by setting:

```sh
ASTRA_SENSOR_MODE=sense-hat
ASTRA_SENSE_HAT_PYTHON=/usr/bin/python3
```

The bridge is entirely on the Pi. Sensor readings are not sent to the internet.

## Gemma 3 benchmark status

An isolated `llama.cpp` benchmark workspace was prepared at:

```text
/home/pi/llm-benchmark
```

- Source revision: `61dbf49228c8a96b72e40c89d93cb7c003411f8c`
- Target: `llama-completion`
- Model: Gemma 3 270M Instruct, Q4_K_M GGUF
- Model size: 253,114,880 bytes (about 241 MiB)
- Model SHA-256: `57bbce8f2095939bde118bafbb65279c6e36ee8bcb09ee258f7f5d6a7b8e7f39`
- Binary: `/home/pi/llm-benchmark/llama.cpp/build/bin/llama-completion`
- Build state: complete and successfully tested

The 32-bit Buster toolchain needed `-lstdc++fs -latomic` at link time. The
successful CMake configuration includes:

```sh
cd /home/pi/llm-benchmark/llama.cpp
cmake -S . -B build \
  -DCMAKE_BUILD_TYPE=Release \
  -DGGML_NATIVE=ON \
  -DGGML_OPENMP=ON \
  -DLLAMA_CURL=OFF \
  -DLLAMA_BUILD_TESTS=OFF \
  -DLLAMA_BUILD_SERVER=OFF \
  -DBUILD_SHARED_LIBS=OFF \
  -DCMAKE_CXX_STANDARD_LIBRARIES='-lstdc++fs -latomic'
cmake --build build --target llama-completion -- -j2
```

A first cold interactive inference produced a valid ASTRA sentence. A final
non-interactive 16-token run measured:

- model load: 7.12 seconds;
- prompt processing: 1.42 tokens/second;
- generation: 0.63 tokens/second;
- internal inference time: 32.95 seconds;
- end-to-end shell wall time: 48.46 seconds.

This confirms feasibility but is too slow for the primary alert path; the
deterministic local explanation remains the default. ASTRA remained healthy
with fresh live sensor samples during and after the benchmark.

ASTRA now exposes this model through `POST /api/v1/chat`. The service invokes
the binary on demand, permits one generation at a time, and keeps the model out
of persistent RAM between requests. Runtime paths, timeout, token limit, and
thread count are configured with the `ASTRA_LLM_*` variables documented in
`raspberry-pi/.env.example`.

Version `0.6.0` hardens the endpoint with deterministic input guardrails,
sanitized and validated output, safe fallback text, a 1024-token context,
closed process standard input, a server-side temperature cap, and a
non-sensitive readiness route:

```bash
curl http://127.0.0.1:8000/api/v1/chat/health
```

The readiness check does not load the model. It should report `ready` before a
demo. The chat remains unauthenticated and must stay on the trusted private LAN.

The Pi recorded active undervoltage/throttling (`0x50005`) during heavy work.
The user explicitly chose to finish the experiment, but a stable 5V/2.5A-or-
better supply and short cable are still recommended before relying on LLM
output or performing repeated load tests.

## Known startup warning

The shell currently reports a malformed `PATH` export after login:

```text
-bash: export: `PATH/home/pi/.local/bin:...': not a valid identifier
```

This does not prevent login, but a shell startup file such as `~/.bashrc` or `~/.profile` likely contains a missing `=` in a `PATH` assignment.

## Disconnect

Run `exit` or press `Ctrl-D`.
