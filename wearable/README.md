# ASTRA CYD Wrist Terminal

This PlatformIO starter targets the team's ESP32-2432S028R 2.8-inch "Cheap
Yellow Display." Its display pins, ILI9341 driver, 40 MHz SPI clock, backlight
pin, and landscape rotation match the known-working sibling CYD workspace. It
connects to local Wi-Fi, polls the Pi once per second, and shows `LEARNING`,
`NORMAL`, `CAUTION`, `ALERT`, or `OFFLINE` with text, symbols, and color.

## Before connecting hardware

Confirm the board revision, screen driver, resolution, backlight pin, and SPI
pins printed on or documented for the exact unit. The defaults in
`platformio.ini` are common but are not universal.

## Configure

```bash
cd wearable
cp include/secrets.example.h include/secrets.h
```

Edit `include/secrets.h` with the local network credentials. The file is ignored
by Git. `include/app_config.h` currently points to the Pi at `10.0.201.67`; update
that value after a network or DHCP address change. Set `ASTRA_ASTRONAUT_ID` to the astronaut assigned to that
physical wearable. The default roster IDs are `astronaut-1`, `astronaut-2`,
`astronaut-3`, and `astronaut-4`; every wearable must have the correct unique
ID for its wearer.

## Build, upload, and monitor

```bash
pio run
pio run --target upload
pio device monitor
```

The firmware compiles without `secrets.h` by using obvious placeholder values,
but it will not connect until real local credentials are supplied. Serial output
reports Wi-Fi, HTTP, and JSON failures without printing the password.

## Expected behavior

- A valid recent payload displays the Pi's state and readings.
- Missing sensor fields display as `--` and do not reset the device.
- An invalid payload, stopped Pi service, lost Wi-Fi connection, or unchanged
  timestamp beyond the stale timeout displays `OFFLINE`.
- A valid response clears `OFFLINE` automatically.
- The wearable polls only its configured astronaut inbox. A new Central Station
  message takes over the screen for ten seconds, then the normal status display
  returns.
- After receiving a message, the wearable acknowledges it to the Pi. Central
  Station then changes its delivery badge from `QUEUED` to `DELIVERED`.
- Messages remain queued in SQLite while the addressed wearable is offline.

This is an engineering prototype, not a medical or flight-certified safety
display.
