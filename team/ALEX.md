# Alex — User Experience Designer, Tester, and Demo Guide

## Role summary

You own the user experience across ASTRA. You make the Central Station and wrist
terminal understandable, accessible, and easy to operate, then test the complete
project from a user's point of view and turn verified behavior into the demo
story.

Your most useful question is: **Can a new person tell what is happening, which
data is real or simulated, and what to do next?**

## Responsibilities

- Define the information hierarchy and plain-language wording for both screens.
- Make state, source, freshness, message priority, and delivery status clear
  without relying only on color.
- Review Central Station with Tyeki and the wrist experience with Ralph.
- Test the project by following written steps exactly.
- Record reproducible bugs with expected and actual results.
- Organize screenshots, photos, videos, test records, and build identifiers.
- Write the main demo and a recovery path that does not overstate the prototype.
- Lead timed rehearsals and keep every claim aligned with evidence.

## Concrete tasks

### User experience

1. Define consistent wording for LEARNING, NORMAL, CAUTION, ALERT, and OFFLINE.
2. Review layout hierarchy, readability, contrast, symbols, touch targets, and
   error recovery on Central Station and the CYD.
3. Make live, cached, simulated, mixed, stale, and unavailable states
   understandable to a first-time viewer.
4. Review crew-message composition, priority, receipt, and delivery feedback.
5. Verify the physical wrist enclosure is understandable, comfortable, and
   does not obstruct controls.

### Testing

Create repeatable tests for:

- startup and baseline learning;
- normal and simulated anomaly states;
- missing fields and malformed responses;
- Pi/service loss and recovery;
- internet loss while the private LAN remains active;
- live versus simulated provenance;
- Central Station message queue and wearable acknowledgement;
- local Gemma readiness, guardrails, fallback, and slow response;
- device reboot, touch calibration, and final enclosure use.

For every run, record time, revision, configuration, source, steps, expected
result, actual result, pass/fail, and owner.

### Demo

1. Write a 60–90 second main path: mission, normal operation, safe change,
   alert, explanation, control-center message, wrist receipt, and offline-first
   behavior.
2. Write a backup path that uses clearly labeled simulation and captured
   evidence.
3. Prepare a one-sentence limitation statement covering simulated data and
   prototype status.
4. Rehearse three times with the exact final hardware and build.

## Start guide

1. Read the root README and current limitations.
2. Ask Tyeki to walk through the full Central Station operator flow.
3. Ask Ralph to demonstrate the wrist UI, message receipt, and enclosure.
4. Ask Budi to explain deterministic anomaly behavior, provenance, and local
   Gemma boundaries.
5. Create one shared wording sheet and one test sheet.
6. Review both screens from normal viewing distance, not only close up.
7. Run the main and backup demo paths without verbal help from developers.

## Bug report format

Use a report that another teammate can reproduce:

> At 3:10 PM on revision abc123, using simulated cycle mode, I stopped the Pi
> service. Central Station still showed NORMAL after 15 seconds. I expected
> OFFLINE. Tyeki should inspect dashboard freshness handling.

Never invent a test result. Label all evidence as live, cached, simulated, or
transformed.

## Expectations

- Use plain language that a visitor understands on the first pass.
- Test documented behavior rather than relying on developer shortcuts.
- Report failures quickly with evidence.
- Keep accessibility and recovery part of the primary design.
- Ask before unplugging, heating, moving, or changing hardware.
- Stop visual polishing when a required workflow is failing.
- Never describe ASTRA as medical, emergency-ready, or flight-certified.

## Deliverables

- Shared UX wording and state/source terminology.
- Reviewed Central Station and wrist-terminal flows.
- Completed test sheet with reproducible failure reports.
- Demo script, backup path, and limitation statement.
- Organized evidence labeled with revision and provenance.
- Three timed rehearsal records.

## Milestones

| Deadline | Your result |
| --- | --- |
| T+1 | Mission wording, user journey, and state language agreed |
| T+4 | First Central Station and wrist UX review complete |
| T+7 | First end-to-end test and prioritized issue list complete |
| T+10 | Alert, offline, provenance, and messaging flows tested |
| T+12 | Main and backup demo paths pass twice |
| T+18 | Accessibility, enclosure, AI-boundary, and recovery reviews complete |
| T+21 | Three final rehearsals complete and timed |

## Dependencies and interfaces

- **With Tyeki:** control-center hierarchy, wording, accessibility, errors,
  message workflow, and operator testing.
- **With Ralph:** wrist hierarchy, wording, touch usability, enclosure comfort,
  source labeling, and message receipt.
- **With Budi:** AI state language, deterministic explanations, local model
  boundaries, integration issues, and evidence for claims.

## Stretch goals

- Run a five-minute usability test with someone outside the team.
- Produce annotated project screenshots and a simple architecture graphic.
- Prepare 30-second and three-minute versions of the pitch.
- Create a lightweight accessibility checklist for future screens.

## Done checklist

- [ ] I can explain ASTRA in one clear sentence.
- [ ] Both interfaces use consistent state and provenance language.
- [ ] Critical meaning does not depend on color alone.
- [ ] I tested normal, anomaly, offline, recovery, and internet-loss behavior.
- [ ] I tested message queue, receipt, and delivery acknowledgement.
- [ ] I verified simulated and live evidence are labeled correctly.
- [ ] Every failed test has reproducible steps and an owner.
- [ ] The main and backup demo paths match actual capabilities.
- [ ] Evidence is organized by revision and source.
- [ ] Three final rehearsals finish within the planned time.
