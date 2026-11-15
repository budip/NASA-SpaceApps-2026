# Astra for ESP32-2432S028

Native landscape dashboard for the 2.8-inch ESP32-2432S028 display. Astra uses clearly labeled simulated values for heart rate, oxygen, body temperature, and blood pressure. It polls the configured HTTP status API for suit pressure, suit temperature, compass, and gyroscope data. On first boot, tap the four calibration targets; Astra stores the touchscreen calibration. To recalibrate later, touch **MENU**, then **CALIBRATE TOUCH**. Touch **MENU** and then **SET UP WI-FI + RASPBERRY PI** to open the setup portal.

## Configure and flash

1. Install [Visual Studio Code](https://code.visualstudio.com/) and the PlatformIO IDE extension.
2. Open this folder in PlatformIO. Its library dependencies are listed in `platformio.ini`.
3. Connect the board over USB and select its serial port in PlatformIO.
4. Build and upload the `esp32-2432s028` environment.
5. The screen starts in demo mode. When ready to configure connectivity, touch **MENU**, then **SET UP WI-FI + RASPBERRY PI**. Join the `Astra-Setup` Wi-Fi network from a phone or computer and open `http://192.168.4.1`. Enter Wi-Fi credentials and the status API host, HTTP port, and path. The default API is `10.0.201.67:8000/api/v1/status`. The setup portal stays open until you save the form; after saving, Astra joins the configured Wi-Fi and closes its setup network.
6. To customize the screen on your computer, open `tools/astra-designer.html` in a browser. It previews Vitals, Navigation, and Suit Monitor. Set page titles, choose which pages and readings appear, change colors and card order, then export `astra_design.h` into `src` and upload again.
7. On the device, open **MENU → CUSTOMIZE DISPLAY** to cycle themes or turn Navigation on or off. Open **SUIT DISPLAY OPTIONS** there to show or hide suit pressure and temperature. Choices save automatically. Swipe left from the dashboard to open **Navigation**; swipe right from the dashboard to open **Suit Monitor**. Swipe left on Suit Monitor to return. Tap any vital card or Suit Monitor reading to view its rolling history graph and average. Astra keeps up to 60 samples per reading in memory; history starts fresh after reboot.

## Status API fields

The ESP32 polls the configured HTTP status endpoint once per second. It reads `sensors.pressure_hpa` and `sensors.temperature_c` for the Suit Monitor, and `sensors.orientation_deg.yaw` plus `sensors.gyroscope_rps` for Navigation. Heart rate, oxygen, body temperature, and blood pressure remain simulated. Central Station messages are polled separately from `/api/v1/messages`.

The project targets the common ESP32-2432S028 CYD revision with an ILI9341 display, TFT SPI pins 12/13/14/15/2, and backlight on GPIO 21. Board revisions can differ; if the screen stays blank, check the exact PCB revision and its pinout before changing the driver settings.

## Status API format

The default endpoint is `http://10.0.201.67:8000/api/v1/status`. It should return JSON like:

```json
{"heading":248,"gx":0.04,"gy":-0.08,"gz":0.12}
```

Navigation uses `orientation_deg.yaw` and `gyroscope_rps` from the response; gyro values are converted to degrees per second. Simulated clinical vital values must not be used for care decisions; Astra does not calculate clinical status or raise medical alarms.

Heart rate, oxygen, body temperature, and blood pressure always use simulated demo readings. The ESP32 reads suit pressure and suit temperature from the HTTP status response. It also reads `orientation_deg.yaw` for compass heading and `gyroscope_rps` for gyro values, converting radians per second to degrees per second.

```json
{"sensors":{"temperature_c":35.194,"pressure_hpa":982.101,"gyroscope_rps":{"x":0.0022,"y":-0.0005,"z":-0.0006},"orientation_deg":{"yaw":260.9328}}}
```
