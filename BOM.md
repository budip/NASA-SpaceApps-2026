# ASTRA Hardware Bill of Materials

Revision: 2026-11-13

This BOM covers one complete, offline-capable ASTRA demonstration: a Raspberry
Pi 3 and Sense HAT in a backpack, an ESP32-2432S028R CYD wrist terminal, a
private local Wi-Fi network, independent wearable power, a safe anomaly trigger,
and the equipment needed to build, recover, and rehearse the system.

## Procurement codes

- **M — Minimum:** required for the complete demonstration.
- **R — Reliability:** strongly recommended for recovery during the event.
- **O — Optional:** useful after the minimum path works; not required to start.

The quantities are for one working demo unit. Items marked as spares are in
addition to the installed item. Record the exact model and owner before the
hardware leaves the team table.

## Confirm before ordering

- [ ] Confirm whether the Raspberry Pi is a 3 Model B or 3 Model B+.
- [ ] Confirm the Pi power connector is Micro-USB.
- [ ] Confirm the CYD label is ESP32-2432S028 or ESP32-2432S028R and inspect its
      USB connector. The team's known firmware target expects a Micro-USB CYD.
- [ ] Confirm the Sense HAT includes four standoffs and mounting screws.
- [ ] Confirm each power bank's output connector and each bank/router charging
      connector before buying cables.
- [ ] Confirm the travel router can create a 2.4 GHz LAN without internet.

Do not order a cable based only on a product photograph. USB-C and Micro-USB
versions of similar products are commonly sold under nearly identical names.

## 1. Core computing and sensing

| Priority | Qty | Item | Minimum specification | Purpose / acceptance check | Have |
| --- | ---: | --- | --- | --- | --- |
| M | 1 | Raspberry Pi 3 Model B or B+ | 40-pin GPIO, onboard Wi-Fi, Micro-USB power | Runs sensing, SQLite, anomaly detection, and FastAPI | [ ] |
| M | 1 | Raspberry Pi Sense HAT | Genuine or fully compatible HAT with temperature, humidity, pressure, orientation, and motion sensors | Mounts firmly on the 40-pin header; every required sensor returns plausible data | [ ] |
| M | 1 | ESP32-2432S028R CYD | 2.8-inch 320×240 ILI9341-compatible display, ESP32, USB programming interface | Builds with `wearable/platformio.ini`; screen, backlight, Wi-Fi, and USB serial work | [ ] |
| M | 1 | Primary microSD card | 32 GB or larger, Class 10, application class A1 or A2, reputable supplier | Holds Raspberry Pi OS and ASTRA; passes a full write/verify | [ ] |
| R | 1 | Spare microSD card | Same or better than primary; pre-imaged and labeled | Restores the Pi without waiting to re-image the failed card | [ ] |
| M | 1 | USB microSD card reader | Supports microSDHC/microSDXC and the team's laptop | Images and recovers the Pi card | [ ] |
| M | 1 set | Pi/Sense HAT mounting hardware | Four M2.5 standoffs, matching screws, and nylon washers; use the hardware supplied with the HAT when suitable | HAT is level, cannot short against the Pi, and does not work loose | [ ] |
| R | 1 | Low-profile Pi heatsink set | Electrically nonconductive adhesive; clears the Sense HAT and enclosure | Reduces Pi heat while preserving airflow; must not touch the HAT | [ ] |
| O | 1 | DS3231-class RTC kit | 3.3 V-safe I²C module, battery holder, CR2032 from a reputable supplier, and safe mounting | Preserves accurate time after an offline cold boot; verify coexistence with Sense HAT I²C addresses first | [ ] |

The Sense HAT is powered from the Pi and needs no separate power supply. It is
compatible with Raspberry Pi computers that have a 40-pin GPIO header and
provides the required environmental and motion sensors.

## 2. Power and batteries

| Priority | Qty | Item | Minimum specification | Purpose / acceptance check | Have |
| --- | ---: | --- | --- | --- | --- |
| M | 1 | Raspberry Pi bench power supply | Regulated 5.1 V, 2.5 A, 12.5 W, Micro-USB; regional safety certification; preferably the official supply | Reliable development and recovery power with no undervoltage warning | [ ] |
| M | 1 | Backpack power bank | Enclosed, protected, safety-certified; 10,000 mAh nominal or larger; one output sustains regulated 5 V at 2.5 A; physical power switch preferred | Runs Pi + Sense HAT for the full rehearsal window without undervoltage or auto-shutoff | [ ] |
| M | 1 | Wrist-terminal power bank | Enclosed, protected, safety-certified; 3,000–5,000 mAh nominal; regulated 5 V at 1 A or more; supports low-current loads without auto-shutoff | Runs the CYD independently for the full rehearsal window | [ ] |
| M | 1 | Router power source | Internal battery, manufacturer wall adapter, or dedicated protected USB bank sized to the selected router | Keeps the local LAN running when venue internet is removed | [ ] |
| R | 1 | Spare protected power bank | 10,000 mAh or larger, regulated 5 V at 2.5 A on one port | Replaces either failed wearable supply after verifying connector/output | [ ] |
| M | 1 | Multi-port charging adapter | Safety-certified; enough independently rated outputs to recharge both banks and the router; use manufacturer adapters when required | Recharges all batteries without sharing the Pi's runtime output | [ ] |
| M | 1 | Surge-protected power strip | At least four outlets, grounded plug, region-appropriate rating, 2 m or longer lead | Single labeled charging and bench-power point | [ ] |
| R | 1 | Inline USB voltage/current meter | Covers 5 V USB-A and/or USB-C used by the selected hardware | Verifies Pi voltage at load and measures real runtime current | [ ] |

