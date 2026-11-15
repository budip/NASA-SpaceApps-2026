---
name: astra-development
description: Build, debug, review, or document ASTRA's Raspberry Pi backend, Sense HAT data path, CYD wrist firmware, offline anomaly behavior, and demo workflow. Use for repository tasks that must preserve ASTRA's frozen interfaces, offline-first behavior, truthful data provenance, or hardware safety boundaries.
---

# ASTRA Development

Use this skill to turn an ASTRA request into a small, verifiable contribution to
the end-to-end astronaut safety prototype.

## Establish Context

Before acting:

1. Read the repository `README.md` for the current scope, API contract,
   checkpoints, and definition of done.
2. Read `AI/AGENTS.md` and obey its offline, interface, evidence, security, and
   hardware-safety constraints.
3. Read only the relevant owner guide:
   - `team/BUDI.md` for backend, database, analysis, configuration, release, or
     integration work;
   - `team/RALPH.md` for CYD firmware, networking, display, or recovery work;
   - `team/TYEKI.md` for Sense HAT, sensor adapters, power, mounting, or anomaly
     trigger work;
   - `team/ALEX.md` for wording, testing, evidence, demo, or presentation work.

Inspect the current implementation and tests before proposing a new structure.
If repository files disagree with a planning document, surface the mismatch and
preserve the last known working interface unless the user asks to change it.

## Select the Work Slice

Map the task to the earliest incomplete priority level:

1. sensor to API to CYD;
2. offline history, baseline, state, and local explanation;
3. wearable reliability and a safe repeatable trigger;
4. optional OpenAI explanation or visual refinement.

Choose the smallest observable result that advances that level. Do not add a
stretch feature while a required path is failing.

## Implement Around the Contract

Preserve the status payload and state meanings in `README.md`. Treat missing
sensor values, stale data, malformed input, stopped services, and unavailable
internet as expected operating conditions. A communication failure must produce
`OFFLINE`, never an inferred safe state.

Keep live, replayed, and simulated sources compatible at the software boundary
and label their provenance. Keep OpenAI optional, backend-only, time-bounded,
and protected by deterministic local output. Never place credentials in code,
firmware, logs, sample data, or demo assets.

For anomaly work, favor understandable statistics and stable state transitions.
Make learning requirements, thresholds, hysteresis or consecutive-sample rules,
and reset behavior explicit. Do not make medical, flight-certification, or
life-safety claims.

## Verify the Result

Run focused tests for the changed unit, then verify the affected interface.
Select failure cases based on the component:

- Backend: missing readings, invalid data, database restart, no internet, and
  OpenAI timeout or invalid output.
- CYD: missing fields, malformed JSON, slow or stopped API, stale timestamps,
  reconnect, and power-on recovery.
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
