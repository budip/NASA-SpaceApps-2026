---
name: astra-development
description: Build, debug, review, or document the ASTRA offline-first prototype across its Raspberry Pi backend, Sense HAT path, CYD wearable, Central Station, messaging, and local Gemma endpoint. Use when repository work must preserve ASTRA's frozen core contract, truthful provenance, recovery behavior, or hardware safety boundaries.
---

# ASTRA Development

Use this skill to turn an ASTRA request into a small, verifiable contribution to
the end-to-end astronaut safety prototype.

## Establish Context

Before acting:

1. Read the repository `README.md` for the current scope, API contract,
   checkpoints, and definition of done.
2. Read `ai/AGENTS.md` and obey its offline, interface, evidence, security, and
   hardware-safety constraints.
3. Read only the relevant owner guide:
   - `team/BUDI.md` for backend, database, analysis, configuration, release, or
     integration work;
   - `team/RAPH.md` for CYD firmware, networking, display, or recovery work;
   - `team/TYEKI.md` for Sense HAT, sensor adapters, power, mounting, or anomaly
     trigger work;
   - `team/ALEX.md` for wording, testing, evidence, demo, or presentation work.

Read `team/SWAGGER_API_GUIDE.md` when changing an endpoint, payload, Central
Station integration, suit or biometric field, task, message flow, or local chat
behavior. Read the affected component README before changing its run or build
path.

Inspect the current implementation and tests before proposing a new structure.
If repository files disagree with a planning document, surface the mismatch and
preserve the last known working interface unless the user asks to change it.
Check `raspberry-pi/app/__init__.py` rather than assuming the current service
version.

## Understand the Current Surface

The minimum `/api/v1/status` fields remain frozen, while the current service
adds history and quality data, explicitly simulated suit telemetry and
biometrics, simulated mission tasks, a durable Central Station-to-wearable
message queue, and a bounded local Gemma chat endpoint. These additions must
not weaken the minimum sensor-to-alert path.

Central Station source lives in `central-station/` and is served by the Pi.
Messaging stays on the trusted private LAN and moves from queued to delivered
only after the addressed wearable acknowledges it. Gemma runs locally on the
Pi; it is experimental, single-turn, and never a source of alert decisions.

## Select the Work Slice

Map the task to the earliest incomplete priority level:

1. sensor to API to CYD;
2. API to Central Station plus offline history, baseline, state, and local
   explanation;
3. wearable reliability, queued messaging, and a safe repeatable trigger;
4. optional local Gemma chat or visual refinement.

Choose the smallest observable result that advances that level. Do not add a
stretch feature while a required path is failing.

## Implement Around the Contract

Preserve the minimum status payload and state meanings in `README.md`. Additive
fields and endpoints must remain compatible with the current schema in
`team/SWAGGER_API_GUIDE.md`. Treat missing sensor values, stale data, malformed
input, stopped services, and unavailable internet as expected operating
conditions. A communication failure must produce `OFFLINE`, never an inferred
safe state.

Keep live, replayed, and simulated sources compatible at the software boundary
and label provenance at the level where data originates. Ambient Sense HAT
readings do not make simulated suit, biometric, or task data live. Keep local
Gemma optional, bounded, guarded, output-validated, and isolated from sensor
sampling. Any future cloud AI path stays backend-only, time-bounded, and
protected by deterministic local output. Never place credentials in code,
firmware, logs, sample data, or demo assets.

Preserve recipient filtering, acknowledgement, persistence, and truthful
delivery state in the message queue. Do not imply authentication exists, and do
not expose the service directly to the internet.

For anomaly work, favor understandable statistics and stable state transitions.
Make learning requirements, thresholds, hysteresis or consecutive-sample rules,
and reset behavior explicit. Do not make medical, flight-certification, or
life-safety claims.

## Verify the Result

Run focused tests for the changed unit, then verify the affected interface.
Select failure cases based on the component:

- Backend: missing readings, invalid data, database restart, no internet, and
  persistence or sampling failure.
- CYD: missing fields, malformed JSON, slow or stopped API, stale timestamps,
  reconnect, message filtering and acknowledgement, and power-on recovery.
- Central Station: current status and history, simulated labels, messaging
  queue state, service degradation, and browser recovery.
- Local chat: health readiness, disabled model, rejected input, invalid model
  output, timeout, concurrent request, and continued sensor responsiveness.
- Sensors and hardware: warm-up, units, sampling stability, read failure,
  thermal or power warnings, mounting, and safe trigger repeatability.
- Experience and demo: all five states, live versus simulated labeling,
  readable wording, exact reproduction steps, and timed rehearsal.

Use simulations for development when hardware is unavailable, but state that
limitation clearly. Do not report a test as passing without observable evidence.

## Hand Off

Conclude with:

1. what now works;
2. exact run, build, or connection steps;
3. the files, endpoint, device behavior, or artifact delivered;
4. known limits and assumptions;
5. proof from tests, logs, screenshots, or a short demonstration.

Call out any API or display impact and name the teammates who need the handoff.