Raspberry Pi specifies 5 V at 2.5 A for all Pi 3 models. Treat that as the
minimum available at the Pi connector, not merely the rating printed on a bank.
Voltage loss in thin or long cables can still trigger undervoltage. Avoid bare
LiPo cells and unprotected battery boards for the wearable prototype.

## 3. Complete cable list

| ID | Priority | Qty | Cable / adapter | Required details | Connection and role | Have |
| --- | --- | ---: | --- | --- | --- | --- |
| C1 | M | 1 | Short Pi battery cable | USB-A to Micro-USB, 30–50 cm, 18–20 AWG power conductors, rated at least 2.5 A | Backpack bank → Raspberry Pi power input | [ ] |
| C2 | R | 1 | Spare Pi power cable | Same specification as C1 | Immediate replacement for C1 | [ ] |
| C3 | M | 1 | Short CYD wearable cable | Power-and-data cable matching the actual CYD USB port, expected USB-A to Micro-USB, 30–50 cm, flexible or right-angle if strain is lower | Wrist bank → CYD | [ ] |
| C4 | M | 1 | CYD programming cable | Data-capable cable matching laptop and CYD, 1–1.5 m; not charge-only | Development laptop → CYD for upload and serial monitor | [ ] |
| C5 | R | 1 | Spare USB data cable | Data-capable equivalent of C4 | Recovery if C3/C4 fails | [ ] |
| C6 | M | 1 | Backpack bank charging cable | Connector required by the selected bank; prefer the manufacturer's cable | Charger → backpack bank | [ ] |
| C7 | M | 1 | Wrist bank charging cable | Connector required by the selected bank; prefer the manufacturer's cable | Charger → wrist bank | [ ] |
| C8 | M | 1 | Router power/charging cable | Connector and current rating required by selected router | Router power source → travel router | [ ] |
| C9 | M | 1 | Ethernet patch cable | Cat5e or Cat6, 1–2 m | Pi → travel router for setup or Wi-Fi recovery | [ ] |
| C10 | R | 1 | Full-size HDMI cable | HDMI male-to-male, 1–2 m | Pi → setup/recovery display | [ ] |
| C11 | R | 1 | Laptop USB adapter | USB-C to USB-A adapter or hub only if the development laptop lacks the port required by C4/card reader | Laptop → programmer/card reader | [ ] |
| C12 | R | 1 | Short USB extension | USB-A male-to-female, rated for the actual load; do not use for Pi power unless measured under load | Strain relief or bench access only | [ ] |

Label both ends of every cable with its ID. Before the event, verify C3, C4, and
C5 can upload firmware; many inexpensive USB cables provide power but no data.

## 4. Local network

| Priority | Qty | Item | Minimum specification | Purpose / acceptance check | Have |
| --- | ---: | --- | --- | --- | --- |
| M | 1 | Travel router | 2.4 GHz 802.11n access point, DHCP, saved configuration, LAN works without internet, USB or internal-battery power | Pi and CYD reconnect automatically after router power-cycle; internet can be removed without breaking LAN traffic | [ ] |
| R | 1 | Printed network/device label card | Device names, non-secret IP plan, cable IDs, and startup order; no password | Lets the team identify devices without exposing credentials | [ ] |
| O | 1 | USB Wi-Fi adapter for recovery | Raspberry Pi OS-compatible, 2.4 GHz | Used only if the Pi's onboard radio fails; not part of the normal build | [ ] |

Use a private event SSID and store its password only in ignored local
configuration. Do not print the password on the public label card, repository,
screenshots, or presentation.

## 5. Backpack, wrist mount, and mechanical hardware

