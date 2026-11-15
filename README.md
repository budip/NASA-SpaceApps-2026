# ASTRA Team Onboarding

ASTRA is an offline-first astronaut safety prototype for NASA Space Apps 2026. It combines a wrist terminal built from a CYD (Cheap Yellow Display) with a Raspberry Pi 3 and Sense HAT backpack computer. The backpack collects and stores sensor readings, learns a local baseline, detects unusual conditions, and serves results over a local network. The wrist terminal shows the current condition and alerts. An optional OpenAI feature may turn technical readings into plain-language explanations when internet access and credentials are available.

This README is the team's shared plan. The individual guides explain each person's work:

- [Budi — Technical Lead and System Integrator](team/BUDI.md)
- [Alex — Experience Designer, Tester, and Demo Guide](team/ALEX.md)
- [Raph — CYD Wrist Terminal Developer](team/RALPH.md)
- [Tyeki — Backpack Hardware and Sensor Lead](team/TYEKI.md)
- [Milestones and activity log](MILESTONES.md)
- [Raspberry Pi connection and deployment notes](RASPBERRY_PI_SSH.md)
- [Teammate Swagger/API guide](team/SWAGGER_API_GUIDE.md)

## The mission

The weekend goal is a reliable end-to-end demonstration:

1. The Sense HAT measures the backpack environment and motion.
2. The Raspberry Pi records readings in SQLite.
3. The local Python/FastAPI service computes a baseline and flags anomalies.
4. The CYD wrist terminal requests a compact status from the Pi and displays `NORMAL`, `CAUTION`, `ALERT`, or `OFFLINE`.
5. A laptop on the private network opens the Pi-hosted central-station dashboard for trends and diagnostics.
6. The system continues to collect, analyze, store, display, and explain basic alerts without internet access.

The success story is: **ASTRA notices a change, warns the crew member, explains what changed, and keeps working when the internet disappears.**

## Scope and priorities

Build in this order. Do not start a later level until the current one works.

| Level | Required behavior | Decision gate |
| --- | --- | --- |
| 1. Core | Pi reads Sense HAT data; API returns sample data; CYD displays it | Must work before integration checkpoint |
| 2. Offline intelligence | SQLite history, local baseline, anomaly flag, local fallback explanation | Required for the final demo |
| 3. Wearable demo | Stable enclosure/mount, clear screen, repeatable anomaly trigger | Required if hardware permits |
| 4. Stretch | OpenAI explanation, richer charts, extra sensors, refined enclosure | Only after the full offline demo passes twice |

OpenAI is an enhancement, not a dependency. Never put an API key in firmware, source control, screenshots, or a presentation. The backend alone may call OpenAI, and it must fall back to a local explanation if the call fails.

## System ownership and interfaces

| Area | Owner | Output consumed by | Interface or handoff |
| --- | --- | --- | --- |
| System architecture, backend, database, integration | Budi | Everyone | API contract, setup commands, integrated build |
| CYD firmware and wrist display | Ralph | Alex and Budi | CYD build plus connection notes |
| Pi, Sense HAT, power, mounting, anomaly trigger | Tyeki | Budi and Alex | Stable sensor stream plus hardware runbook |
| Screen wording, test passes, demo script, evidence | Alex | Ralph, Budi, and presenter | Approved labels, issue list, final demo steps |

The stable minimum API contract is:

```json
{
  "timestamp": "2026-11-13T18:30:00Z",
  "status": "NORMAL",
  "score": 0.18,
  "summary": "Conditions are within the learned baseline.",
  "sensors": {
    "temperature_c": 22.4,
    "humidity_pct": 41.0,
    "pressure_hpa": 1012.7,
    "acceleration_g": {"x": 0.01, "y": 0.02, "z": 1.0},
    "gyroscope_rps": {"x": 0.01, "y": 0.0, "z": -0.01},
    "magnetic_uT": {"x": 12.1, "y": -4.2, "z": 31.8},
    "orientation_deg": {"pitch": 2.0, "roll": 1.0, "yaw": 180.0}
  },
  "source": "live"
}
```

Rules for this interface:

- `status` is one of `LEARNING`, `NORMAL`, `CAUTION`, `ALERT`, or `OFFLINE`.
- Missing sensor values are allowed and must not crash either device.
- `summary` always has a local fallback; it cannot depend on OpenAI.
- `source` is `live`, `cached`, or `simulated`, so the demo never mislabels sample data as live data.
- Budi owns changes to field names. Ralph and Alex review any display-impacting change.

The current service extends this minimum contract without renaming or removing
any of its fields. It adds filtered motion `features`, data `quality`, explicitly
simulated `biometrics`, and a `tasks` array selected from a separate 200-message
catalog. The biometric demo values are randomized and are not real medical
measurements. See the [Swagger/API guide](team/SWAGGER_API_GUIDE.md) for the
complete current schema and examples.

Version `0.5.0` also adds explicitly simulated `suit_pressure` and
`suit_temperature` objects. These do not replace `sensors.pressure_hpa` or
`sensors.temperature_c`: the Sense HAT fields remain ambient backpack
measurements. The suit objects carry their own source, thresholds, status, and
prototype-limit flags. Simulated heart rate also includes a deterministic
status with a 140 bpm critical-high threshold.

Central Station can also queue a message for an individual astronaut. The Pi
stores it until that astronaut's configured wearable polls and acknowledges it;
the dashboard reports `QUEUED` or `DELIVERED`. Messaging stays on the private
LAN and is documented in the same Swagger guide.

