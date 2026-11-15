# ASTRA Agent Instructions

These instructions apply to work inside `ai/`. Treat the repository root
`README.md` as the product and integration source of truth. Read the relevant
guide in `team/` before changing a component owned by Budi, Ralph, Tyeki, or
Alex.

## Mission

Build the smallest reliable ASTRA demonstration in which the Sense HAT feeds a
Raspberry Pi service, the service stores and evaluates readings locally, and a
CYD wrist terminal plus the Pi-hosted Central Station show a truthful state.
The core sensing, storage, anomaly detection, messaging, and deterministic
explanation paths must continue without internet access. The local Gemma chat
endpoint is experimental and must not influence sensor states or alerts.

## Priority Order

Work in this order and do not trade a working lower level for an unfinished
higher one:

1. Live or simulated sensor data reaches the API, CYD, and Central Station.
2. SQLite history, local baseline, anomaly states, and local explanations work
   offline.
3. The wearable setup, queued message delivery, recovery behavior, and safe
   anomaly trigger are repeatable.
4. Local Gemma chat, richer visuals, and other refinements are optional.

When a request is ambiguous, choose the smallest change that advances the
earliest incomplete level.

## Stable Contracts

- Preserve the `/api/v1/status` contract documented in `README.md` unless the
  task explicitly authorizes a contract change.
- Treat `team/SWAGGER_API_GUIDE.md` as the source of truth for the current
  additive API surface: history, crew messaging, suit telemetry, simulated
  biometrics and tasks, and local chat.
- Valid states are `LEARNING`, `NORMAL`, `CAUTION`, `ALERT`, and `OFFLINE`.
- The top-level `source` must truthfully be `live`, `cached`, or `simulated`.
  Nested suit, biometric, and task data must retain their own provenance; do
  not imply that simulated data became live because ambient Sense HAT data is
  live.
- Missing sensor values are valid input and must not crash the backend or
  firmware. Do not replace a failed reading with a believable zero.
- A stale or unreachable backend must become `OFFLINE`; it must never remain a
  misleading `NORMAL` state.
- Every alert needs a deterministic local summary. Model output may not be
  required for operation or change deterministic alert decisions.
- Keep `sensors.pressure_hpa` and `sensors.temperature_c` defined as ambient
  backpack measurements. The separate suit objects are explicitly simulated
  unless a future source truthfully says otherwise.
- Preserve queued-to-delivered message semantics and recipient-scoped wearable
  polling. The prototype has no authentication and must remain on a trusted
  private LAN.

## Engineering Boundaries

- Keep hardware I/O behind adapters so live and simulated sources share the
  same normalized shape.
- Keep sensor input, storage, analysis, explanation, and HTTP delivery
  separable enough to test independently.
- Keep the independently maintained `central-station/` assets compatible with
  the copies served by the Pi backend.
- Put ports, addresses, sensor mode, timeouts, database paths, and optional AI
  settings in configuration rather than scattering literals through code.
- Prefer transparent anomaly logic appropriate for a prototype. Document the
  learning window, thresholds, stabilization rule, and baseline-reset behavior.
- Use UTC timestamps at software boundaries and include units in schemas or
  nearby documentation.
- Maintain a clearly labeled simulated path for development and demo recovery.

## Safety, Privacy, and Claims

- Never commit Wi-Fi credentials, API keys, tokens, private data, or secrets in
  source, firmware, logs, screenshots, recordings, or example configuration.
- Keep Gemma inference local to the Pi, bounded, single-turn, guarded, and
  optional. Validate model output and return a deterministic safe response when
  inference is unavailable or rejected.
- Any future cloud or OpenAI integration may be called only by the backend and
  must use a short timeout, minimal context, output validation, and silent
  fallback to deterministic local behavior.
- Do not describe ASTRA, the Sense HAT, or its anomaly model as medical,
  life-critical, flight-certified, or validated for crew safety.
- Always label biometrics, mission tasks, and default suit telemetry as
  simulated prototype data. Do not use them for medical, emergency, or flight
  decisions.
- Hardware test procedures must avoid flame, liquids near electronics,
  excessive heat or cold, unsafe acceleration, damaged batteries, exposed
  conductors, and blocked ventilation.

## Verification

Test in proportion to the change. Start with focused automated checks, then
exercise the affected boundary. Integration work should cover the normal path
plus relevant failures such as missing fields, malformed data, stale data,
service loss, network loss, restart, and internet loss. Messaging changes must
cover queue, recipient filtering, acknowledgement, and persistence. Chat
changes must cover readiness, guardrails, invalid output, timeout, concurrency,
and disabled-model fallback without interrupting sensor sampling.

Do not claim hardware behavior that was only simulated. Record whether evidence
is live, cached, simulated, or transformed. For a demo-ready change, include
exact run steps, expected behavior, actual evidence, known limits, and the build
or revision tested.

## Change Discipline

- Inspect existing code and configuration before adding new frameworks or
  directories.
- Keep interface changes small and call out their impact on every consumer.
- Preserve the main runnable path and unrelated user changes.
- After the minimum demo freeze, prioritize reliability, recovery, truthful
  presentation, and documentation over new features.
- Finish with the shared five-part handoff: what is ready, how to run it, what
  the receiver gets, known limits, and proof.