| Priority | Qty | Item | Minimum specification | Purpose / acceptance check | Have |
| --- | ---: | --- | --- | --- | --- |
| M | 1 | Backpack | Lightweight, ventilated, padded, with a compartment that separates electronics from the wearer | Carries Pi, battery, and cables without blocking airflow | [ ] |
| M | 1 | Pi + Sense HAT protective frame/enclosure | Nonconductive, ventilated, GPIO/HAT-compatible, with access to Micro-USB, HDMI, Ethernet, and microSD | Prevents shorts and impact while keeping the HAT exposed to representative airflow | [ ] |
| M | 1 | Rigid mounting plate | 2–3 mm polycarbonate, ABS, or other nonconductive sheet, approximately 150 × 100 mm or sized after layout | Keeps the Pi assembly flat and supports strain relief | [ ] |
| M | 1 | CYD protective enclosure | Nonconductive, ventilated, with visible display and access to USB/reset; no sharp edges | Protects the wrist terminal without trapping heat or pressing the touchscreen | [ ] |
| M | 1 | Adjustable wrist/forearm strap | 20–25 mm hook-and-loop or elastic strap, sized for users, quick-release preferred | Holds CYD securely without restricting circulation | [ ] |
| M | 1 kit | Nylon fastener assortment | M2, M2.5, and M3 screws, nuts, washers, and standoffs | Select only after measuring board/enclosure holes; avoids metal shorts | [ ] |
| M | 1 pack | Industrial hook-and-loop strips | Sew-on or high-quality removable adhesive, at least 25 mm wide | Secures mounting plate and removable battery pouches | [ ] |
| M | 10 | Reusable cable ties | 100–150 mm, hook-and-loop preferred | Bundles cables without crushing insulation | [ ] |
| M | 10 | Adhesive cable anchors or P-clips | Sized for USB cables and compatible with mounting plate | Provides strain relief near every connector | [ ] |
| M | 1 m | Split cable sleeve or braided loom | Fits the backpack power/data bundle | Prevents snagging and abrasion | [ ] |
| M | 2 | Padded battery pouches | One backpack-sized and one wrist-bank-sized, ventilated and removable | Keeps hard battery edges away from the wearer; permits inspection | [ ] |
| M | 4 | Non-slip rubber or silicone feet | Adhesive or screw-mounted, heat tolerant | Maintains an airflow gap under the backpack mounting plate | [ ] |
| M | 1 roll | Gaffer tape | Residue-controlled, approximately 25–50 mm wide | Temporary cable routing and floor safety; never cover vents | [ ] |
| M | 1 pack | Writable equipment labels | Removable, high-contrast | Labels device owner, cable ID, live/simulated mode, and shutdown order | [ ] |
| R | 1 | Small compartment organizer | Hard-sided, labeled | Carries screws, card, adapters, and spares without loss | [ ] |

Do not place the Pi, Sense HAT, CYD, or power banks directly against skin. Do
not mount batteries where they are bent, crushed, or trapped without inspection
access.

## 6. Safe anomaly trigger and measurement

| Priority | Qty | Item | Minimum specification | Purpose / acceptance check | Have |
| --- | ---: | --- | --- | --- | --- |
| M | 1 | Guarded 5 V USB desk fan | Low-speed setting, stable base, enclosed blades, its own rated cable | Creates mild, repeatable airflow to cool the Pi-biased Sense HAT temperature without heat, liquid, or impact | [ ] |
| R | 1 | Manual folding fan | Lightweight, no sharp edges | Zero-power backup airflow trigger | [ ] |
| M | 1 | Reference thermometer/hygrometer | Digital room monitor with a stable display; record its stated accuracy | Checks whether Sense HAT readings are plausible and documents ambient conditions | [ ] |
| R | 1 | Digital multimeter | CAT-rated from a reputable manufacturer, insulated probes | Checks continuity and supply voltage; not used on exposed mains | [ ] |
| R | 1 | Nonconductive ruler/tape measure | Metric markings | Fixes the fan distance so three anomaly trials are repeatable | [ ] |

The approved trigger must use a written distance, fan setting, and duration.
Never use flame, a heat gun, ice, compressed refrigerant, liquid, damaged cells,
or unsafe acceleration near the prototype.

## 7. Setup and recovery equipment

These can be team-owned rather than purchased, but they must be physically
present at integration and the final demo.

