# Alex — Experience Designer, Tester, and Demo Guide

## Role summary

You help make ASTRA easy to understand and easy to demonstrate. You decide whether the wrist screen is clear, test the project like a crew member would use it, record problems, and help tell the final story. You do not need to understand every line of code. Your most useful question is: **“Can a new person tell what is happening and what to do next?”**

## Responsibilities

- Choose short, clear words for the wrist screen with Ralph.
- Check that colors, symbols, and text all communicate the same state.
- Test the system by following written steps exactly.
- Write down bugs so another teammate can repeat them.
- Keep screenshots, photos, short videos, and test results organized.
- Build the demo script and make sure every claim matches what the project really does.
- Lead rehearsals and time the final presentation.
- Speak up when a screen, instruction, or explanation is confusing.

## Concrete tasks

1. Make a one-page test sheet with these cases:
   - Starting and learning the normal environment;
   - Showing normal readings;
   - Creating the planned unusual condition;
   - Returning to normal;
   - Turning off the Pi or network;
   - Turning off the internet while the local system stays on;
   - Restarting the system.
2. Agree with Ralph on the screen states:
   - `LEARNING`: “Learning surroundings”;
   - `NORMAL`: “All conditions normal”;
   - `CAUTION`: “Change detected — check conditions”;
   - `ALERT`: “Strong change detected”;
   - `OFFLINE`: “Backpack not connected.”
3. For each test, record the time, what you did, what you expected, what happened, and who should look at it.
4. Take readable pictures of the working wrist screen and backpack.
5. Make a 60–90 second demo path: introduce the problem, show normal, create a safe change, show the alert and explanation, disconnect internet, and show that ASTRA keeps working.
6. Rehearse the path three times and keep each run within the planned time.

## Start guide

### First: learn the project in five minutes

Read the mission and timeline in the [team README](../README.md). Then ask each teammate to show you their part:

- Tyeki shows where the sensor is and how to make a safe test change.
- Budi shows where the readings and explanations come from.
- Ralph shows how the wrist screen receives and displays a status.

You should be able to say: “The backpack senses the area, the Pi decides whether something changed, and the wrist screen warns the person.”

### Next: create your test sheet

Use one row for each test:

| Test | Steps | Expected | Actual | Pass? | Owner |
| --- | --- | --- | --- | --- | --- |
| Normal state | Start system; wait for learning to finish | Screen says `NORMAL` |  |  |  |
| Alert state | Use Tyeki's approved safe trigger | Screen changes and explains why |  |  |  |
| Backpack off | Turn off only the Pi | Screen says `OFFLINE` |  |  |  |
| Internet off | Disconnect internet, keep local link | Sensing and local explanation continue |  |  |  |

Never invent a test result. If something uses sample data, label it “simulated.”

### When you find a problem

Write a bug report like this:

> At 3:10 PM, using build 12, I turned off the Pi. After 15 seconds the wrist screen still said NORMAL. I expected OFFLINE. Ralph and Budi should check this.

This is more useful than “the screen is broken” because your teammates can repeat it.

### Finally: prepare the demo

1. Put the devices, charger, and safe test item in their marked places.
2. Follow Budi's startup guide without skipping a step.
3. Wait for `LEARNING` to become `NORMAL`.
4. Show the live reading, then use the safe trigger.
5. Point to the new state and read its short explanation.
6. Show offline-first behavior by removing internet access while keeping the local connection.
7. End with what ASTRA could become after the hackathon.

## Expectations

- Use plain words that a visitor can understand on the first try.
- Test what the instructions say, even if you know a shortcut.
- Tell the team quickly when a test fails. A failed test is useful information.
- Ask before unplugging, heating, moving, or changing any hardware.
- Keep evidence honest: clearly label live, cached, and simulated data.
- Stop polishing slides or colors when a required test is failing.

## Deliverables

- Approved wording for all five wrist states.
- Completed test sheet with repeatable bug notes.
- A short demo script and a backup demo path.
- Organized screenshots/photos/video of the working system.
- Three timed rehearsal records.
- Final list of what the project does, what is simulated, and what comes next.

## Milestones

| Deadline | Your result |
| --- | --- |
| T+1 | First screen words and one-sentence mission story |
| T+4 | Test sheet and demo outline; first wrist screen reviewed |
| T+7 | First end-to-end test and clear bug list |
| T+10 | Alert and offline cases tested; screenshots started |
| T+12 | Exact demo path saved after two successful runs |
| T+18 | Presentation assets ready; backup path tested |
| T+21 | Three rehearsals complete and timed |

## Dependencies and interfaces

- **With Ralph:** you give him approved words and notes about readability. He gives you a screen that shows every state. The handoff is complete when you can identify the state from a quick glance.
- **With Tyeki:** Tyeki gives you the safe anomaly trigger and handling rules. You give feedback on comfort and how the hardware looks during the demo. The handoff is complete when you can perform the trigger safely from written steps.
- **With Budi:** Budi gives you the startup guide, state meanings, and known-good build. You give Budi repeatable test failures and the final demo order. The handoff is complete when you run the whole demo without help.

## Stretch goals

- Create a simple paper wrist-screen mockup for future screens.
- Add a short user scenario with an astronaut name and mission task.
- Make a labeled project photo or simple architecture picture for the submission.
- Run a five-minute test with someone outside the team and record what confused them.
- Prepare a 30-second version of the pitch in case presentation time is cut.

## Done checklist

- [ ] I can explain ASTRA in one clear sentence.
- [ ] Every screen state has short, approved wording.
- [ ] I tested normal, alert, offline-backpack, offline-internet, and restart cases.
- [ ] Each failed test includes steps, expected result, and actual result.
- [ ] I know and follow the safe anomaly-trigger steps.
- [ ] Live and simulated data are labeled correctly.
- [ ] Photos and video are readable and organized.
- [ ] The backup demo path is ready.
- [ ] Three rehearsals finished within the time limit.
- [ ] I can run the final demo without someone whispering the next step.
