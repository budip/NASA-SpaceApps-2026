# Budi — Technical Lead and System Integrator

## Role summary

You own ASTRA's technical direction and the working end-to-end build. Your primary implementation area is the Raspberry Pi software: Python, FastAPI, SQLite, local baseline/anomaly detection, optional OpenAI explanations, and system startup. You also protect the API contract, manage scope, resolve integration blockers, and decide which build becomes the demo build.

Your standard is not “every feature exists.” It is “the smallest credible mission story works repeatedly, offline, and can be operated by another teammate.”

## Responsibilities

- Define and protect the Pi-to-CYD API contract in the team README.
- Build the backend as small replaceable components: sensor input, storage, analysis, explanation, and API.
- Make real and simulated sensor sources use the same internal data shape.
- Keep SQLite writes and API responses safe under missing, delayed, or invalid readings.
- Implement an explainable local baseline and anomaly score appropriate for a weekend prototype.
- Ensure the OpenAI path is optional, server-side only, time-bounded, and backed by a local explanation.
- Provide one-command or clearly documented startup and a basic health check.
- Lead integration checkpoints, prioritize defects, freeze known-good builds, and protect submission time.
- Help less experienced teammates by reducing ambiguous tasks into small observable results.

## Concrete tasks

### Before or at kickoff

1. Confirm hardware, network method, repository layout, Python version, and device addresses.
2. Freeze the minimum API response shown in the README; create a simulated response immediately.
3. Define a single configuration source for ports, sensor mode, database path, and optional OpenAI use.
4. Create a visible task board with owners, checkpoints, blockers, and the current demo-build identifier.

### Backend and data path

1. Read normalized Sense HAT samples supplied through Tyeki's sensor adapter.
2. Store UTC timestamp, sensor values, status, score, and source in SQLite.
3. Expose at least:
   - `GET /health` for service health and version;
   - `GET /api/v1/status` for the compact CYD payload;
   - a local-only debug/history view if time allows.
4. Return a controlled response when a sensor is missing instead of throwing an unhandled error.
5. Add a simulated mode that produces normal and anomalous samples without changing the CYD contract.

### Baseline and anomaly logic

1. Use a transparent baseline such as rolling mean/median plus dispersion for temperature, humidity, and pressure.
2. Start in `LEARNING`; require a documented minimum sample count before calling data normal.
3. Combine per-sensor deviations into a bounded score and stable states. Add hysteresis or consecutive-sample rules so the display does not flicker.
4. Persist enough recent history that a service restart does not destroy the demo, while allowing a clearly documented “reset baseline” action.
5. Document the prototype limitation: the model finds deviations from recent local conditions and is not a medical or flight-certified safety system.

### Explanations and resilience

1. Generate a deterministic local summary from the strongest sensor deviation.
2. If OpenAI is enabled, send only the minimum numeric context, use a short timeout, validate the returned text, and fall back silently on failure.
3. Keep the API responsive if internet, OpenAI, or a nonessential component fails.
4. Verify startup after power loss and verify that the CYD reports `OFFLINE` when the service stops.

### Integration and release

1. Run the T+4, T+10, and T+18 checkpoint demonstrations from the README.
2. Record the known-good revision and configuration after each successful freeze.
3. Reject contract changes that do not materially improve the mission story after the first integration.
4. Give Alex the exact startup, reset, anomaly-trigger, recovery, and shutdown sequence for rehearsal.

## Start guide

1. Read the [team README](../README.md), especially scope levels, API contract, timeline, and definition of done.
2. Inventory the Pi, Sense HAT, CYD, chargers, batteries, cables, and available router/hotspot. Assign each physical item an owner.
3. Bring up a FastAPI service with `/health` and a simulated `/api/v1/status` before waiting for hardware.
4. Ask Ralph to consume the simulated response. This proves the network and contract early.
5. Ask Tyeki for a sensor adapter that returns one normalized sample at a time. Keep hardware-specific imports behind that adapter.
6. Replace the simulated source with the live adapter, then add SQLite storage.
7. Collect a stable baseline before tuning anomaly thresholds. Save a short normal dataset and at least one labeled stimulus run.
8. Add the local explanation and state stabilization. Treat optional OpenAI integration as the last backend feature.
9. Hand Alex a clean runbook and watch Alex execute it without verbal help. Fix the instructions wherever the run stalls.

## Expectations

- Keep the team focused on a reliable offline demo and make scope decisions quickly.
- Maintain backward compatibility with the frozen API after Ralph integrates it.
- Review the security-sensitive pieces: credentials, input validation, network exposure, and debug output.
- Give feedback in terms of observable behavior and acceptance checks.
- Pair on difficult interfaces, but leave each teammate with ownership and an understandable next step.
- Announce a freeze, rollback, or interface change to the whole team immediately.

## Deliverables

- Runnable FastAPI service with health and status endpoints.
- SQLite schema and reliable local data recording.
- Documented baseline/anomaly algorithm with `LEARNING`, `NORMAL`, `CAUTION`, and `ALERT` behavior.
- Local summary generator plus an optional, isolated OpenAI explanation path.
- Simulated-data mode and baseline reset procedure.
- Startup/runbook information that another teammate can follow.
- Known-good integrated build and final technical notes for the submission.

## Milestones

| Deadline | Your result |
| --- | --- |
| T+1 | API contract, mock response, ownership, and scope are frozen |
| T+4 | Mock API reachable from CYD network; live sensor adapter available or actively paired |
| T+7 | Live readings flow through API to CYD and failures produce controlled states |
| T+10 | SQLite, baseline, anomaly, and local summary work offline |
| T+12 | Minimum demo passes twice and a known-good build is frozen |
| T+18 | Power-cycle and offline tests pass; runbook is usable by Alex |
| T+21 | Feature freeze; three rehearsals pass and final evidence is saved |

## Dependencies and interfaces

- **From Tyeki:** normalized sensor names/units, sampling behavior, safe anomaly trigger, power and physical constraints. Accept after reproducing a stable sensor run.
- **To Ralph:** stable JSON, Pi address/port, refresh guidance, state meanings, mock mode. Accept when Ralph can display all states and recover from a stopped service.
- **From Alex:** wording and usability issues ranked by demo impact. Convert accepted issues into clear Ralph/backend changes.
- **To Alex:** complete runbook, known limitations, truth about simulated/live data, and final build identifier. Accept when Alex can rehearse without rescue.

## Stretch goals

- OpenAI-generated plain-language explanation with strict fallback and no client-side key.
- Web dashboard for recent readings and anomaly markers.
- Automated local integration test using recorded sensor traces.
- Store-and-forward event log or export for post-mission review.
- Service discovery or a QR code that simplifies connecting the CYD to the Pi.

## Done checklist

- [ ] API contract is documented and consumed by the CYD.
- [ ] Live and simulated sources use the same response shape.
- [ ] SQLite records timestamped readings and statuses.
- [ ] Baseline learning and reset behavior are documented.
- [ ] A planned stimulus reliably changes the status.
- [ ] Missing sensors, stopped backend, and no internet have controlled outcomes.
- [ ] Local summaries work with OpenAI disabled.
- [ ] No secret appears in code, firmware, logs, or demo materials.
- [ ] Alex can run the demo from the written runbook.
- [ ] The frozen build completes three consecutive rehearsals.
