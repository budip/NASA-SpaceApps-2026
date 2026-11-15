# Raph — CYD Wrist Terminal Developer

## Role summary

You build the wrist part of ASTRA. The CYD connects to the Raspberry Pi, asks for the latest status, and turns that data into a screen a crew member can understand quickly. Your job is complete when the wrist terminal clearly shows every state, handles lost connections safely, and comes back after the Pi returns.

Think of the terminal as a safety display: it should be simple, calm, and truthful. A missing connection must never look like “everything is normal.”

## Responsibilities

- Set up and program the correct CYD board and display.
- Connect the CYD to the team's local Wi-Fi network or hotspot.
- Request the status JSON from the Pi at a steady, reasonable rate.
- Show `LEARNING`, `NORMAL`, `CAUTION`, `ALERT`, and `OFFLINE` clearly.
- Display a few useful readings and a short summary without crowding the screen.
- Detect old or missing data and show `OFFLINE`.
- Recover automatically when the Pi or network comes back.
- Give Alex a build that is easy to test and Budi clear logs when something fails.

## Concrete tasks

1. Identify the exact CYD board version, screen driver, resolution, touch controller if used, and available flash/RAM.
2. Build a first screen with fake values and all five states.
3. Put network name, password, Pi address, and refresh rate in one configuration place. Do not publish real passwords.
4. Connect to Budi's mock endpoint and read the JSON fields in the README.
5. Update the screen without blocking the device. Keep the last successful timestamp.
6. If requests fail or data is too old, display `OFFLINE` with a visible reconnect indicator.
7. Treat missing fields as unavailable; do not reboot or freeze.
8. Add a small diagnostic view or serial log for Wi-Fi state, HTTP result, last update, and parse errors.
9. Test power-on, network loss, Pi loss, invalid JSON, slow response, and recovery.
10. Write the exact build, upload, configuration, and reset steps for another person.

## Start guide

### 1. Get the screen working

Ask Budi where the CYD project should live and which toolchain the team will use. Confirm the board version before choosing display settings. Upload a tiny program that fills the screen with a color and prints `ASTRA`. Save the working board and display settings.

### 2. Draw the five states with fake data

Make a simple layout:

- Top: ASTRA and connection symbol;
- Middle: large state word;
- Below it: one short sentence;
- Bottom: temperature, humidity, pressure, and age of last update.

Use more than color. Add a word and a symbol so the meaning is still clear in bright light or to someone who sees color differently. Ask Alex to approve the wording and quick-glance readability.

### 3. Connect to the Pi

Use Budi's mock API first. Request `GET /api/v1/status`, read only the documented fields, and show the result. Keep the request interval conservative—about once per second is plenty for the demo unless Budi changes it.

Start with this rule:

- Good, recent response: show the status from the Pi.
- No good response for the agreed timeout: show `OFFLINE`.
- Good response returns: update the screen and clear `OFFLINE` automatically.

Never guess that the environment is normal after a request fails.

### 4. Test bad situations on purpose

With the team ready, try each case:

1. Turn the Pi service off and wait for `OFFLINE`.
2. Start it again and check recovery.
3. Ask Budi to send one response with a missing sensor.
4. Ask Budi to send bad JSON and confirm the CYD stays usable.
5. Restart the CYD and check that it reconnects without a computer.

Write down what happened and give Alex the build for the full test sheet.

## Expectations

- Keep the main screen readable from arm's length within one second.
- Do not hide connection failure behind an old normal reading.
- Keep networking and screen drawing separate enough that a slow request does not freeze the display.
- Work against the shared API contract; ask Budi before changing field names.
- Share a working build early, even if it is plain.
- Tell Budi the exact serial error or HTTP result when blocked.
- After the T+12 freeze, focus on reliability and clarity before animation or decoration.

## Deliverables

- CYD firmware that builds and uploads using written steps.
- Clear screen for all five states and missing sensor values.
- Local-network connection and API parsing.
- Stale-data timeout, `OFFLINE` state, and automatic recovery.
- Useful diagnostics for integration.
- Configuration notes that do not expose passwords.
- A tested firmware build identified for the final demo.

## Milestones

| Deadline | Your result |
| --- | --- |
| T+1 | Exact CYD hardware and toolchain confirmed |
| T+4 | Fake data and all states visible; first Alex review complete |
| T+7 | Live Pi response displayed; disconnect and recovery demonstrated |
| T+10 | Every backend state and missing-value case handled |
| T+12 | Minimum wrist demo passes twice and build is frozen |
| T+18 | Power-on, network loss, malformed response, and recovery tests pass |
| T+21 | Final firmware supports three complete rehearsals |

## Dependencies and interfaces

- **From Budi:** JSON contract, mock/live URL, refresh and timeout guidance, state meanings. Accept when the CYD displays a mock response and Budi sees correct request logs.
- **To Budi:** request behavior, diagnostic output, failure cases, and required network settings. Hand off with a 30-second disconnect/reconnect demonstration.
- **From Alex:** final state wording and readability feedback. Accept only wording that fits without making critical text too small.
- **To Alex:** labeled test build and simple power/restart instructions. The handoff is complete when Alex can run all display tests without editing code.
- **From Tyeki:** physical wrist mounting and power constraints. Confirm cable direction, heat, strain relief, and access to reset/USB before enclosure freeze.

## Stretch goals

- Touch screen for details, mute/acknowledge, or sensor history.
- Small sparkline for the sensor that caused an alert.
- Vibration, buzzer, or LED alert if the hardware is available and safe.
- Battery level and signal-strength display.
- Friendly local setup screen for changing the Pi address.

## Done checklist

- [ ] The exact CYD model and working display settings are documented.
- [ ] All five states are clear without relying on color alone.
- [ ] The CYD reads the shared JSON response.
- [ ] Missing values and bad JSON do not freeze or reboot the device.
- [ ] Old or missing data becomes `OFFLINE` within the agreed time.
- [ ] The display recovers when the Pi returns.
- [ ] Power-on works without a development computer.
- [ ] Alex approved readability and can run the test build.
- [ ] Build/upload instructions work for another teammate.
- [ ] The final firmware passes three full rehearsals.
