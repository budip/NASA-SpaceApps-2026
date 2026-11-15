# ASTRA Agent Instructions

These instructions apply to work inside `AI/`. Treat the repository root
`README.md` as the product and integration source of truth. Read the relevant
guide in `team/` before changing a component owned by Budi, Ralph, Tyeki, or
Alex.

## Mission

Build the smallest reliable ASTRA demonstration in which the Sense HAT feeds a
Raspberry Pi service, the service stores and evaluates readings locally, and a
CYD wrist terminal shows a truthful state. The core sensing, storage, anomaly
detection, and fallback explanation must continue without internet access.

## Priority Order

Work in this order and do not trade a working lower level for an unfinished
higher one:

1. Live or simulated sensor data reaches the API and CYD.
2. SQLite history, local baseline, anomaly states, and local explanations work
   offline.
3. The wearable setup and safe anomaly trigger are repeatable.
4. OpenAI explanations, richer visuals, and other refinements are optional.

When a request is ambiguous, choose the smallest change that advances the
earliest incomplete level.

## Stable Contracts

- Preserve the `/api/v1/status` contract documented in `README.md` unless the
  task explicitly authorizes a contract change.
- Valid states are `LEARNING`, `NORMAL`, `CAUTION`, `ALERT`, and `OFFLINE`.
- `source` must truthfully be `live`, `cached`, or `simulated`.
- Missing sensor values are valid input and must not crash the backend or
  firmware. Do not replace a failed reading with a believable zero.
- A stale or unreachable backend must become `OFFLINE`; it must never remain a
  misleading `NORMAL` state.
- Every alert needs a deterministic local summary. OpenAI output may enhance
  that summary but may not be required for operation.

## Engineering Boundaries

- Keep hardware I/O behind adapters so live and simulated sources share the
  same normalized shape.
- Keep sensor input, storage, analysis, explanation, and HTTP delivery
  separable enough to test independently.
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
- Only the backend may call OpenAI. Use a short timeout, minimal numeric
  context, output validation, and silent fallback to the local explanation.
- Do not describe ASTRA, the Sense HAT, or its anomaly model as medical,
  life-critical, flight-certified, or validated for crew safety.
- Hardware test procedures must avoid flame, liquids near electronics,
  excessive heat or cold, unsafe acceleration, damaged batteries, exposed
  conductors, and blocked ventilation.

## Verification

Test in proportion to the change. Start with focused automated checks, then
exercise the affected boundary. Integration work should cover the normal path
plus relevant failures such as missing fields, malformed data, stale data,
service loss, network loss, restart, and internet loss.

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

