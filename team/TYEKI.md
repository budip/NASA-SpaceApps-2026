# Tyeki — Backpack Hardware and Sensor Lead

## Role summary

You own the physical sensing system: Raspberry Pi 3, Sense HAT, power, wiring, backpack placement, and the safe test method used to produce a detectable environmental change. You translate the Sense HAT's raw measurements into a dependable engineering input for Budi's software and help make the prototype wearable enough for a convincing demonstration.

Treat the backpack as an early engineering prototype. The goal is traceable measurements, stable operation, safe handling, and honest documentation of limitations.

## Responsibilities

- Inventory, inspect, assemble, and label the Pi/Sense HAT hardware.
- Define sensor names, units, expected ranges, sampling interval, and limitations.
- Confirm stable temperature, humidity, pressure, orientation, and acceleration reads.
- Characterize warm-up and thermal bias from the Pi/Sense HAT assembly.
- Provide Budi a clean, repeatable sensor-sampling interface or reference script.
- Design a safe and repeatable method for creating an anomaly during the demo.
- Plan power, cable routing, ventilation, strain relief, mounting, and access.
- Document startup, shutdown, handling, and troubleshooting.

## Concrete tasks

### Hardware bring-up

1. Record the Pi model/revision, Sense HAT version, storage, power supply, battery pack, cables, and mounting materials.
2. Inspect headers and connectors; mount the Sense HAT with correct orientation and spacers.
3. Verify regulated power is appropriate for the Pi 3 and observe undervoltage or thermal warnings.
4. Enable the required Pi interfaces and confirm each Sense HAT sensor returns plausible values.
5. Log at least 10 minutes of stationary readings with timestamps, followed by a labeled motion segment.

### Sensor characterization

1. Use SI units in the software boundary: degrees Celsius, percent relative humidity, hectopascals, g or m/s² as agreed, and degrees/radians as agreed.
2. Measure warm-up behavior. Note how the Pi's heat affects Sense HAT temperature and how long readings take to settle.
3. Estimate idle noise and slow drift for each chosen feature; give Budi representative normal data.
4. Identify which readings are reliable enough for the main story. Do not present Sense HAT measurements as life-critical physiological or certified cabin measurements.
5. Mark every recorded trial as live, simulated, or transformed/calibrated.

### Integration adapter

1. Agree with Budi on one sample object with timestamp, values, units/source metadata, and missing-value behavior.
2. Keep I/O failures explicit. A failed sensor read should return a controlled error or missing value rather than a believable zero.
3. Choose a sample rate that fits slow environmental changes and the Pi 3; roughly 1 Hz is sufficient for the minimum demo unless testing shows otherwise.
4. Provide a replayable sample file so Budi can develop without occupying the hardware.

### Physical prototype and demo trigger

1. Position the Pi and power source so ventilation is not blocked and hot surfaces do not rest against the wearer.
2. Add strain relief and prevent exposed conductors or sharp edges from contacting the wearer.
3. Keep shutdown, charging, reset, and cable access practical.
4. Define one safe anomaly trigger with a repeatable duration and distance. Prefer mild airflow, ordinary room-to-room environmental change, or controlled orientation/motion. Avoid open flame, liquids near electronics, excessive heat/cold, or unsafe acceleration.
5. Test whether the chosen trigger consistently crosses Budi's detection threshold and returns to baseline in demo time.

## Start guide