Clients may optionally call `POST /api/v1/chat` for a short, single-turn reply
from Gemma 3 running entirely on the Pi. The endpoint is deliberately bounded
and asynchronous; it never replaces deterministic sensing or alert logic.
Version `0.6.0` adds deterministic prompt guardrails, output validation, safe
fallback text, a server-side temperature cap, a bounded context, and
`GET /api/v1/chat/health` for demo readiness checks.

## Hackathon weekend timeline

Times are relative to the official build start so the plan survives schedule changes. Budi records the actual clock time beside each checkpoint at kickoff. Every checkpoint ends with a short show-and-tell on the shared table.

| Time | Shared milestone | Required evidence | Handoff |
| --- | --- | --- | --- |
| T+0 to T+1 hour | Kickoff and freeze the minimum demo | Hardware inventory, roles confirmed, sample API response agreed | Budi gives Ralph the JSON example; Tyeki gives Budi a sensor-field list; Alex gives Ralph the first screen wording |
| T+1 to T+4 | Parallel bring-up | Pi reads Sense HAT; backend serves simulated status; CYD shows a fixed status; Alex has a test sheet and demo outline | Tyeki hands Budi a working sensor script; Budi gives Ralph a reachable API address or mock; Ralph gives Alex a screen to inspect |
| T+4 to T+7 | First integration | Live sensor values travel Pi → API → CYD; disconnect produces `OFFLINE` | Ralph and Tyeki hand integration notes to Budi; Alex logs failures with exact steps |
| T+7 to T+10 | Offline intelligence | SQLite stores readings; baseline reaches `NORMAL`; planned stimulus produces `CAUTION` or `ALERT` | Tyeki documents a safe anomaly trigger; Budi exposes status/summary; Ralph maps every state to the display |
| T+10 to T+12 | Checkpoint 1: minimum demo freeze | Full offline path passes twice from a clean start | Budi tags/freezes the known-good version; Alex takes screenshots/video and writes the exact demo sequence |
| T+12 to T+18 | Reliability and presentation | Power-cycle recovery, readable wearable, clear story, fallback demo data | Each owner fixes only high-value issues; all changes return to Budi for integration |
| T+18 to T+21 | Checkpoint 2: feature freeze | Three consecutive rehearsals; one with internet disabled | Alex owns the rehearsal checklist; Budi decides whether any failing stretch feature is removed |
| T+21 to submission | Submission buffer | Video, screenshots, architecture image, repository instructions, final pitch | Owners supply evidence to Alex; Budi performs final technical check; designated submitter uploads |

If the event is shorter, preserve the order and compress the time blocks. Reserve at least the final 20% of the event for rehearsal, packaging, and submission.

## Definition of done

The project is demo-ready when all of these are true:

- [ ] A new teammate can start the Pi and CYD from written instructions.
- [ ] The live Sense HAT reading appears on the wrist terminal.
- [ ] A laptop on the private LAN can open the dashboard and monitor current and recent readings.
- [ ] The Pi stores timestamped readings in SQLite.
- [ ] The system visibly distinguishes learning, normal, anomalous, and disconnected states.
- [ ] A safe, repeatable stimulus creates an anomaly during rehearsal.
- [ ] Turning off internet access does not stop sensing, storage, anomaly detection, or the basic explanation.
- [ ] Turning off the Pi makes the wrist terminal show `OFFLINE` instead of stale live data.
- [ ] The end-to-end demo succeeds three times in a row.
- [ ] The presentation says which data is live, cached, or simulated.
- [ ] The submission materials and source contain no credentials or private data.

## Team working agreement

- Keep the main path runnable. Integrate small changes early instead of joining four large pieces at the end.
- Report blockers within 15 minutes. Say what you tried, what happened, and what you need.
- At each checkpoint, demonstrate the result; a verbal “done” is not enough.
- Use short branches or clearly separated changes. Budi approves changes to shared interfaces.
- Log every test with time, build/version, expected result, actual result, and owner.
- Protect the demo freeze. After Checkpoint 1, fix reliability or presentation issues before adding features.
- Keep a simulated-data mode available as a clearly labeled backup for filming and troubleshooting.

## Shared handoff format

Every handoff should contain five things:

1. **What is ready:** one sentence describing the working result.
2. **How to run it:** exact start, build, or connection steps.
3. **What the receiver gets:** file, endpoint, device, drawing, or test result.
4. **Known limits:** failures, assumptions, and unfinished items.
5. **Proof:** a screen, log line, photo, or 30-second demonstration.

The receiver repeats the run steps before accepting the handoff. If the repeat fails, both owners stay on the interface until it works or Budi changes the scope.

## Starter projects

The repository includes two runnable starter projects:

- [`raspberry-pi/`](raspberry-pi/) contains the FastAPI service, simulated and
  Sense HAT sensor adapters, local baseline/anomaly logic, and SQLite storage.
- [`wearable/`](wearable/) contains PlatformIO firmware for an ESP32-2432S028R-style CYD
  that polls the Pi and displays the five ASTRA states.
- [`central-station/`](central-station/) contains the buildless laptop dashboard
  served by the Pi over the private local network.

Start the Pi service in simulated mode first, then point the CYD configuration
at the Pi's local IP address. Each project README contains exact setup and test
commands. Confirm the exact CYD revision and display pins before connecting the
hardware.
