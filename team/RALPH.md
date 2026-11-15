# Ralph — CYD Wrist Terminal and 3D Printing Developer

## Role summary

You own ASTRA's wrist terminal and its physical enclosure. Your primary work is
the ESP32-2432S028 CYD firmware, touchscreen experience, device-side API and
message integration, and the 3D-printed enclosure and wearable mount.

You do not own network infrastructure. The firmware must consume the configured
Pi service reliably, but router, LAN, and control-center networking decisions
belong outside this role.

## Responsibilities

- Configure, build, and maintain the CYD firmware.
- Present vitals, navigation, environmental readings, messages, and provenance
  clearly on the touchscreen.
- Handle missing, stale, malformed, or unavailable API data without freezing.
- Receive only messages addressed to the configured astronaut and acknowledge
  them after display.
- Maintain touch calibration, local setup, display customization, and recovery.
- Measure the board and design a protective, printable wearable enclosure.
- Preserve access to USB, reset, touch, ventilation, and cable strain relief.
- Document firmware build/upload steps and enclosure print/assembly steps.

## Concrete tasks

### Wrist firmware

1. Confirm the exact CYD board, display driver, touch controller, pins, USB
   connector, and power behavior.
2. Keep screen drawing, API polling, touch input, and message handling
   responsive.
3. Parse only documented fields and treat missing values as unavailable.
4. Stop presenting old API values as live after the agreed stale timeout.
5. Show whether values are live, simulated, mixed, or demo-only.
6. Poll the recipient-scoped message inbox, validate the response, display the
   message, and retry acknowledgement safely.
7. Preserve a clearly labeled demo mode for development and recovery.

### 3D printing and wearable fit

1. Measure the real board, display opening, connector placement, reset access,
   mounting holes, and component clearance before modeling.
2. Create an enclosure that protects the board without pressing the touchscreen
   or blocking ventilation.
3. Add safe cable routing, strain relief, rounded edges, and a practical wrist
   or forearm attachment.
4. Print a fit prototype before the final enclosure and record printer,
   material, layer height, orientation, supports, and revision.
5. Inspect the assembled enclosure for heat, sharp edges, pinching, loose
   hardware, and blocked controls.

### Verification

1. Test power-on, touch calibration, API loss, malformed JSON, missing fields,
   stale data, message delivery, acknowledgement retry, and recovery.
2. Confirm the device never labels simulated vitals or demo values as live.
3. Run the firmware in the final enclosure long enough to check heat, comfort,
   access, and cable strain.
4. Give Alex the exact build and enclosure revision used for each test.

## Start guide

1. Read the root README, wearable guide, and frozen status contract.
2. Build and upload the esp32-2432s028 PlatformIO environment.
3. Complete touch calibration and verify all existing pages in demo mode.
4. Configure the Pi endpoint through the on-device setup flow.
5. Compare displayed values and provenance with the API response.
6. Work with Tyeki to receive and acknowledge a Central Station message.
7. Work with Alex to review glance readability, touch targets, wording, and
   physical comfort.
8. Measure the real device, print a low-cost fit prototype, revise, and only
   then print the final enclosure.

## Expectations

- Keep the wrist experience readable from arm's length.
- Do not hide connection failure behind an old live-looking value.
- Keep secrets out of firmware, source control, logs, and screenshots.
- Ask Budi before depending on a new API field.
- Ask Alex to approve wording and interaction changes.
- Use the actual board for enclosure measurements; do not trust a generic model.
- Stop using an enclosure that traps heat, has sharp edges, restricts
  circulation, or damages cables.

## Deliverables

- Reproducible CYD firmware build and upload instructions.
- Touchscreen experience with truthful live/simulated/offline presentation.
- Recipient-scoped message display and acknowledgement.
- Diagnostics sufficient to reproduce device-side failures.
- Printable enclosure source, exported print file, and revision notes.
- Print settings, assembly steps, and wearable safety inspection.
- A labeled firmware and enclosure combination for the final demo.

## Milestones

| Deadline | Your result |
| --- | --- |
| T+1 | CYD revision, toolchain, dimensions, and enclosure constraints confirmed |
| T+4 | Core screens and first enclosure sketch reviewed by Alex |
| T+7 | Pi data and Central Station messages appear on the wrist terminal |
| T+10 | Failure handling and first enclosure fit print are complete |
| T+12 | Firmware plus wearable enclosure pass two demo runs |
| T+18 | Recovery, comfort, heat, cable, and print-revision checks pass |
| T+21 | Final firmware/enclosure pair supports three rehearsals |

## Dependencies and interfaces

- **From Budi:** stable status fields, state meanings, provenance, and
  integration support.
- **To Budi:** parse failures, stale-data behavior, and device-side integration
  evidence.
- **With Tyeki:** crew recipient IDs, message priority, acknowledgement, and
  terminology shared with Central Station.
- **With Alex:** wrist information hierarchy, wording, touch usability, visual
  accessibility, comfort, and final demo behavior.

## Stretch goals

- Add a compact anomaly-state screen once current pages remain stable.
- Add accessible haptic or audible cues if the hardware supports them safely.
- Add a battery indicator based on a real measurement rather than an estimate.
- Refine the enclosure for faster assembly and multiple strap sizes.

## Done checklist

- [ ] Firmware builds and uploads from written instructions.
- [ ] Touch calibration and all required pages work after reboot.
- [ ] Missing, malformed, stale, and unavailable data remain controlled.
- [ ] Live and simulated values are clearly distinguished.
- [ ] Recipient-scoped messages display and acknowledge correctly.
- [ ] The enclosure matches the actual board and leaves controls accessible.
- [ ] Ventilation, cable strain, edges, and wearer comfort are acceptable.
- [ ] Print source, exported file, settings, and revision are documented.
- [ ] Alex approves the wrist experience and physical presentation.
- [ ] The final firmware/enclosure pair passes three rehearsals.