1. Read the [team README](../README.md) and underline the required sensor-to-screen path and checkpoints.
2. Make a hardware table with item, owner, condition, power requirement, and backup. Photograph the connected stack before putting it in the backpack.
3. Assemble on a nonconductive surface. Power the Pi with the known-good supply and check for undervoltage/temperature warnings.
4. Run a sensor check for temperature, humidity, pressure, orientation, and acceleration. Compare stationary values with expected room conditions and note obvious errors.
5. Record a 10-minute warm-up dataset. Add event labels rather than relying on memory.
6. Give Budi the field names, units, missing-data convention, sample interval, and a short recorded dataset at T+1.
7. Produce the smallest sensor adapter or reference script that returns one normalized sample. Demonstrate it to Budi at T+4.
8. Work with Budi to tune one safe anomaly trigger. Measure its response over at least three trials.
9. Install the stack in the backpack only after the bench setup is stable. Re-run the sensor test after mounting because heat and orientation may change.
10. Teach Alex the trigger and hardware handling using written steps. Watch Alex repeat it before accepting the handoff.

## Expectations

- Use units and timestamps consistently; document assumptions and transformations.
- Distinguish sensor accuracy, repeatability, and demo behavior. Do not claim validation the team did not perform.
- Keep the bench setup recoverable until the integrated demo passes.
- Report power, thermal, mounting, or sensor-read failures immediately because they affect every software layer.
- Change only one physical variable at a time during characterization.
- Get Budi's agreement before changing field names or sample rates after first integration.
- Stop and correct unsafe heat, battery damage, exposed conductors, unstable mounting, or strain immediately.

## Deliverables

- Hardware inventory and connection/orientation notes.
- Stable Pi 3 + Sense HAT assembly and power plan.
- Sensor field/unit definition plus representative normal and event data.
- Working normalized sensor adapter or reference script for Budi.
- Warm-up, noise, thermal-bias, and prototype-limitation notes.
- Safe, repeatable anomaly-trigger procedure with three-trial evidence.
- Wearable mounting and a short hardware start/shutdown/troubleshooting runbook.

## Milestones

| Deadline | Your result |
| --- | --- |
| T+1 | Inventory complete; sensor fields, units, and power risks handed to Budi |
| T+4 | Stable live sample stream and reference dataset accepted by Budi |
| T+7 | Mounted or bench-ready hardware supports live Pi → CYD integration |
| T+10 | Safe anomaly trigger succeeds repeatedly and recovery is understood |
| T+12 | Hardware setup supports two complete offline demo runs |
| T+18 | Power-cycle, thermal, cable, and wearable checks completed |
| T+21 | Hardware supports three rehearsals without intervention |

## Dependencies and interfaces

- **To Budi:** normalized values, units, timestamps, missing-data behavior, representative datasets, and sensor limitations. The handoff is accepted when Budi can run the adapter and replay the data without your help.
- **From Budi:** chosen sample rate, anomaly features, threshold behavior, and logging requirements. Confirm the trigger against the exact frozen algorithm.
- **With Ralph:** agree on wrist-terminal power/mounting constraints and avoid cable or enclosure choices that block controls or create strain.
- **To Alex:** handling rules, startup/shutdown steps, and the safe anomaly trigger. The handoff is accepted when Alex repeats the trigger and obtains the expected state without unsafe improvisation.

## Stretch goals

- Compare Sense HAT temperature with an external reference and add a documented empirical offset if justified.
- Add an external sensor only if the core system is frozen and the interface remains compatible.
- Estimate battery runtime under realistic load.
- Design or model a ventilated enclosure with better strain relief.
- Add a sensor-health metric that distinguishes disconnected, saturated, stale, and plausible data.

## Done checklist

- [ ] Pi, Sense HAT, power, storage, and backup items are inventoried.
- [ ] Every used sensor has documented name, unit, sample rate, and limitation.
- [ ] Warm-up and Pi heat effects were measured and recorded.
- [ ] Budi can consume the normalized live sample and replay file.
- [ ] Sensor failures produce missing/error data rather than fake zeros.
- [ ] The safe anomaly trigger works in at least three trials.
- [ ] Mounting, ventilation, cable strain, and access are acceptable.
- [ ] No unsafe heat, damaged battery, sharp edge, or exposed conductor remains.
- [ ] Alex can operate the hardware from the written guide.
- [ ] The final hardware setup passes three complete rehearsals.
