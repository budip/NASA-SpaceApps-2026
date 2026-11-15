# Tyeki — Central Station and Control Center Developer

## Role summary

You own ASTRA's complete control-center experience. Your primary implementation
area is central-station/: the browser dashboard served by the Raspberry Pi,
telemetry and history views, system-health monitoring, crew messaging, and the
operator workflow used during the demo.

Your standard is a control center that tells the truth at a glance. Operators
must be able to distinguish live, cached, simulated, stale, and unavailable
data without reading source code or opening developer tools.

## Responsibilities

- Develop and maintain all Central Station interface code.
- Present current status, trends, service health, data quality, and provenance.
- Keep simulated biometrics, suit telemetry, and mission tasks visibly labeled.
- Provide the crew roster, message composer, outbox, and delivery state.
- Turn service loss or stale telemetry into an obvious OFFLINE experience.
- Keep the dashboard usable on the private LAN without internet access.
- Coordinate control-center wording and interaction decisions with Alex.
- Document how to open, operate, test, and recover the control center.

## Concrete tasks

### Dashboard

1. Render LEARNING, NORMAL, CAUTION, ALERT, and OFFLINE without relying on color
   alone.
2. Show the deterministic summary, sample age, source, and relevant sensor
   values.
3. Display bounded history and trends without overwhelming the Raspberry Pi or
   browser.
4. Surface health information including sensor mode, baseline progress,
   freshness, and sampling failures.
5. Make live, cached, simulated, and unavailable values visually distinct.

### Crew messaging

1. Load the server-provided crew roster.
2. Validate message recipient, priority, and length before sending.
3. Show QUEUED after the Pi stores a message and DELIVERED only after the
   addressed wearable acknowledges it.
4. Keep failures recoverable and never claim a message was delivered without
   acknowledgement.
5. Test recipient isolation with Ralph's configured wearable ID.

### Reliability and integration

1. Consume only documented API fields and handle missing optional fields.
2. Show controlled empty and error states for slow, malformed, or unavailable
   responses.
3. Keep the integrated Pi-hosted dashboard compatible with central-station/
   source assets.
4. Verify operation with internet disconnected while the private LAN remains
   active.
5. Record browser, viewport, API version, expected result, and actual evidence
   for each control-center test.

## Start guide

1. Read the root README and the Swagger/API guide.
2. Start the Raspberry Pi service in simulated cycle mode.
3. Open /dashboard and confirm status, health, history, simulated labels, crew,
   and message outbox load without console errors.
4. Compare every displayed field with /api/v1/status, /api/v1/history, and
   /health.
5. Work with Alex to review hierarchy, wording, accessibility, and operator
   flow.
6. Work with Ralph to queue a message for the configured wearable and observe
   its acknowledgement.
7. Stop the service and verify the control center becomes clearly OFFLINE.
8. Restore the service and verify the dashboard recovers without a page reset.

## Expectations

- Treat the API as a contract; coordinate field changes with Budi.
- Never hide stale, simulated, or unavailable data behind a live-looking card.
- Keep operator-critical information readable at a glance.
- Preserve a buildless browser path for the integrated dashboard.
- Keep credentials and private information out of source, screenshots, and
  logs.
- Prioritize reliability and truthful state over decorative animation.

## Deliverables

- Pi-hosted Central Station dashboard.
- Current status, history, health, and provenance views.
- Crew message composer with truthful queue and delivery state.
- Controlled loading, empty, stale, malformed-response, and offline states.
- Control-center operating and recovery notes.
- Browser screenshots or recordings labeled with the tested build and source.

## Milestones

| Deadline | Your result |
| --- | --- |
| T+1 | Control-center information hierarchy and API needs agreed |
| T+4 | Simulated status and health visible in Central Station |
| T+7 | Live Pi status, history, and offline recovery demonstrated |
| T+10 | Provenance labels and crew messaging work end to end |
| T+12 | Integrated control center passes two complete demo runs |
| T+18 | Error states, accessibility, and operator recovery are verified |
| T+21 | Final control center supports three timed rehearsals |

## Dependencies and interfaces

- **From Budi:** stable AI state, score, summary, provenance, health behavior,
  and integration support.
- **To Budi:** API mismatches, integration failures, and the exact fields needed
  by the control center.
- **With Ralph:** recipient IDs, message priorities, acknowledgement behavior,
  and shared display terminology.
- **With Alex:** information hierarchy, plain-language wording, accessibility,
  usability findings, and demo flow.

## Stretch goals

- Add accessible trend annotations for anomaly events.
- Add an operator-focused local Gemma panel only after deterministic status and
  messaging are reliable.
- Add exportable, provenance-preserving demo evidence.
- Improve responsive layouts for large displays and tablets.

## Done checklist

- [ ] Central Station loads from the Pi on the private LAN.
- [ ] All five states remain understandable without color alone.
- [ ] Status, history, and health agree with the API.
- [ ] Simulated and unavailable data are unmistakably labeled.
- [ ] Service loss becomes OFFLINE and recovery is automatic.
- [ ] Messages move from QUEUED to DELIVERED only after wearable acknowledgement.
- [ ] Unknown recipients and invalid messages fail clearly.
- [ ] Alex has approved the operator flow and readability.
- [ ] No credential or private data appears in assets or evidence.
- [ ] The final dashboard passes three complete rehearsals.
