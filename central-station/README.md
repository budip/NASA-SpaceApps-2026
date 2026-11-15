# ASTRA Central Station

This folder contains the laptop monitoring interface as a standalone,
buildless web client:

- `index.html` defines the accessible dashboard structure;
- `dashboard.css` provides the responsive mission-control visual system;
- `dashboard.js` polls the Pi status, health, and bounded history endpoints.

The live display includes environmental values plus acceleration, gyroscope,
magnetic-field, and fused pitch/roll/yaw readings from the Sense HAT. It also
shows derived IMU quality, clearly labeled randomized biometrics, and the
current batch of one to three simulated mission tasks selected from the
200-message catalog. A new batch is selected every five minutes. The crew
communications panel queues a 1–240 character message for a selected astronaut
and shows whether that wearable has acknowledged delivery.

Messages are not browser-only state. The Pi stores them in SQLite, and the
dashboard refreshes its outbox from `/api/v1/messages`. It obtains recipient
IDs from `/api/v1/crew`, so the form and API use the same roster.

The browser UI and Raspberry Pi backend are intentionally separate code areas.
The Pi still serves these static files so the central station works without
internet access or a laptop-side installation.

## Run

Start the service from `raspberry-pi/`:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Then open the following URL from a laptop on the same private LAN:

```text
http://PI_ADDRESS:8000/dashboard
```

Do not open `index.html` directly from the filesystem. The dashboard uses
same-origin requests to `/health`, `/api/v1/status`, and `/api/v1/history`, so it
must be served by the Pi application or another compatible local HTTP server.

No credentials, Wi-Fi values, or API keys belong in this folder.
