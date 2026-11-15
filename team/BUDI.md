# Budi — AI Development and Integration Lead

## Role summary

You own ASTRA's AI development and end-to-end technical integration. Your
primary work is the transparent local anomaly pipeline, deterministic
explanations, optional local Gemma endpoint, and the interfaces that carry those
results reliably to Central Station and the wrist terminal.

Your standard is not the most complex model. It is the smallest explainable
intelligence that works repeatedly, stays useful offline, and integrates
cleanly with every ASTRA surface.

## Responsibilities

- Develop and document baseline learning, anomaly scoring, and stabilized state
  transitions.
- Maintain deterministic local summaries that never depend on a language model.
- Develop and guard the optional local Gemma endpoint.
- Preserve the frozen status contract and truthful data provenance.
- Integrate sensor processing, SQLite history, API delivery, Central Station,
  messaging, and wearable consumption.
- Keep AI and integration failures controlled under missing data, restart,
  service loss, internet loss, timeout, and invalid model output.
- Own integration checkpoints, known-good revisions, and technical release
  readiness.
- Provide teammates with stable test data, interface guidance, and reproducible
  run steps.

## Concrete tasks

### Deterministic intelligence

1. Keep live and simulated sensor sources compatible at the analysis boundary.
2. Filter obvious spikes, calculate quality and motion features, and preserve
   missing values instead of inventing zeros.
3. Learn a documented local baseline and expose learning progress.
4. Calculate an understandable bounded anomaly score.
5. Require stable or consecutive evidence before changing displayed state.
6. Keep anomaly-level samples from teaching the baseline that an event is
   normal.
7. Restore only compatible, baseline-eligible history after restart.
8. Generate a deterministic summary from the strongest relevant change.

### Local Gemma

1. Keep Gemma single-turn, optional, and completely outside alert decisions.
2. Bound input length, output length, context, temperature, timeout, and
   concurrency.
3. Intercept prompt injection, secret extraction, hazardous operations, and
   medical or emergency direction before inference.
4. Sanitize and validate output, replacing unsafe or unusable text with a
   deterministic fallback.
5. Report readiness without exposing model paths, prompts, secrets, or
   environment values.
6. Verify that model load and inference do not stop sensor sampling.

### Integration

1. Protect the minimum /api/v1/status contract and coordinate additive fields.
2. Keep SQLite, status, history, health, crew messaging, and chat behavior
   compatible with their documented consumers.
3. Provide deterministic simulation profiles for development and rehearsals.
4. Exercise Pi-to-Central-Station and Pi-to-wearable boundaries, including
   stale data and recovery.
5. Record the tested revision, configuration, source, expected result, and
   observed evidence at each integration checkpoint.

## Start guide

1. Read the root README, Swagger/API guide, and current implementation tests.
2. Start in simulated normal mode and verify health, status, history, and
   deterministic summaries.
3. Run cycle mode and confirm LEARNING becomes NORMAL before a labeled anomaly.
4. Run the automated backend suite before changing AI or shared contracts.
5. Give Tyeki the current schema and sample payloads for Central Station.
6. Give Ralph the compact fields, provenance rules, and failure behavior needed
   by the wrist terminal.
7. Ask Alex to review every user-facing state and explanation.
8. Run the integrated demo with internet disconnected before enabling optional
   Gemma behavior.

## Expectations

- Prefer explainable, testable logic over opaque complexity.
- Keep deterministic sensing and alerts independent of Gemma or cloud access.
- Treat missing, delayed, malformed, and stale data as expected conditions.
- Make interface changes additive when possible and announce consumer impact.
- Keep credentials, private data, model paths, and prompts out of public
  evidence.
- Reject medical, emergency, life-critical, and flight-certification claims.
- Freeze a known-good integrated revision before adding experimental features.

## Deliverables

- Documented baseline, score, state stabilization, and reset behavior.
- Deterministic local alert summaries.
- Truthful live, cached, and simulated provenance.
- Guarded local Gemma endpoint with health, timeout, concurrency, validation,
  and fallback behavior.
- Stable shared API contract and integration notes.
- Automated AI and integration tests.
- Known-good revision and exact run/recovery steps for the final demo.

## Milestones

| Deadline | Your result |
| --- | --- |
| T+1 | AI scope, frozen status contract, and simulation payload agreed |
| T+4 | Deterministic baseline and status available to both interfaces |
| T+7 | Live or simulated data integrates through Central Station and CYD |
| T+10 | Anomaly, summary, history, messaging, and recovery work offline |
| T+12 | Minimum integrated demo passes twice and revision is frozen |
| T+18 | Local Gemma guardrails and failure paths are verified if enabled |
| T+21 | Final integrated build supports three rehearsals |

## Dependencies and interfaces

- **With Tyeki:** status/history/health schema, Central Station integration,
  control-center failures, and message delivery behavior.
- **With Ralph:** compact status fields, provenance, device failure behavior,
  message API, and integration diagnostics.
- **With Alex:** state language, explanation clarity, AI limitation wording,
  reproducible failures, and final evidence.
- **From every owner:** exact failure steps and observable evidence rather than
  vague reports.

## Stretch goals

- Evaluate alternative transparent anomaly features using recorded traces.
- Add provenance-preserving event annotations and exports.
- Improve local Gemma latency only after the deterministic path is frozen.
- Add automated end-to-end tests against recorded API and message flows.

## Done checklist

- [ ] Baseline learning and state stabilization are documented and tested.
- [ ] Missing data never becomes a believable zero.
- [ ] Deterministic summaries work with Gemma disabled.
- [ ] Live, cached, and simulated sources stay truthfully labeled.
- [ ] Restart restores only compatible baseline history.
- [ ] Central Station and the wrist terminal consume the frozen contract.
- [ ] Message queue and acknowledgement integrate end to end.
- [ ] Gemma guardrails, timeout, concurrency, validation, and fallback pass.
- [ ] Internet loss does not stop the core ASTRA path.
- [ ] The frozen integrated build completes three rehearsals.