| Priority | Qty | Item | Minimum specification | Purpose / acceptance check | Have |
| --- | ---: | --- | --- | --- | --- |
| M | 1 | Central-station/development laptop | Modern browser, 2.4 GHz Wi-Fi, and ability to run Git, Python, Raspberry Pi Imager, PlatformIO, serial monitor, and SSH | Opens the Pi-hosted dashboard, builds both projects, and can re-image the Pi | [ ] |
| M | 1 | Laptop charger | Manufacturer-rated adapter and region-appropriate wall lead | Keeps the central station operating through rehearsals and the final demo | [ ] |
| R | 1 | HDMI display or television | Full-size HDMI input compatible with C10 | Recovers a Pi that cannot be reached over the network | [ ] |
| R | 1 | USB keyboard | Compatible with Raspberry Pi | Local recovery and login | [ ] |
| R | 1 | USB mouse | Compatible with Raspberry Pi; not required for Raspberry Pi OS Lite | Local graphical recovery | [ ] |
| R | 1 | Small powered USB hub | Its own certified supply; only if laptop/Pi port count requires it | Connects setup peripherals without overloading Pi USB | [ ] |
| R | 1 | USB flash drive | 16 GB or larger, labeled | Carries the known-good Pi image, firmware binary, configuration examples, and offline installers | [ ] |
| M | 1 set | Precision screwdriver set | Phillips and small metric bits matching enclosures | Assembly without stripped hardware | [ ] |
| R | 1 | ESD work mat and wrist strap | Grounded according to manufacturer instructions | Safe bench assembly; never connect to unknown ground points | [ ] |
| R | 1 | Small flush cutters and needle-nose pliers | Insulated handles | Cable-tie and mounting work; keep away from powered circuits | [ ] |
| M | 1 | Transport case/bin | Padded, closable, labeled | Moves all devices and prevents loose batteries or boards | [ ] |

## 8. Critical spares summary

At minimum, bring these spares even if the team does not buy duplicate compute
boards:

- [ ] One pre-imaged microSD card;
- [ ] one Pi-rated Micro-USB power cable;
- [ ] one CYD-compatible data cable;
- [ ] one protected 5 V / 2.5 A-capable power bank;
- [ ] spare M2/M2.5/M3 nylon fasteners, washers, cable ties, and labels;
- [ ] an offline copy of the last known-good Pi image and CYD firmware binary.

If budget permits, the highest-value full-device spares are one additional CYD,
then one Raspberry Pi 3. A spare Sense HAT is lower priority after one unit has
passed the sensor and mounting tests.

## 9. Power and connection map

| Source | Cable | Consumer | Normal use |
| --- | --- | --- | --- |
| Backpack 5 V / 2.5 A power bank | C1 | Raspberry Pi 3; Pi powers Sense HAT through GPIO | Wearable demo |
| Wrist 5 V / 1 A-or-greater power bank | C3 | CYD wrist terminal | Wearable demo |
| Router battery or dedicated rated supply | C8 | Travel router | Private offline LAN |
| Official 5.1 V / 2.5 A Pi supply | Captive Micro-USB lead | Raspberry Pi 3 | Bench development and recovery |
| Certified multi-port charger | C6 and C7 | Power banks | Charging only, outside the worn enclosure |
| Development laptop | C4 | CYD | Firmware upload and serial diagnostics |
| Travel router LAN port | C9 | Raspberry Pi Ethernet | Network recovery or fixed bench link |

## 10. Receiving and readiness checks

Complete these checks before accepting the BOM as ready:

- [ ] Photograph each board label and record the exact revision and owner.
- [ ] Inspect every power bank for swelling, impact, damaged ports, or unusual
      heat; quarantine damaged units.
- [ ] Fully charge, then runtime-test each battery with its real consumer.
- [ ] Run the Pi under sensor and network load for at least 30 minutes with no
      undervoltage or thermal warning.
- [ ] Verify C3, C4, and C5 carry data, not only power.
- [ ] Verify the CYD boots, uploads, and reconnects from each intended cable and
      power bank.
- [ ] Verify the private LAN works with its internet/WAN connection removed.
- [ ] Verify the Sense HAT mounting, airflow, and warm-up behavior after it is
      installed in the backpack.
- [ ] Perform the written airflow trigger three times and record the result.
- [ ] Confirm no vent is covered and every worn cable has strain relief.
- [ ] Confirm the emergency shutdown order and label all power controls.
- [ ] Pack the spares, tools, known-good images, and charging equipment in the
      transport case.

## Reference specifications

- Raspberry Pi recommends **5 V at 2.5 A** and a **12.5 W Micro-USB supply** for
  Raspberry Pi 3 models: [Raspberry Pi getting-started documentation](https://www.raspberrypi.com/documentation/computers/getting-started.html) and
  [official 12.5 W Micro-USB supply](https://www.raspberrypi.com/products/micro-usb-power-supply/).
- Raspberry Pi recommends at least **32 GB** for a normal Raspberry Pi OS
  installation; official cards are A2/C10/U3/V30:
  [Raspberry Pi SD cards](https://www.raspberrypi.com/products/sd-cards/).
- The Sense HAT is powered by the Pi, uses its 40-pin header, and supplies the
  environmental and motion sensors used by ASTRA:
  [official Sense HAT product page](https://www.raspberrypi.com/products/sense-hat/).
- The team's CYD pin, driver, rotation, and display-clock assumptions are kept
  in [`wearable/platformio.ini`](wearable/platformio.ini) and
  [`wearable/README.md`](wearable/README.md).

