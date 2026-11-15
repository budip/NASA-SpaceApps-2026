#include <Arduino.h>
#include <WiFi.h>
#include <WiFiManager.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <SPI.h>
#include <Preferences.h>
#include <esp_system.h>
#include <time.h>
#include <sys/time.h>

// ESP32-2432S028 (common CYD revision), ILI9341 display.
#include <TFT_eSPI.h>
#include "astra_design.h"

TFT_eSPI tft;
WiFiManager wifiManager;
Preferences preferences;
static constexpr uint8_t TP_CLK = 25, TP_MOSI = 32, TP_MISO = 39, TP_CS = 33, TP_IRQ = 36;

uint16_t BG = ASTRA_BG, PANEL = ASTRA_PANEL, EDGE = ASTRA_EDGE;
uint16_t WHITE = ASTRA_TEXT, MUTED = ASTRA_MUTED, ACCENT = ASTRA_ACCENT;
static constexpr uint16_t HR_COLOR = 0x6E5D, SPO2_COLOR = 0x75DF, TEMP_COLOR = 0xF5A8,
                          BP_COLOR = 0xB5BF;
struct Reading {
  float hr = 72, spo2 = 98, temp = 36.8, sys = 118, dia = 76, suitPressure = 4.2, suitTemp = 22.0;
} reading;
char suitPressureUnit[10] = "";
struct NavigationReading {
  float heading = 248, gx = 0.04, gy = -0.08, gz = 0.12;
} navReading;
char piHost[64] = "10.0.201.67", piPort[8] = "8000", piPath[64] = "/api/v1/status";
constexpr char ASTRA_MESSAGES_PATH[] = "/api/v1/messages";
constexpr char ASTRA_ASTRONAUT_ID[] = "astronaut-1";
constexpr unsigned long ASTRA_MESSAGE_POLL_INTERVAL_MS = 1500;
constexpr unsigned long ASTRA_MESSAGE_DISPLAY_MS = 10000;
constexpr unsigned long ASTRA_MESSAGE_ACK_RETRY_MS = 2000;
constexpr size_t ASTRA_MESSAGE_TEXT_CAPACITY = 181;
static constexpr uint8_t HISTORY_SIZE = 60;
struct Sample {
  float a, b;
};
Sample history[6][HISTORY_SIZE];
uint8_t historyHead[6] = {0, 0, 0, 0, 0, 0}, historyCount[6] = {0, 0, 0, 0, 0, 0};
bool apiConnected = false, liveData = false, menuOpen = false, graphOpen = false;
bool vitalSourceSimulated = false;
uint8_t vitalLiveMask = 0;
struct CrewMessage {
  uint32_t id = 0;
  char priority[10] = "";
  char text[ASTRA_MESSAGE_TEXT_CAPACITY] = "";
  bool displayed = false;
};
CrewMessage activeCrewMessage;
bool crewMessageVisible = false, crewMessageAckPending = false;
uint32_t lastReceivedMessageId = 0;
uint32_t displayedMessageIds[16] = {};
uint8_t displayedMessageIdCount = 0, displayedMessageIdHead = 0;
uint32_t crewMessageDisplayStartedAt = 0, lastCrewMessagePollAt = 0, nextCrewAckRetryAt = 0;
bool calibrationActive = false, returnToMenuAfterCal = false, rawYForScreenX = true;
uint8_t selectedVital = 0;
bool graphReturnToSuit = false;
uint16_t touchXStart = 240, touchXEnd = 3860, touchYStart = 3800, touchYEnd = 180;
uint16_t calibrationRawX[4] = {0, 0, 0, 0}, calibrationRawY[4] = {0, 0, 0, 0};
uint8_t calibrationStep = 0;
uint32_t calibrationReadyAt = 0;
uint16_t lastAcceptedRawX = 0, lastAcceptedRawY = 0;
bool navigationPage = false, navigationLiveData = false, touchCurrentlyDown = false,
     swipeTracking = false, swipeConsumed = false;
bool customizePage = false, suitPage = false, suitCustomizePage = false,
     navigationEnabled = ASTRA_NAV_ENABLED;
bool suitPressureEnabled = ASTRA_SUIT_PRESSURE_ENABLED, suitTempEnabled = ASTRA_SUIT_TEMP_ENABLED;
bool suitPressureFromApi = false, suitTempFromApi = false;
int swipeStartX = 0, swipeStartY = 0;
uint16_t currentTouchRawX = 0, currentTouchRawY = 0;
uint8_t themeIndex = 0;
uint32_t lastHttpPoll = 0, lastData = 0, lastDemo = 0, lastTouch = 0;
uint8_t apiFailureCount = 0;
bool earthClockVisible = false;
uint32_t lastClockDraw = 0, lastClockSave = 0;
time_t lastDisplayedMinute = 0;

constexpr time_t MIN_VALID_EPOCH = 1735689600; // 2025-01-01 UTC
constexpr uint32_t CLOCK_SAVE_INTERVAL_MS = 900000; // limit flash writes to once per 15 minutes

uint16_t readTouchChannel(uint8_t command);
bool getTouchPress(uint16_t &rawX, uint16_t &rawY);
void refreshNavigationData();
void paintSuitMonitor();
void refreshSuitMonitorData();
void paintCrewMessage();
void pollCrewMessages();
void retryCrewMessageAcknowledgement();

void restoreSavedClock() {
  preferences.begin("astra", true);
  const int64_t savedEpoch = preferences.getLong64("clockEpoch", 0);
  preferences.end();
  if (savedEpoch >= MIN_VALID_EPOCH) {
    timeval savedTime = {(time_t)savedEpoch, 0};
    settimeofday(&savedTime, nullptr);
  }
}

void saveClockIfValid() {
  const time_t now = time(nullptr);
  if (now < MIN_VALID_EPOCH || millis() - lastClockSave < CLOCK_SAVE_INTERVAL_MS)
    return;
  lastClockSave = millis();
  preferences.begin("astra", false);
  preferences.putLong64("clockEpoch", (int64_t)now);
  preferences.end();
}

void drawEarthClock() {
  char timeText[8] = "--:--";
  char dateText[16] = "-- --- ----";
  const time_t now = time(nullptr);
  if (now >= MIN_VALID_EPOCH) {
    struct tm localTime;
    localtime_r(&now, &localTime);
    strftime(timeText, sizeof(timeText), "%H:%M", &localTime);
    strftime(dateText, sizeof(dateText), "%d %b %Y", &localTime);
  }
  tft.fillRect(154, 4, 105, 30, PANEL);
  tft.setTextColor(ACCENT, PANEL);
  tft.drawCentreString(timeText, 206, 5, 2);
  tft.setTextColor(MUTED, PANEL);
  tft.drawCentreString(dateText, 206, 22, 1);
  earthClockVisible = true;
  lastDisplayedMinute = now >= MIN_VALID_EPOCH ? now / 60 : 0;
}

void updateEarthClock() {
  saveClockIfValid();
  if (!earthClockVisible || millis() - lastClockDraw < 1000)
    return;
  lastClockDraw = millis();
  const time_t now = time(nullptr);
  const time_t minute = now >= MIN_VALID_EPOCH ? now / 60 : 0;
  if (minute != lastDisplayedMinute)
    drawEarthClock();
}

void configureHttp(HTTPClient &http, uint16_t timeoutMs) {
  http.useHTTP10(true);
  http.setConnectTimeout(timeoutMs);
  http.setTimeout(timeoutMs);
}

const char *resetReasonName(esp_reset_reason_t reason) {
  switch (reason) {
  case ESP_RST_POWERON:
    return "power-on";
  case ESP_RST_EXT:
    return "external reset";
  case ESP_RST_SW:
    return "software reset";
  case ESP_RST_PANIC:
    return "panic/crash";
  case ESP_RST_INT_WDT:
    return "interrupt watchdog";
  case ESP_RST_TASK_WDT:
    return "task watchdog";
  case ESP_RST_WDT:
    return "watchdog";
  case ESP_RST_DEEPSLEEP:
    return "deep sleep wake";
  case ESP_RST_BROWNOUT:
    return "brownout / low voltage";
  case ESP_RST_SDIO:
    return "SDIO reset";
  default:
    return "other/unknown";
  }
}

void recordSample() {
  const float a[6] = {reading.hr,  reading.spo2,         reading.temp,
                      reading.sys, reading.suitPressure, reading.suitTemp};
  const float b[6] = {0, 0, 0, reading.dia, 0, 0};
  for (uint8_t id = 0; id < 6; id++) {
    history[id][historyHead[id]] = {a[id], b[id]};
    historyHead[id] = (historyHead[id] + 1) % HISTORY_SIZE;
    if (historyCount[id] < HISTORY_SIZE)
      historyCount[id]++;
  }
}

Sample getSample(uint8_t id, uint8_t index) {
  uint8_t oldest = (historyHead[id] + HISTORY_SIZE - historyCount[id]) % HISTORY_SIZE;
  return history[id][(oldest + index) % HISTORY_SIZE];
}

void clearVitalHistory(uint8_t id) {
  if (id < 6) {
    historyHead[id] = 0;
    historyCount[id] = 0;
  }
}

bool selectedGraphIsLive() {
  if (selectedVital == 4 || selectedVital == 5)
    return apiConnected;
  return (vitalLiveMask & (1U << selectedVital)) != 0;
}

JsonVariant findVitalField(JsonDocument &doc, const char *key, const char *alias1 = nullptr,
                           const char *alias2 = nullptr) {
  JsonVariant value = doc["sensors"][key];
  if (value.isNull())
    value = doc[key];
  if (value.isNull())
    value = doc["biometrics"][key];
  if (value.isNull() && alias1) {
    value = doc["sensors"][alias1];
    if (value.isNull())
      value = doc[alias1];
  }
  if (value.isNull() && alias1)
    value = doc["biometrics"][alias1];
  if (value.isNull() && alias2) {
    value = doc["sensors"][alias2];
    if (value.isNull())
      value = doc[alias2];
    if (value.isNull())
      value = doc["biometrics"][alias2];
  }
  return value;
}

struct Theme {
  const char *name;
  uint16_t bg, panel, edge, text, muted, accent;
};
static constexpr uint8_t THEME_COUNT = 6;
const Theme THEMES[THEME_COUNT] = {
    {"Astra classic", ASTRA_BG, ASTRA_PANEL, ASTRA_EDGE, ASTRA_TEXT, ASTRA_MUTED, ASTRA_ACCENT},
    {"Deep teal", 0x08F2, 0x1120, 0x222D, 0xEF7D, 0x8D13, 0x6E5D},
    {"Soft light", 0xFFFF, 0xE71C, 0xBDF7, 0x1082, 0x5AEB, 0x0572},
    {"Nebula", 0x100F, 0x2115, 0x4A59, 0xF7DE, 0xB3B5, 0xD2FF},
    {"Mars", 0x2104, 0x3987, 0x7A08, 0xFFDF, 0xC5D6, 0xFC60},
    {"Aurora", 0x0028, 0x084B, 0x1D14, 0xEFFF, 0x6EDB, 0x4FE6}};

void applyTheme() {
  themeIndex %= THEME_COUNT;
  const Theme &t = THEMES[themeIndex];
  BG = t.bg;
  PANEL = t.panel;
  EDGE = t.edge;
  WHITE = t.text;
  MUTED = t.muted;
  ACCENT = t.accent;
}

void saveCustomization() {
  preferences.begin("astra", false);
  preferences.putUChar("theme", themeIndex);
  preferences.putBool("navOn", navigationEnabled);
  preferences.putBool("suitPOn", suitPressureEnabled);
  preferences.putBool("suitTOn", suitTempEnabled);
  preferences.end();
}

void loadCustomization() {
  preferences.begin("astra", true);
  themeIndex = preferences.getUChar("theme", 0) % THEME_COUNT;
  navigationEnabled = preferences.getBool("navOn", ASTRA_NAV_ENABLED);
  suitPressureEnabled = preferences.getBool("suitPOn", ASTRA_SUIT_PRESSURE_ENABLED);
  suitTempEnabled = preferences.getBool("suitTOn", ASTRA_SUIT_TEMP_ENABLED);
  preferences.end();
  applyTheme();
}

void drawSpaceStars(int x1 = 0, int y1 = 0, int x2 = 320, int y2 = 240) {
  const int sx[23] = {18,  42,  76,  106, 132, 205, 239, 286, 300, 28,  61, 92,
                      121, 189, 221, 270, 309, 14,  51,  101, 232, 254, 291};
  const int sy[23] = {22, 48,  17, 57,  31,  26,  51,  20,  62,  102, 89, 120,
                      94, 111, 82, 103, 131, 174, 202, 160, 185, 216, 203};
  for (uint8_t i = 0; i < 23; i++)
    if (sx[i] >= x1 && sx[i] < x2 && sy[i] >= y1 && sy[i] < y2)
      tft.drawPixel(sx[i], sy[i], i % 4 == 0 ? WHITE : MUTED);
}

void drawBootA(int x, int y, int w, int h, uint8_t phase, bool engineOn) {
  const uint16_t bootBg = 0x0008;
  int cx = x + w / 2;
  tft.fillTriangle(cx, y, x, y + h, x + w, y + h, ACCENT);
  tft.fillTriangle(cx, y + h / 3, x + w / 4, y + (h * 2) / 3, x + (w * 3) / 4, y + (h * 2) / 3,
                   bootBg);
  int barY = y + (h * 2) / 3;
  tft.fillRect(x + w / 4, barY, max(2, w / 2), max(2, h / 9), WHITE);
  if (engineOn) {
    uint16_t flame = phase % 3 == 0 ? 0xFFE0 : (phase % 3 == 1 ? 0xFD20 : 0xF800);
    tft.fillTriangle(x + w / 3, y + h, x + (w * 2) / 3, y + h, cx, y + h + 4 + (phase % 2) * 2,
                     flame);
  }
}

void playBootAnimation() {
  const uint16_t bootBg = 0x0008;
  const char *word = "ASTRA";
  const int wordY = 102;
  int aWidth = tft.textWidth("A", 4), wordWidth = tft.textWidth(word, 4),
      shipX = (320 - wordWidth) / 2, shipY = wordY;
  int shipH = tft.fontHeight(4);
  shipH = constrain(shipH, 20, 32);
  aWidth = constrain(aWidth, 13, 24);
  tft.fillScreen(bootBg);
  drawSpaceStars();
  tft.drawCircle(267, 77, 25, EDGE);
  tft.drawCircle(267, 77, 20, MUTED);
  tft.drawCircle(267, 77, 14, EDGE);
  tft.drawLine(241, 77, 293, 77, EDGE);
  tft.drawLine(267, 51, 267, 103, EDGE);
  tft.setTextColor(ACCENT, bootBg);
  tft.drawString("STRA", shipX + aWidth, wordY, 4);
  int previousY = -100;
  const uint8_t descentSteps = 34;
  for (uint8_t step = 0; step <= descentSteps; step++) {
    int y = -shipH + (int)(shipY + shipH) * step / descentSteps;
    if (previousY > -90) {
      int clearTop = max(0, previousY - 2), clearBottom = min(240, previousY + shipH + 9);
      if (clearBottom > clearTop) {
        tft.fillRect(shipX, clearTop, aWidth, clearBottom - clearTop, bootBg);
        drawSpaceStars(shipX, clearTop, shipX + aWidth, clearBottom);
      }
    }
    drawBootA(shipX, y, aWidth, shipH, step, step < descentSteps);
    previousY = y;
    delay(32);
  }
  tft.setTextColor(WHITE, bootBg);
  tft.drawCentreString("VITALS  ·  SUIT  ·  NAVIGATION", 160, 145, 2);
  tft.drawRoundRect(31, 180, 258, 13, 6, EDGE);
  tft.setTextColor(MUTED, bootBg);
  tft.drawCentreString("SYSTEMS INITIALIZING", 160, 202, 1);
  for (uint8_t frame = 0; frame <= 24; frame++) {
    int fillWidth = (252 * frame) / 24;
    tft.fillRoundRect(34, 183, 252, 7, 3, 0x18E3);
    if (fillWidth > 0)
      tft.fillRoundRect(34, 183, fillWidth, 7, 3, ACCENT);
    if (frame == 24) {
      tft.fillRect(52, 198, 216, 15, bootBg);
      tft.setTextColor(ACCENT, bootBg);
      tft.drawCentreString("READY FOR FLIGHT", 160, 202, 1);
    }
    delay(38);
  }
  delay(180);
}

void drawHeader() {
  earthClockVisible = false;
  tft.fillRect(0, 0, 320, 38, PANEL);
  tft.setTextColor(ACCENT, PANEL);
  tft.drawString(ASTRA_TITLE, 12, 11, 2);
  tft.fillRoundRect(264, 5, 47, 27, 6, EDGE);
  tft.setTextColor(WHITE, EDGE);
  tft.drawCentreString("MENU", 287, 12, 1);
  drawEarthClock();
  tft.drawFastHLine(0, 38, 320, EDGE);
  tft.fillRect(0, 39, 320, 24, BG);
  const char *label =
      liveData
          ? (vitalSourceSimulated ? "PI DATA · SIMULATED"
                                  : (vitalLiveMask == 0x0F ? "LIVE DATA" : "LIVE · MIXED VITALS"))
          : (apiConnected ? "DEMO · API ONLINE" : "DEMO DATA");
  uint16_t status = liveData && !vitalSourceSimulated ? ACCENT : 0xF5A8;
  tft.fillCircle(14, 53, 4, status);
  tft.setTextColor(status, BG);
  tft.drawString(label, 24, 47, 2);
  tft.setTextColor(MUTED, BG);
  tft.drawRightString(WiFi.isConnected() ? WiFi.localIP().toString() : "Wi-Fi not set", 307, 48, 1);
}

uint16_t vitalValueColor(uint8_t id, uint16_t normalColor) {
  if (id >= 4 || (!vitalSourceSimulated && (vitalLiveMask & (1U << id))))
    return normalColor;

  float value = NAN;
  bool warning = false, critical = false;
  switch (id) {
  case 0:
    value = reading.hr;
    critical = value <= 40 || value >= 131;
    warning = value <= 50 || (value >= 91 && value <= 130);
    break;
  case 1:
    value = reading.spo2;
    critical = value <= 91;
    warning = value >= 92 && value <= 95;
    break;
  case 2:
    value = reading.temp;
    critical = value <= 35.0f;
    warning = (value > 35.0f && value <= 36.0f) || value >= 38.1f;
    break;
  case 3:
    value = reading.sys;
    critical = value <= 90 || value >= 220;
    warning = value >= 91 && value <= 110;
    break;
  }
  if (isnan(value))
    return normalColor;
  if (critical)
    return 0xF800; // red
  if (warning)
    return 0xFFE0; // yellow
  return normalColor;
}

// Suit limits are demo-display cues based on the NASA values discussed with
// the user; they are not certified alarms. Pressure thresholds use hPa.
uint16_t suitPressureValueColor(uint16_t normalColor) {
  if (suitPressureFromApi || isnan(reading.suitPressure))
    return normalColor;
  const float pressureHpa = suitPressureUnit[0] == 'h'
                                ? reading.suitPressure
                                : reading.suitPressure * 68.9476f; // demo value is psi
  if (pressureHpa <= 248.0f || pressureHpa >= 455.0f)
    return 0xF800; // red: critical low/high
  if (pressureHpa < 276.0f || pressureHpa > 365.0f)
    return 0xFFE0; // yellow: warning low/high
  return normalColor;
}

uint16_t suitTemperatureValueColor(uint16_t normalColor) {
  if (suitTempFromApi || isnan(reading.suitTemp))
    return normalColor;
  const float temperatureC = reading.suitTemp;
  if (temperatureC <= 0.0f || temperatureC >= 49.0f)
    return 0xF800; // red: tissue-damage limits
  if (temperatureC < 20.0f || temperatureC > 30.0f)
    return 0xFFE0; // yellow: outside the cited suit-air comfort envelope
  return normalColor;
}

void metricCard(int x, int y, int w, int h, const char *title, const char *unit, float value,
                int decimals, uint16_t accent, uint8_t vitalId) {
  tft.fillRoundRect(x, y, w, h, ASTRA_CARD_RADIUS, PANEL);
  tft.drawRoundRect(x, y, w, h, ASTRA_CARD_RADIUS, EDGE);
  tft.fillRoundRect(x + 8, y + 9, 3, h - 18, 2, accent);
  tft.setTextColor(MUTED, PANEL);
  tft.drawString(title, x + 18, y + 11, 2);
  tft.setTextColor(accent, PANEL);
  tft.drawString(unit, x + w - 37, y + 12, 1);
  char buf[18];
  dtostrf(value, 0, decimals, buf);
  tft.setTextColor(vitalValueColor(vitalId, WHITE), PANEL);
  tft.drawString(buf, x + 18, y + 38, 4);
}

void drawVital(int id, int x, int y) {
  if (id == 0)
    metricCard(x, y, 145, 74, "HEART RATE", "BPM", reading.hr, 0, HR_COLOR, id);
  else if (id == 1)
    metricCard(x, y, 145, 74, "OXYGEN", "SpO2", reading.spo2, 0, SPO2_COLOR, id);
  else if (id == 2)
    metricCard(x, y, 145, 74, "TEMPERATURE", "C", reading.temp, 1, TEMP_COLOR, id);
  else {
    tft.fillRoundRect(x, y, 145, 74, ASTRA_CARD_RADIUS, PANEL);
    tft.drawRoundRect(x, y, 145, 74, ASTRA_CARD_RADIUS, EDGE);
    tft.fillRoundRect(x + 8, y + 9, 3, 56, 2, BP_COLOR);
    tft.setTextColor(MUTED, PANEL);
    tft.drawString("BLOOD PRESSURE", x + 18, y + 11, 1);
    tft.setTextColor(BP_COLOR, PANEL);
    tft.drawString("mmHg", x + 108, y + 12, 1);
    char bp[20];
    snprintf(bp, sizeof(bp), "%.0f / %.0f", reading.sys, reading.dia);
    tft.setTextColor(vitalValueColor(id, WHITE), PANEL);
    tft.drawString(bp, x + 18, y + 38, 4);
  }
}

void drawVitalValue(int id, int x, int y) {
  tft.fillRect(x + 16, y + 34, 122, 35, PANEL);
  char buf[20];
  uint16_t normalColor = id == 0   ? HR_COLOR
                         : id == 1 ? SPO2_COLOR
                         : id == 2 ? TEMP_COLOR
                                   : WHITE;
  tft.setTextColor(vitalValueColor(id, normalColor), PANEL);
  if (id == 0) {
    dtostrf(reading.hr, 0, 0, buf);
    tft.drawString(buf, x + 18, y + 38, 4);
  } else if (id == 1) {
    dtostrf(reading.spo2, 0, 0, buf);
    tft.drawString(buf, x + 18, y + 38, 4);
  } else if (id == 2) {
    dtostrf(reading.temp, 0, 1, buf);
    tft.drawString(buf, x + 18, y + 38, 4);
  } else {
    snprintf(buf, sizeof(buf), "%.0f / %.0f", reading.sys, reading.dia);
    tft.drawString(buf, x + 18, y + 38, 4);
  }
}

void paintFooter() {
  if (!ASTRA_SHOW_FOOTER)
    return;
  tft.fillRect(0, 239, 320, 34, BG);
  tft.drawFastHLine(10, 239, 300, EDGE);
  tft.setTextColor(MUTED, BG);
  tft.drawString(liveData
                     ? (vitalSourceSimulated ? "PI BIOMETRICS · SIMULATED" : "RASPBERRY PI · LIVE")
                     : "SAMPLE READINGS · DEMO ONLY",
                 12, 250, 1);
  if (liveData) {
    uint32_t age = (millis() - lastData) / 1000;
    char ago[24];
    snprintf(ago, sizeof(ago), "Updated %lus ago", (unsigned long)age);
    tft.setTextColor(ACCENT, BG);
    tft.drawRightString(ago, 307, 250, 1);
  } else {
    tft.setTextColor(MUTED, BG);
    tft.drawRightString("Swipe left: Navigation", 307, 250, 1);
  }
}

void refreshValues() {
  const uint8_t order[4] = {ASTRA_ORDER_0, ASTRA_ORDER_1, ASTRA_ORDER_2, ASTRA_ORDER_3};
  const int xs[4] = {10, 165, 10, 165}, ys[4] = {68, 68, 153, 153};
  int pos = 0;
  for (uint8_t i = 0; i < 4; i++) {
    uint8_t id = order[i];
    if (id < 4 && (ASTRA_VISIBLE_MASK & (1 << id))) {
      drawVitalValue(id, xs[pos], ys[pos]);
      pos++;
    }
  }
}

const char *vitalName(uint8_t id) {
  const char *names[6] = {"HEART RATE",     "OXYGEN SATURATION", "TEMPERATURE",
                          "BLOOD PRESSURE", "SUIT PRESSURE",     "SUIT TEMPERATURE"};
  return names[id < 6 ? id : 0];
}

void drawGraphData() {
  const int boxX = 10, boxY = 70, boxW = 300, boxH = 112;
  tft.fillRoundRect(boxX, boxY, boxW, boxH, ASTRA_CARD_RADIUS, PANEL);
  tft.drawRoundRect(boxX, boxY, boxW, boxH, ASTRA_CARD_RADIUS, EDGE);
  const int left = 24, right = 296, top = 82, bottom = 161;
  for (int i = 0; i < 4; i++) {
    int gy = top + i * (bottom - top) / 3;
    tft.drawFastHLine(left, gy, right - left, EDGE);
  }
  uint8_t count = historyCount[selectedVital];
  float low = INFINITY, high = -INFINITY, avgA = 0, avgB = 0;
  for (uint8_t i = 0; i < count; i++) {
    Sample s = getSample(selectedVital, i);
    low = min(low, s.a);
    high = max(high, s.a);
    avgA += s.a;
    if (selectedVital == 3) {
      low = min(low, s.b);
      high = max(high, s.b);
      avgB += s.b;
    }
  }
  if (count) {
    avgA /= count;
    if (selectedVital == 3)
      avgB /= count;
    float pad = max(1.0f, (high - low) * 0.12f);
    low -= pad;
    high += pad;
    int prevX = left, prevYa = bottom, prevYb = bottom;
    for (uint8_t i = 0; i < count; i++) {
      Sample s = getSample(selectedVital, i);
      int px = count == 1 ? (left + right) / 2 : left + (int)i * (right - left) / (count - 1);
      int ya = bottom - (int)((s.a - low) * (bottom - top) / (high - low));
      if (i)
        tft.drawLine(prevX, prevYa, px, ya, ACCENT);
      else
        tft.fillCircle(px, ya, 2, ACCENT);
      if (selectedVital == 3) {
        int yb = bottom - (int)((s.b - low) * (bottom - top) / (high - low));
        if (i)
          tft.drawLine(prevX, prevYb, px, yb, SPO2_COLOR);
        else
          tft.fillCircle(px, yb, 2, SPO2_COLOR);
        prevYb = yb;
      }
      prevX = px;
      prevYa = ya;
    }
  }
  tft.fillRect(12, 187, 296, 48, BG);
  char avg[40];
  if (!count)
    snprintf(avg, sizeof(avg), "Waiting for samples...");
  else if (selectedVital == 0)
    snprintf(avg, sizeof(avg), "AVG %.0f BPM", avgA);
  else if (selectedVital == 1)
    snprintf(avg, sizeof(avg), "AVG %.0f %%", avgA);
  else if (selectedVital == 2 || selectedVital == 5)
    snprintf(avg, sizeof(avg), "AVG %.1f C", avgA);
  else if (selectedVital == 4)
    snprintf(avg, sizeof(avg), suitPressureUnit[0] ? "AVG %.2f hPa" : "AVG %.2f DEMO", avgA);
  else if (selectedVital == 3)
    snprintf(avg, sizeof(avg), "AVG %.0f / %.0f mmHg", avgA, avgB);
  tft.setTextColor(WHITE, BG);
  tft.drawString(avg, 16, 194, 2);
  char nbuf[24];
  snprintf(nbuf, sizeof(nbuf), "%u samples", (unsigned)count);
  tft.setTextColor(MUTED, BG);
  tft.drawRightString(nbuf, 304, 195, 1);
  tft.setTextColor(MUTED, BG);
  tft.drawString(vitalSourceSimulated && selectedVital < 4
                     ? "PI HISTORY · SIMULATED"
                     : (selectedGraphIsLive() ? "LIVE HISTORY" : "DEMO HISTORY · SAMPLE ONLY"),
                 16, 218, 1);
}

void paintGraph() {
  earthClockVisible = false;
  tft.fillScreen(BG);
  tft.fillRect(0, 0, 320, 38, PANEL);
  tft.setTextColor(ACCENT, PANEL);
  tft.drawString(vitalName(selectedVital), 12, 11, 2);
  tft.fillRoundRect(264, 5, 47, 27, 6, EDGE);
  tft.setTextColor(WHITE, EDGE);
  tft.drawCentreString("BACK", 287, 12, 1);
  drawEarthClock();
  tft.drawFastHLine(0, 38, 320, EDGE);
  tft.fillRect(0, 39, 320, 25, BG);
  bool graphLive = selectedGraphIsLive();
  uint16_t status = graphLive ? ACCENT : 0xF5A8;
  tft.fillCircle(14, 52, 4, status);
  tft.setTextColor(status, BG);
  tft.drawString(graphLive ? "LIVE DATA" : "DEMO DATA", 24, 46, 2);
  tft.setTextColor(MUTED, BG);
  tft.drawRightString("RECENT SAMPLES", 307, 48, 1);
  drawGraphData();
}

void refreshCurrentView() {
  if (crewMessageVisible || menuOpen || customizePage || suitCustomizePage)
    return;
  if (graphOpen)
    drawGraphData();
  else if (navigationPage)
    refreshNavigationData();
  else if (suitPage)
    refreshSuitMonitorData();
  else {
    refreshValues();
    paintFooter();
  }
}

void paintDashboard() {
  menuOpen = false;
  graphOpen = false;
  graphReturnToSuit = false;
  navigationPage = false;
  customizePage = false;
  suitPage = false;
  suitCustomizePage = false;
  tft.fillScreen(BG);
  drawHeader();
  const uint8_t order[4] = {ASTRA_ORDER_0, ASTRA_ORDER_1, ASTRA_ORDER_2, ASTRA_ORDER_3};
  const int xs[4] = {10, 165, 10, 165}, ys[4] = {68, 68, 153, 153};
  int pos = 0;
  for (uint8_t i = 0; i < 4; i++) {
    uint8_t id = order[i];
    if ((ASTRA_VISIBLE_MASK & (1 << id)) && id < 4) {
      drawVital(id, xs[pos], ys[pos]);
      pos++;
    }
  }
  paintFooter();
}

void refreshNavigationData() {
  const bool showCompass = ASTRA_NAV_COMPASS;
  const bool showGyro = ASTRA_NAV_GYRO;
  if (showCompass) {
    const int cx = 84, cy = 145, r = 54;
    tft.fillRoundRect(12, 70, 144, 151, ASTRA_CARD_RADIUS, PANEL);
    tft.drawRoundRect(12, 70, 144, 151, ASTRA_CARD_RADIUS, EDGE);
    tft.drawCircle(cx, cy, r, EDGE);
    tft.drawCircle(cx, cy, r - 2, EDGE);
    tft.setTextColor(suitPressureValueColor(ACCENT), PANEL);
    tft.drawCentreString("N", cx, cy - r + 3, 1);
    tft.setTextColor(MUTED, PANEL);
    tft.drawCentreString("E", cx + r - 8, cy - 4, 1);
    tft.drawCentreString("S", cx, cy + r - 12, 1);
    tft.drawCentreString("W", cx - r + 8, cy - 4, 1);
    if (!isnan(navReading.heading)) {
      float a = navReading.heading * PI / 180.0f;
      int ex = cx + (int)(sinf(a) * 37), ey = cy - (int)(cosf(a) * 37);
      tft.drawLine(cx, cy, ex, ey, ACCENT);
      tft.fillCircle(ex, ey, 4, ACCENT);
    }
    tft.fillCircle(cx, cy, 4, WHITE);
    char head[16];
    if (isnan(navReading.heading))
      strcpy(head, "-- deg");
    else
      snprintf(head, sizeof(head), "%.0f deg", navReading.heading);
    tft.setTextColor(WHITE, PANEL);
    tft.drawCentreString(head, cx, cy + 17, 2);
  }
  if (showGyro) {
    int gx = showCompass ? 165 : 12, gw = showCompass ? 143 : 296;
    tft.fillRoundRect(gx, 70, gw, 151, ASTRA_CARD_RADIUS, PANEL);
    tft.drawRoundRect(gx, 70, gw, 151, ASTRA_CARD_RADIUS, EDGE);
    tft.setTextColor(ACCENT, PANEL);
    tft.drawString("GYROSCOPE", gx + 12, 80, 2);
    tft.setTextColor(MUTED, PANEL);
    tft.drawRightString("deg/s", gx + gw - 10, 83, 1);
    const char *axis[3] = {"X", "Y", "Z"};
    float values[3] = {navReading.gx, navReading.gy, navReading.gz};
    uint16_t colors[3] = {HR_COLOR, SPO2_COLOR, TEMP_COLOR};
    for (int i = 0; i < 3; i++) {
      int yy = 111 + i * 31;
      tft.setTextColor(colors[i], PANEL);
      tft.drawString(axis[i], gx + 13, yy, 2);
      char val[18];
      if (isnan(values[i]))
        strcpy(val, "--");
      else
        snprintf(val, sizeof(val), "%+.2f", values[i]);
      tft.setTextColor(WHITE, PANEL);
      tft.drawRightString(val, gx + gw - 13, yy, 2);
    }
  }
  tft.setTextColor(MUTED, BG);
  tft.drawCentreString(navigationLiveData ? "RASPBERRY PI · LIVE" : "DEMO DATA · SAMPLE ONLY", 160,
                       226, 1);
}

void paintNavigation() {
  navigationPage = true;
  menuOpen = false;
  graphOpen = false;
  customizePage = false;
  suitPage = false;
  suitCustomizePage = false;
  tft.fillScreen(BG);
  tft.fillRect(0, 0, 320, 38, PANEL);
  tft.setTextColor(ACCENT, PANEL);
  tft.drawString(ASTRA_NAV_TITLE, 12, 10, 2);
  tft.fillRoundRect(264, 5, 47, 27, 6, EDGE);
  tft.setTextColor(WHITE, EDGE);
  tft.drawCentreString("MENU", 287, 12, 1);
  drawEarthClock();
  tft.drawFastHLine(0, 38, 320, EDGE);
  tft.fillRect(0, 39, 320, 24, BG);
  uint16_t status = navigationLiveData ? ACCENT : 0xF5A8;
  tft.fillCircle(14, 52, 4, status);
  tft.setTextColor(status, BG);
  tft.drawString(navigationLiveData ? "LIVE NAVIGATION" : "DEMO NAVIGATION", 24, 46, 2);
  tft.setTextColor(MUTED, BG);
  tft.drawRightString("SWIPE RIGHT FOR VITALS", 307, 48, 1);
  refreshNavigationData();
}

uint16_t crewMessagePriorityColor() {
  if (strcmp(activeCrewMessage.priority, "INFO") == 0)
    return 0x07FF; // cyan
  if (strcmp(activeCrewMessage.priority, "ADVISORY") == 0)
    return 0xF81F; // magenta
  if (strcmp(activeCrewMessage.priority, "CAUTION") == 0)
    return 0xFFE0; // yellow
  return 0xF800; // red for ALERT
}

void paintCrewMessage() {
  earthClockVisible = false;
  tft.fillScreen(BG);
  tft.fillRect(0, 0, 320, 38, PANEL);
  tft.setTextColor(ACCENT, PANEL);
  tft.drawCentreString("CENTRAL STATION MESSAGE", 160, 11, 2);
  tft.drawFastHLine(0, 38, 320, EDGE);

  uint16_t priorityColor = crewMessagePriorityColor();
  tft.setTextColor(priorityColor, BG);
  tft.drawString(activeCrewMessage.priority, 14, 46, 2);
  tft.setTextColor(MUTED, BG);
  tft.drawRightString(ASTRA_ASTRONAUT_ID, 306, 50, 1);
  tft.drawFastHLine(14, 67, 292, EDGE);

  const char *message = activeCrewMessage.text;
  size_t length = strlen(message), pos = 0;
  const size_t charsPerLine = 24;
  uint8_t lineNumber = 0;
  tft.setTextColor(WHITE, BG);
  while (pos < length && lineNumber < 8) {
    size_t end = pos + charsPerLine;
    if (end > length)
      end = length;
    if (end < length && message[end] != '\n') {
      size_t boundary = end;
      while (boundary > pos && message[boundary] != ' ' && message[boundary] != '\n')
        boundary--;
      if (boundary > pos)
        end = boundary;
    }
    char line[charsPerLine + 1];
    size_t count = end - pos;
    memcpy(line, message + pos, count);
    line[count] = '\0';
    tft.drawString(line, 14, 75 + lineNumber * 18, 2);
    lineNumber++;
    pos = end;
    while (pos < length && (message[pos] == ' ' || message[pos] == '\n'))
      pos++;
  }

  char messageId[28];
  snprintf(messageId, sizeof(messageId), "MESSAGE ID: %lu", (unsigned long)activeCrewMessage.id);
  tft.setTextColor(MUTED, BG);
  tft.drawString(messageId, 14, 222, 1);
  tft.setTextColor(priorityColor, BG);
  tft.drawRightString("RECEIVED", 306, 222, 1);
}

void paintSuitMonitor() {
  menuOpen = false;
  graphOpen = false;
  navigationPage = false;
  customizePage = false;
  suitPage = true;
  suitCustomizePage = false;
  tft.fillScreen(BG);
  tft.fillRect(0, 0, 320, 38, PANEL);
  tft.setTextColor(ACCENT, PANEL);
  tft.drawString(ASTRA_SUIT_TITLE, 12, 11, 2);
  tft.fillRoundRect(264, 5, 47, 27, 6, EDGE);
  tft.setTextColor(WHITE, EDGE);
  tft.drawCentreString("MENU", 287, 12, 1);
  drawEarthClock();
  tft.drawFastHLine(0, 38, 320, EDGE);
  tft.setTextColor(MUTED, BG);
  tft.drawString((suitPressureFromApi || suitTempFromApi) ? "LIVE SUIT DATA" : "DEMO SUIT DATA", 14,
                 49, 1);
  if (suitPressureEnabled) {
    tft.fillRoundRect(12, 70, 296, 65, ASTRA_CARD_RADIUS, PANEL);
    tft.drawRoundRect(12, 70, 296, 65, ASTRA_CARD_RADIUS, EDGE);
    tft.setTextColor(MUTED, PANEL);
    tft.drawString("SUIT PRESSURE", 24, 81, 2);
    char value[24];
    if (isnan(reading.suitPressure))
      strcpy(value, "--");
    else
      dtostrf(reading.suitPressure, 0, 2, value);
    tft.setTextColor(ACCENT, PANEL);
    tft.drawString(value, 24, 104, 4);
    tft.setTextColor(MUTED, PANEL);
    if (suitPressureUnit[0])
      tft.drawRightString(suitPressureUnit, 294, 112, 2);
  } else {
    tft.setTextColor(MUTED, BG);
    tft.drawCentreString("Suit pressure is hidden in Display Options.", 160, 96, 2);
  }
  if (suitTempEnabled) {
    tft.fillRoundRect(12, 146, 296, 65, ASTRA_CARD_RADIUS, PANEL);
    tft.drawRoundRect(12, 146, 296, 65, ASTRA_CARD_RADIUS, EDGE);
    tft.setTextColor(MUTED, PANEL);
    tft.drawString("SUIT TEMPERATURE", 24, 157, 2);
    char value[20];
    if (isnan(reading.suitTemp))
      strcpy(value, "--");
    else
      dtostrf(reading.suitTemp, 0, 1, value);
    tft.setTextColor(suitTemperatureValueColor(TEMP_COLOR), PANEL);
    tft.drawString(value, 24, 180, 4);
    tft.setTextColor(MUTED, PANEL);
    tft.drawString("C", 119, 188, 2);
  } else {
    tft.setTextColor(MUTED, BG);
    tft.drawCentreString("Suit temperature is hidden in Display Options.", 160, 173, 2);
  }
  tft.setTextColor(MUTED, BG);
  tft.drawCentreString("Tap a reading for its graph", 160, 225, 1);
}

void refreshSuitMonitorData() {
  tft.fillRect(14, 45, 220, 18, BG);
  tft.setTextColor(MUTED, BG);
  tft.drawString((suitPressureFromApi || suitTempFromApi) ? "LIVE SUIT DATA" : "DEMO SUIT DATA", 14,
                 49, 1);
  if (suitPressureEnabled) {
    tft.fillRect(20, 102, 232, 31, PANEL);
    char value[24];
    if (isnan(reading.suitPressure))
      strcpy(value, "--");
    else
      dtostrf(reading.suitPressure, 0, 2, value);
    tft.setTextColor(suitPressureValueColor(ACCENT), PANEL);
    tft.drawString(value, 24, 104, 4);
  }
  if (suitTempEnabled) {
    tft.fillRect(20, 178, 94, 31, PANEL);
    char value[20];
    if (isnan(reading.suitTemp))
      strcpy(value, "--");
    else
      dtostrf(reading.suitTemp, 0, 1, value);
    tft.setTextColor(suitTemperatureValueColor(TEMP_COLOR), PANEL);
    tft.drawString(value, 24, 180, 4);
  }
}

void paintCustomization() {
  menuOpen = false;
  graphOpen = false;
  navigationPage = false;
  customizePage = true;
  suitPage = false;
  suitCustomizePage = false;
  tft.fillScreen(BG);
  tft.fillRect(0, 0, 320, 38, PANEL);
  tft.setTextColor(ACCENT, PANEL);
  tft.drawString("DISPLAY OPTIONS", 12, 11, 2);
  tft.fillRoundRect(264, 5, 47, 27, 6, EDGE);
  tft.setTextColor(WHITE, EDGE);
  tft.drawCentreString("BACK", 287, 12, 1);
  drawEarthClock();
  tft.setTextColor(MUTED, BG);
  tft.drawString("LOOK & PAGES", 14, 51, 1);
  tft.fillRoundRect(14, 70, 292, 54, ASTRA_CARD_RADIUS, PANEL);
  tft.drawRoundRect(14, 70, 292, 54, ASTRA_CARD_RADIUS, EDGE);
  tft.fillRoundRect(22, 80, 43, 34, 7, EDGE);
  tft.setTextColor(WHITE, EDGE);
  tft.drawCentreString("<", 43, 90, 2);
  tft.setTextColor(MUTED, PANEL);
  tft.drawCentreString("COLOR THEME", 160, 76, 1);
  tft.setTextColor(ACCENT, PANEL);
  tft.drawCentreString(THEMES[themeIndex].name, 160, 91, 2);
  tft.fillRoundRect(255, 80, 43, 34, 7, EDGE);
  tft.setTextColor(WHITE, EDGE);
  tft.drawCentreString(">", 276, 90, 2);
  tft.fillRoundRect(14, 136, 292, 34, 8, PANEL);
  tft.drawRoundRect(14, 136, 292, 34, 8, EDGE);
  tft.setTextColor(WHITE, PANEL);
  tft.drawString("Navigation page", 24, 147, 2);
  tft.setTextColor(navigationEnabled ? ACCENT : MUTED, PANEL);
  tft.drawRightString(navigationEnabled ? "ON" : "OFF", 292, 148, 2);
  tft.fillRoundRect(14, 179, 292, 34, 8, PANEL);
  tft.drawRoundRect(14, 179, 292, 34, 8, EDGE);
  tft.setTextColor(ACCENT, PANEL);
  tft.drawCentreString("SUIT DISPLAY OPTIONS  >", 160, 190, 2);
}

void paintSuitCustomization() {
  menuOpen = false;
  graphOpen = false;
  navigationPage = false;
  customizePage = false;
  suitPage = false;
  suitCustomizePage = true;
  tft.fillScreen(BG);
  tft.fillRect(0, 0, 320, 38, PANEL);
  tft.setTextColor(ACCENT, PANEL);
  tft.drawString("SUIT DISPLAY", 12, 11, 2);
  tft.fillRoundRect(264, 5, 47, 27, 6, EDGE);
  tft.setTextColor(WHITE, EDGE);
  tft.drawCentreString("BACK", 287, 12, 1);
  drawEarthClock();
  tft.setTextColor(MUTED, BG);
  tft.drawString("SHOW ON SUIT MONITOR", 14, 53, 1);
  tft.fillRoundRect(14, 78, 292, 48, ASTRA_CARD_RADIUS, PANEL);
  tft.drawRoundRect(14, 78, 292, 48, ASTRA_CARD_RADIUS, EDGE);
  tft.setTextColor(WHITE, PANEL);
  tft.drawString("Suit pressure", 24, 94, 2);
  tft.setTextColor(suitPressureEnabled ? ACCENT : MUTED, PANEL);
  tft.drawRightString(suitPressureEnabled ? "ON" : "OFF", 292, 95, 2);
  tft.fillRoundRect(14, 142, 292, 48, ASTRA_CARD_RADIUS, PANEL);
  tft.drawRoundRect(14, 142, 292, 48, ASTRA_CARD_RADIUS, EDGE);
  tft.setTextColor(WHITE, PANEL);
  tft.drawString("Suit temperature", 24, 158, 2);
  tft.setTextColor(suitTempEnabled ? ACCENT : MUTED, PANEL);
  tft.drawRightString(suitTempEnabled ? "ON" : "OFF", 292, 159, 2);
  tft.setTextColor(MUTED, BG);
  tft.drawCentreString("Choices save automatically", 160, 218, 1);
}

void paintMenu(const char *message = "") {
  menuOpen = true;
  graphOpen = false;
  navigationPage = false;
  customizePage = false;
  suitPage = false;
  suitCustomizePage = false;
  tft.fillScreen(BG);
  tft.fillRect(0, 0, 320, 38, PANEL);
  tft.setTextColor(ACCENT, PANEL);
  tft.drawString(ASTRA_TITLE, 12, 11, 2);
  tft.fillRoundRect(264, 5, 47, 27, 6, EDGE);
  tft.setTextColor(WHITE, EDGE);
  tft.drawCentreString("BACK", 287, 12, 1);
  drawEarthClock();
  tft.setTextColor(MUTED, BG);
  tft.drawString("Choose a section", 14, 51, 1);
  const char *labels[3] = {"DISPLAY OPTIONS", "WI-FI + PI SETUP", "CALIBRATE TOUCH"};
  for (int i = 0; i < 3; i++) {
    int y = 76 + i * 45;
    tft.fillRoundRect(14, y, 292, 36, 9, PANEL);
    tft.drawRoundRect(14, y, 292, 36, 9, EDGE);
    tft.setTextColor(WHITE, PANEL);
    tft.drawCentreString(labels[i], 160, y + 10, 2);
  }
  tft.setTextColor(MUTED, BG);
  tft.drawCentreString("Swipe left: Navigation  ·  right: Suit", 160, 222, 1);
  if (message && message[0]) {
    tft.setTextColor(ACCENT, BG);
    tft.drawCentreString(message, 160, 229, 1);
  }
}

void animateSwipeTransition(int direction) {
  const int sx[20] = {18,  35,  58,  76,  101, 123, 147, 171, 194, 218,
                      241, 263, 286, 304, 28,  91,  156, 229, 278, 319};
  const int sy[20] = {33,  178, 67,  213, 42,  112, 221, 55, 153, 23,
                      198, 84,  229, 127, 139, 17,  197, 96, 45,  175};
  const uint16_t starColors[3] = {WHITE, ACCENT, MUTED};
  const int cx = 160, cy = 120, mirror = direction < 0 ? 1 : -1;
  for (int frame = 0; frame < 8; frame++) {
    tft.fillScreen(0x0008);
    float nearScale = 0.10f + frame * 0.11f, farScale = max(0.0f, nearScale - 0.24f);
    for (uint8_t i = 0; i < 20; i++) {
      int dx = (sx[i] - cx) * mirror, dy = sy[i] - cy;
      int x0 = cx + (int)(dx * farScale), y0 = cy + (int)(dy * farScale);
      int x1 = cx + (int)(dx * nearScale), y1 = cy + (int)(dy * nearScale);
      if (x0 >= 0 && x0 < 320 && y0 >= 0 && y0 < 240 && x1 >= 0 && x1 < 320 && y1 >= 0 && y1 < 240)
        tft.drawLine(x0, y0, x1, y1, starColors[i % 3]);
    }
    tft.fillCircle(cx, cy, 2 + frame / 3, ACCENT);
    delay(24);
  }
}

void drawCalibrationTarget() {
  const int tx[4] = {22, 298, 298, 22}, ty[4] = {72, 72, 222, 222};
  calibrationReadyAt = millis() + (calibrationStep == 0 ? 1400 : 450);
  tft.fillScreen(BG);
  tft.fillRect(0, 0, 320, 40, PANEL);
  tft.setTextColor(ACCENT, PANEL);
  tft.drawString("TOUCH CALIBRATION", 12, 12, 2);
  tft.setTextColor(WHITE, BG);
  tft.drawCentreString("Release the screen, then tap each cross", 160, 47, 2);
  tft.drawCentreString("Press firmly, then lift", 160, 67, 1);
  tft.drawCircle(tx[calibrationStep], ty[calibrationStep], 13, ACCENT);
  tft.drawFastHLine(tx[calibrationStep] - 9, ty[calibrationStep], 19, ACCENT);
  tft.drawFastVLine(tx[calibrationStep], ty[calibrationStep] - 9, 19, ACCENT);
  char step[16];
  snprintf(step, sizeof(step), "%u / 4", (unsigned)(calibrationStep + 1));
  tft.setTextColor(MUTED, BG);
  tft.drawCentreString(step, 160, 202, 2);
}

void startCalibration(bool returnToMenu) {
  returnToMenuAfterCal = returnToMenu;
  calibrationActive = true;
  menuOpen = true;
  graphOpen = false;
  calibrationStep = 0;
  lastAcceptedRawX = 0;
  lastAcceptedRawY = 0;
  drawCalibrationTarget();
}

void finishCalibration() {
  float leftX = (calibrationRawX[0] + calibrationRawX[3]) * 0.5f,
        rightX = (calibrationRawX[1] + calibrationRawX[2]) * 0.5f;
  float topX = (calibrationRawX[0] + calibrationRawX[1]) * 0.5f,
        bottomX = (calibrationRawX[2] + calibrationRawX[3]) * 0.5f;
  float leftY = (calibrationRawY[0] + calibrationRawY[3]) * 0.5f,
        rightY = (calibrationRawY[1] + calibrationRawY[2]) * 0.5f;
  float topY = (calibrationRawY[0] + calibrationRawY[1]) * 0.5f,
        bottomY = (calibrationRawY[2] + calibrationRawY[3]) * 0.5f;
  rawYForScreenX = fabsf(rightY - leftY) > fabsf(rightX - leftX);
  float xStart = rawYForScreenX ? leftY : leftX, xEnd = rawYForScreenX ? rightY : rightX;
  float yStart = rawYForScreenX ? topX : topY, yEnd = rawYForScreenX ? bottomX : bottomY;
  if (fabsf(xEnd - xStart) < 500 || fabsf(yEnd - yStart) < 500) {
    calibrationActive = false;
    menuOpen = true;
    paintMenu("Calibration failed; try again.");
    return;
  }
  touchXStart = (uint16_t)constrain((int)roundf(xStart), 0, 4095);
  touchXEnd = (uint16_t)constrain((int)roundf(xEnd), 0, 4095);
  touchYStart = (uint16_t)constrain((int)roundf(yStart), 0, 4095);
  touchYEnd = (uint16_t)constrain((int)roundf(yEnd), 0, 4095);
  preferences.begin("astra", false);
  preferences.putBool("touchok", true);
  preferences.putUChar("touchver", 3);
  preferences.putBool("swapxy", rawYForScreenX);
  preferences.putUShort("txstart", touchXStart);
  preferences.putUShort("txend", touchXEnd);
  preferences.putUShort("tystart", touchYStart);
  preferences.putUShort("tyend", touchYEnd);
  preferences.end();
  calibrationActive = false;
  if (returnToMenuAfterCal) {
    menuOpen = true;
    paintMenu("Touch calibration saved.");
  } else {
    menuOpen = false;
    paintDashboard();
  }
}

void loadCalibration() {
  preferences.begin("astra", true);
  bool valid = preferences.getBool("touchok", false) && preferences.getUChar("touchver", 0) == 3;
  if (valid) {
    rawYForScreenX = preferences.getBool("swapxy", true);
    touchXStart = preferences.getUShort("txstart", 240);
    touchXEnd = preferences.getUShort("txend", 3860);
    touchYStart = preferences.getUShort("tystart", 3800);
    touchYEnd = preferences.getUShort("tyend", 180);
  }
  preferences.end();
  // Run touch calibration at every startup so users can correct alignment after power-up.
  startCalibration(false);
}

void copyPortalValues(WiFiManagerParameter &host, WiFiManagerParameter &port,
                      WiFiManagerParameter &path) {
  strlcpy(piHost, host.getValue(), sizeof(piHost));
  strlcpy(piPort, port.getValue(), sizeof(piPort));
  strlcpy(piPath, path.getValue(), sizeof(piPath));
  preferences.begin("astra", false);
  preferences.putString("apiHost", piHost);
  preferences.putString("apiPort", piPort);
  preferences.putString("apiPath", piPath);
  preferences.end();
}

void loadApiConfig() {
  preferences.begin("astra", true);
  preferences.getString("apiHost", piHost, sizeof(piHost));
  preferences.getString("apiPort", piPort, sizeof(piPort));
  preferences.getString("apiPath", piPath, sizeof(piPath));
  preferences.end();
}

void pollStatusEndpoint() {
  if (!WiFi.isConnected() || millis() - lastHttpPoll < 1000)
    return;
  lastHttpPoll = millis();
  HTTPClient http;
  WiFiClient transport;
  String url = String("http://") + piHost + ":" + piPort + piPath;
  // Keep each poll isolated: no persistent socket and no JSON parser reading the socket directly.
  configureHttp(http, 1200);
  bool wasConnected = apiConnected, wasLiveData = liveData,
       wasVitalSourceSimulated = vitalSourceSimulated;
  uint8_t wasVitalLiveMask = vitalLiveMask;
  bool responseOk = false, navGot = false;
  if (http.begin(transport, url)) {
    int code = http.GET();
    if (code == HTTP_CODE_OK) {
      String responseBody = http.getString();
      JsonDocument doc;
      DeserializationError error = deserializeJson(doc, responseBody);
      if (!error) {
        responseOk = true;
        uint8_t previousVitalLiveMask = vitalLiveMask;
        vitalLiveMask = 0;
        JsonVariant bpm = findVitalField(doc, "bpm", "heart_rate_bpm", "heart_rate");
        if (bpm.isNull())
          bpm = findVitalField(doc, "pulse_bpm");
        if (!bpm.isNull()) {
          reading.hr = bpm.as<float>();
          if (!(previousVitalLiveMask & (1U << 0)))
            clearVitalHistory(0);
          vitalLiveMask |= 1U << 0;
        }
        JsonVariant oxygen = findVitalField(doc, "o2_saturation", "spo2", "oxygen_saturation");
        if (oxygen.isNull())
          oxygen = findVitalField(doc, "spo2_percent");
        if (oxygen.isNull())
          oxygen = findVitalField(doc, "oxygen_saturation_pct");
        if (!oxygen.isNull()) {
          reading.spo2 = oxygen.as<float>();
          if (!(previousVitalLiveMask & (1U << 1)))
            clearVitalHistory(1);
          vitalLiveMask |= 1U << 1;
        }
        JsonVariant bodyTemperature =
            findVitalField(doc, "body_temperature_c", "body_temp_c", "body_temperature");
        if (bodyTemperature.isNull())
          bodyTemperature = findVitalField(doc, "body_temp");
        if (!bodyTemperature.isNull()) {
          reading.temp = bodyTemperature.as<float>();
          if (!(previousVitalLiveMask & (1U << 2)))
            clearVitalHistory(2);
          vitalLiveMask |= 1U << 2;
        }
        JsonVariant pressurePair = findVitalField(doc, "blood_pressure");
        JsonVariant systolic, diastolic;
        if (pressurePair.is<JsonObject>()) {
          systolic = pressurePair["systolic"];
          if (systolic.isNull())
            systolic = pressurePair["systolic_mm_hg"];
          if (systolic.isNull())
            systolic = pressurePair["systolic_mmhg"];
          diastolic = pressurePair["diastolic"];
          if (diastolic.isNull())
            diastolic = pressurePair["diastolic_mm_hg"];
          if (diastolic.isNull())
            diastolic = pressurePair["diastolic_mmhg"];
        }
        if (systolic.isNull())
          systolic = findVitalField(doc, "systolic_mmhg", "systolic_bp", "systolic");
        if (diastolic.isNull())
          diastolic = findVitalField(doc, "diastolic_mmhg", "diastolic_bp", "diastolic");
        if (!systolic.isNull() && !diastolic.isNull()) {
          reading.sys = systolic.as<float>();
          reading.dia = diastolic.as<float>();
          if (!(previousVitalLiveMask & (1U << 3)))
            clearVitalHistory(3);
          vitalLiveMask |= 1U << 3;
        }
        const char *biometricSource = doc["biometrics"]["source"] | "";
        vitalSourceSimulated = strcmp(biometricSource, "simulated") == 0;
        liveData = vitalLiveMask != 0;
        if (liveData)
          lastData = millis();
        JsonVariant pressure = doc["sensors"]["pressure_hpa"];
        suitPressureFromApi = !pressure.isNull();
        if (suitPressureFromApi) {
          reading.suitPressure = pressure.as<float>();
          strlcpy(suitPressureUnit, "hPa", sizeof(suitPressureUnit));
        }
        JsonVariant suitTemperature = doc["sensors"]["temperature_c"];
        suitTempFromApi = !suitTemperature.isNull();
        if (suitTempFromApi)
          reading.suitTemp = suitTemperature.as<float>();
        if (!doc["sensors"]["orientation_deg"]["yaw"].isNull()) {
          navReading.heading = doc["sensors"]["orientation_deg"]["yaw"].as<float>();
          navGot = true;
        }
        if (!doc["sensors"]["gyroscope_rps"]["x"].isNull()) {
          navReading.gx = doc["sensors"]["gyroscope_rps"]["x"].as<float>() * 180.0f / PI;
          navGot = true;
        }
        if (!doc["sensors"]["gyroscope_rps"]["y"].isNull()) {
          navReading.gy = doc["sensors"]["gyroscope_rps"]["y"].as<float>() * 180.0f / PI;
          navGot = true;
        }
        if (!doc["sensors"]["gyroscope_rps"]["z"].isNull()) {
          navReading.gz = doc["sensors"]["gyroscope_rps"]["z"].as<float>() * 180.0f / PI;
          navGot = true;
        }
      }
    }
    http.end();
  }
  if (responseOk) {
    apiFailureCount = 0;
    apiConnected = true;
    navigationLiveData = navGot;
  } else if (apiFailureCount < 3) {
    apiFailureCount++;
    if (apiFailureCount >= 3)
      apiConnected = false;
  }
  if (!apiConnected) {
    navigationLiveData = false;
    suitPressureFromApi = false;
    suitTempFromApi = false;
    suitPressureUnit[0] = '\0';
    vitalLiveMask = 0;
    liveData = false;
    vitalSourceSimulated = false;
  }
  if (crewMessageVisible || graphOpen)
    return;
  if (suitPage) {
    if (wasConnected != apiConnected)
      paintSuitMonitor();
    else
      refreshSuitMonitorData();
  } else if (navigationPage) {
    if (wasConnected != apiConnected)
      paintNavigation();
    else
      refreshNavigationData();
  } else if ((wasConnected != apiConnected || wasLiveData != liveData ||
              wasVitalLiveMask != vitalLiveMask ||
              wasVitalSourceSimulated != vitalSourceSimulated) &&
             !menuOpen && !graphOpen && !customizePage && !suitCustomizePage)
    drawHeader();
}

bool crewMessageWasDisplayed(uint32_t id) {
  for (uint8_t i = 0; i < displayedMessageIdCount; i++) {
    if (displayedMessageIds[i] == id)
      return true;
  }
  return false;
}

void rememberDisplayedCrewMessage(uint32_t id) {
  if (crewMessageWasDisplayed(id))
    return;
  displayedMessageIds[displayedMessageIdHead] = id;
  displayedMessageIdHead = (displayedMessageIdHead + 1) % 16;
  if (displayedMessageIdCount < 16)
    displayedMessageIdCount++;
}

bool validCrewMessagePriority(const char *priority) {
  return strcmp(priority, "INFO") == 0 || strcmp(priority, "ADVISORY") == 0 ||
         strcmp(priority, "CAUTION") == 0 || strcmp(priority, "ALERT") == 0;
}

void pollCrewMessages() {
  uint32_t now = millis();
  if (!WiFi.isConnected() || calibrationActive || crewMessageVisible || crewMessageAckPending ||
      now - lastCrewMessagePollAt < ASTRA_MESSAGE_POLL_INTERVAL_MS)
    return;
  lastCrewMessagePollAt = now;

  HTTPClient http;
  WiFiClient transport;
  String url = String("http://") + piHost + ":" + piPort + ASTRA_MESSAGES_PATH +
               "?recipient_id=" + ASTRA_ASTRONAUT_ID + "&pending_only=true&limit=1";
  configureHttp(http, 900);
  if (!http.begin(transport, url))
    return;
  int code = http.GET();
  if (code != HTTP_CODE_OK) {
    http.end();
    return;
  }
  int contentLength = http.getSize();
  if (contentLength <= 0 || contentLength > 2048) {
    http.end();
    return;
  }

  // Parse only required fields, with a small response-size and nesting bound.
  JsonDocument filter;
  JsonObject filteredMessage = filter.to<JsonArray>().add<JsonObject>();
  filteredMessage["id"] = true;
  filteredMessage["recipient_id"] = true;
  filteredMessage["priority"] = true;
  filteredMessage["text"] = true;
  JsonDocument doc;
  DeserializationError error = deserializeJson(
      doc, http.getStream(), DeserializationOption::Filter(filter),
      DeserializationOption::NestingLimit(4));
  http.end();
  if (error || !doc.is<JsonArray>())
    return;
  JsonArray messages = doc.as<JsonArray>();
  if (messages.size() == 0)
    return;

  JsonVariant item = messages[0];
  if (!item.is<JsonObject>())
    return;
  JsonVariant idValue = item["id"];
  JsonVariant recipientValue = item["recipient_id"];
  JsonVariant priorityValue = item["priority"];
  JsonVariant textValue = item["text"];
  if (!idValue.is<uint32_t>() || !recipientValue.is<const char *>() ||
      !priorityValue.is<const char *>() || !textValue.is<const char *>())
    return;
  uint32_t id = idValue.as<uint32_t>();
  const char *recipient = recipientValue.as<const char *>();
  const char *priority = priorityValue.as<const char *>();
  const char *text = textValue.as<const char *>();
  if (!id || strcmp(recipient, ASTRA_ASTRONAUT_ID) != 0 || !validCrewMessagePriority(priority))
    return;
  if (crewMessageWasDisplayed(id) || id == lastReceivedMessageId)
    return;

  activeCrewMessage.id = id;
  strlcpy(activeCrewMessage.priority, priority, sizeof(activeCrewMessage.priority));
  size_t textLength = strlen(text);
  strlcpy(activeCrewMessage.text, text, sizeof(activeCrewMessage.text));
  if (textLength >= sizeof(activeCrewMessage.text))
    memcpy(activeCrewMessage.text + sizeof(activeCrewMessage.text) - 4, "...", 4);
  paintCrewMessage();
  activeCrewMessage.displayed = true;
  crewMessageVisible = true;
  crewMessageDisplayStartedAt = millis();
  crewMessageAckPending = true;
  nextCrewAckRetryAt = 0;
  lastReceivedMessageId = id;
  rememberDisplayedCrewMessage(id);
}

void retryCrewMessageAcknowledgement() {
  if (!crewMessageAckPending || !activeCrewMessage.displayed ||
      (int32_t)(millis() - nextCrewAckRetryAt) < 0)
    return;
  if (!WiFi.isConnected()) {
    nextCrewAckRetryAt = millis() + ASTRA_MESSAGE_ACK_RETRY_MS;
    return;
  }

  HTTPClient http;
  WiFiClient transport;
  String url = String("http://") + piHost + ":" + piPort + ASTRA_MESSAGES_PATH + "/" +
               String((unsigned long)activeCrewMessage.id) + "/ack";
  configureHttp(http, 900);
  if (!http.begin(transport, url)) {
    nextCrewAckRetryAt = millis() + ASTRA_MESSAGE_ACK_RETRY_MS;
    return;
  }
  http.addHeader("Content-Type", "application/json");
  char body[80];
  snprintf(body, sizeof(body), "{\"recipient_id\":\"%s\"}", ASTRA_ASTRONAUT_ID);
  int code = http.POST((uint8_t *)body, strlen(body));
  http.end();
  if (code >= 200 && code < 300) {
    crewMessageAckPending = false;
  } else {
    nextCrewAckRetryAt = millis() + ASTRA_MESSAGE_ACK_RETRY_MS;
  }
}

void updateCrewMessageDisplayTimer() {
  if (crewMessageVisible && millis() - crewMessageDisplayStartedAt >= ASTRA_MESSAGE_DISPLAY_MS) {
    crewMessageVisible = false;
    paintDashboard();
  }
}

void startSetupPortal() {
  menuOpen = false;
  graphOpen = false;
  tft.fillScreen(BG);
  tft.setTextColor(ACCENT, BG);
  tft.drawString("ASTRA SETUP", 12, 16, 4);
  tft.setTextColor(WHITE, BG);
  tft.drawString("Join Astra-Setup on your phone", 12, 70, 2);
  tft.drawString("Open http://192.168.4.1", 12, 99, 2);
  tft.setTextColor(MUTED, BG);
  tft.drawString("Enter Wi-Fi and status API details", 12, 140, 2);
  tft.drawString("Health vitals stay in demo mode.", 12, 166, 2);
  static WiFiManagerParameter host("host", "Status API host or IP", piHost, sizeof(piHost));
  static WiFiManagerParameter port("port", "HTTP port", piPort, sizeof(piPort));
  static WiFiManagerParameter path("path", "Status API path", piPath, sizeof(piPath));
  static bool paramsAdded = false;
  if (!paramsAdded) {
    wifiManager.addParameter(&host);
    wifiManager.addParameter(&port);
    wifiManager.addParameter(&path);
    paramsAdded = true;
  }
  wifiManager.setConfigPortalTimeout(0);
  wifiManager.setConnectTimeout(30);
  bool connected = wifiManager.startConfigPortal("Astra-Setup");
  copyPortalValues(host, port, path);
  if (connected) {
    lastHttpPoll = 0;
    paintDashboard();
  } else {
    menuOpen = true;
    paintMenu("Setup closed; demo is still active.");
  }
}

uint16_t readTouchChannel(uint8_t command) {
  digitalWrite(TP_CS, LOW);
  shiftOut(TP_MOSI, TP_CLK, MSBFIRST, command);
  uint16_t value =
      (uint16_t(shiftIn(TP_MISO, TP_CLK, MSBFIRST)) << 8) | shiftIn(TP_MISO, TP_CLK, MSBFIRST);
  digitalWrite(TP_CS, HIGH);
  return value >> 3;
}

bool getTouchPress(uint16_t &rawX, uint16_t &rawY) {
  static uint32_t lastPoll = 0, lastDown = 0, lastUp = 0, lastDiagnostic = 0, releaseSince = 0;
  static bool touchWasDown = false, armed = false;
  if (millis() - lastPoll < 10)
    return false;
  lastPoll = millis();
  rawX = readTouchChannel(0xD0);
  rawY = readTouchChannel(0x90);
  currentTouchRawX = rawX;
  currentTouchRawY = rawY;
  uint16_t z1 = readTouchChannel(0xB0), z2 = readTouchChannel(0xC0);
  int pressure = (int)z1 + 4095 - (int)z2;
  if (millis() - lastDiagnostic >= 250) {
    Serial.printf("Touch probe raw=%u,%u z=%u,%u p=%d irq=%d\n", rawX, rawY, z1, z2, pressure,
                  digitalRead(TP_IRQ));
    lastDiagnostic = millis();
  }
  bool down = (digitalRead(TP_IRQ) == LOW) && (pressure > 350);
  touchCurrentlyDown = down;
  if (!armed) {
    if (!down) {
      if (!releaseSince)
        releaseSince = millis();
      if (millis() - releaseSince >= 500)
        armed = true;
    } else
      releaseSince = 0;
    return false;
  }
  if (!down) {
    lastDown = 0;
    if (!lastUp)
      lastUp = millis();
    if (millis() - lastUp >= 80)
      touchWasDown = false;
    return false;
  }
  lastUp = 0;
  if (!lastDown)
    lastDown = millis();
  bool movedDuringCalibration = calibrationActive && lastAcceptedRawX &&
                                (abs((int)rawX - (int)lastAcceptedRawX) > 350 ||
                                 abs((int)rawY - (int)lastAcceptedRawY) > 350);
  if ((touchWasDown && !movedDuringCalibration) || (!touchWasDown && millis() - lastDown < 50) ||
      (int32_t)(millis() - calibrationReadyAt) < 0 || millis() - lastTouch < 180)
    return false;
  touchWasDown = true;
  lastTouch = millis();
  lastAcceptedRawX = rawX;
  lastAcceptedRawY = rawY;
  Serial.printf("Touch raw=%u,%u p=%d irq=%d\n", rawX, rawY, pressure, digitalRead(TP_IRQ));
  return true;
}

void mapTouchToScreen(uint16_t rawX, uint16_t rawY, int &x, int &y) {
  int rawForX = rawYForScreenX ? rawY : rawX, rawForY = rawYForScreenX ? rawX : rawY;
  x = constrain(map(rawForX, touchXStart, touchXEnd, 10, 309), 0, 319);
  y = constrain(map(rawForY, touchYStart, touchYEnd, 10, 229), 0, 239);
}

bool headerButtonHit(int x, int y) {
  // Header controls are drawn at x=254..311, y=5..32. Keep a small touch
  // margin around that button without letting content taps trigger navigation.
  return x >= 250 && y < 38;
}

void handleTap(int x, int y) {
  if (graphOpen && headerButtonHit(x, y)) {
    if (graphReturnToSuit)
      paintSuitMonitor();
    else
      paintDashboard();
    return;
  }
  if (customizePage) {
    if (headerButtonHit(x, y)) {
      paintMenu();
      return;
    }
    if (y >= 65 && y < 130) {
      // Treat each half of the theme card as a large previous/next target;
      // users do not need to hit the small arrow glyph precisely.
      if (x < 160)
        themeIndex = (themeIndex + THEME_COUNT - 1) % THEME_COUNT;
      else
        themeIndex = (themeIndex + 1) % THEME_COUNT;
      applyTheme();
      saveCustomization();
      Serial.printf("Theme changed: %u (%s), tap=%d,%d\n", themeIndex,
                    THEMES[themeIndex].name, x, y);
      paintCustomization();
      return;
    }
    if (y >= 130 && y < 175) {
      navigationEnabled = !navigationEnabled;
      saveCustomization();
      paintCustomization();
      return;
    }
    if (y >= 175 && y < 218) {
      paintSuitCustomization();
      return;
    }
    return;
  }
  if (suitCustomizePage) {
    if (headerButtonHit(x, y)) {
      paintCustomization();
      return;
    }
    if (y >= 66 && y < 132) {
      suitPressureEnabled = !suitPressureEnabled;
      saveCustomization();
      paintSuitCustomization();
      return;
    }
    if (y >= 136 && y < 200) {
      suitTempEnabled = !suitTempEnabled;
      saveCustomization();
      paintSuitCustomization();
      return;
    }
    return;
  }
  if (suitPage) {
    if (headerButtonHit(x, y)) {
      paintMenu();
      return;
    }
    if (suitPressureEnabled && y >= 70 && y < 135) {
      selectedVital = 4;
      graphReturnToSuit = true;
      graphOpen = true;
      paintGraph();
      return;
    }
    if (suitTempEnabled && y >= 146 && y < 212) {
      selectedVital = 5;
      graphReturnToSuit = true;
      graphOpen = true;
      paintGraph();
      return;
    }
    return;
  }
  if (menuOpen) {
    if (headerButtonHit(x, y)) {
      paintDashboard();
      return;
    }
    // Keep the first menu card easy to hit if touch calibration is slightly off.
    // Its center is y=94, while the visible Back control stays in the top header.
    if (y >= 55 && y < 117) {
      paintCustomization();
      return;
    }
    if (y >= 117 && y < 162) {
      startSetupPortal();
      return;
    }
    if (y >= 162 && y < 211) {
      startCalibration(true);
      return;
    }
    return;
  }
  if (headerButtonHit(x, y)) {
    menuOpen = true;
    paintMenu();
    return;
  }
  if (!menuOpen && !graphOpen && !navigationPage && !customizePage) {
    const uint8_t order[4] = {ASTRA_ORDER_0, ASTRA_ORDER_1, ASTRA_ORDER_2, ASTRA_ORDER_3};
    const int xs[4] = {10, 165, 10, 165}, ys[4] = {68, 68, 153, 153};
    int pos = 0;
    for (uint8_t i = 0; i < 4; i++) {
      uint8_t id = order[i];
      if (id < 4 && (ASTRA_VISIBLE_MASK & (1 << id))) {
        if (x >= xs[pos] && x < xs[pos] + 145 && y >= ys[pos] && y < ys[pos] + 74) {
          selectedVital = id;
          graphReturnToSuit = false;
          graphOpen = true;
          paintGraph();
          return;
        }
        pos++;
      }
    }
  }
}

void handleTouch() {
  static bool tapPending = false;
  static bool ignoreUntilRelease = false;
  static int pendingTapX = 0, pendingTapY = 0;
  static uint32_t pendingReleaseAt = 0;
  uint16_t pressRawX = 0, pressRawY = 0;
  bool pressed = getTouchPress(pressRawX, pressRawY);
  if (ignoreUntilRelease) {
    if (touchCurrentlyDown)
      return;
    ignoreUntilRelease = false;
  }
  if (crewMessageVisible) {
    if (touchCurrentlyDown)
      ignoreUntilRelease = true;
    return;
  }
  if (calibrationActive) {
    if (pressed) {
      calibrationRawX[calibrationStep] = pressRawX;
      calibrationRawY[calibrationStep] = pressRawY;
      calibrationStep++;
      if (calibrationStep >= 4)
        finishCalibration();
      else
        drawCalibrationTarget();
    }
    return;
  }
  if ((menuOpen || customizePage || suitCustomizePage) && pressed) {
    int tapX, tapY;
    mapTouchToScreen(pressRawX, pressRawY, tapX, tapY);
    Serial.printf("UI press=%d,%d\n", tapX, tapY);
    tapPending = false;
    pendingReleaseAt = 0;
    handleTap(tapX, tapY);
    // The newly displayed page must not interpret the tail of this same
    // physical press as a second tap (for example, Back then Menu).
    ignoreUntilRelease = true;
    swipeTracking = false;
    swipeConsumed = false;
    return;
  }
  if (!menuOpen && !graphOpen && !customizePage && !suitCustomizePage &&
      (navigationEnabled || suitPressureEnabled || suitTempEnabled)) {
    if (touchCurrentlyDown) {
      int x, y;
      mapTouchToScreen(currentTouchRawX, currentTouchRawY, x, y);
      if (!swipeTracking) {
        swipeTracking = true;
        swipeConsumed = false;
        swipeStartX = x;
        swipeStartY = y;
      } else {
        int dx = x - swipeStartX, dy = y - swipeStartY;
        if (!swipeConsumed && abs(dx) > 68 && abs(dy) < 95) {
          if (dx < 0) {
            if (suitPage) {
              swipeConsumed = true;
              animateSwipeTransition(-1);
              paintDashboard();
            } else if (!navigationPage && navigationEnabled) {
              swipeConsumed = true;
              animateSwipeTransition(-1);
              paintNavigation();
            }
          } else {
            if (navigationPage) {
              swipeConsumed = true;
              animateSwipeTransition(1);
              paintDashboard();
            } else if (!suitPage && (suitPressureEnabled || suitTempEnabled)) {
              swipeConsumed = true;
              animateSwipeTransition(1);
              paintSuitMonitor();
            }
          }
        }
      }
      return;
    }
    if (swipeTracking) {
      if (!swipeConsumed)
        handleTap(swipeStartX, swipeStartY);
      swipeTracking = false;
      swipeConsumed = false;
      return;
    }
  }
  if (pressed) {
    mapTouchToScreen(pressRawX, pressRawY, pendingTapX, pendingTapY);
    tapPending = true;
    pendingReleaseAt = 0;
  }
  if (tapPending) {
    if (touchCurrentlyDown) {
      pendingReleaseAt = 0;
      int x, y;
      mapTouchToScreen(currentTouchRawX, currentTouchRawY, x, y);
      if (abs(x - pendingTapX) > 24 || abs(y - pendingTapY) > 24)
        tapPending = false;
      return;
    }
    if (!pendingReleaseAt)
      pendingReleaseAt = millis();
    if (millis() - pendingReleaseAt >= 100) {
      Serial.printf("Touch tap=%d,%d\n", pendingTapX, pendingTapY);
      tapPending = false;
      pendingReleaseAt = 0;
      handleTap(pendingTapX, pendingTapY);
    }
  }
}

void setup() {
  Serial.begin(115200);
  delay(150);
  esp_reset_reason_t resetReason = esp_reset_reason();
  Serial.printf("\n[Astra] Boot reset cause: %s (%d); free heap: %u bytes\n",
                resetReasonName(resetReason), (int)resetReason, (unsigned)ESP.getFreeHeap());
  pinMode(TFT_BL, OUTPUT);
  digitalWrite(TFT_BL, TFT_BACKLIGHT_ON);
  tft.init();
  tft.setRotation(1);
  pinMode(TP_CLK, OUTPUT);
  digitalWrite(TP_CLK, LOW);
  pinMode(TP_MOSI, OUTPUT);
  pinMode(TP_MISO, INPUT);
  pinMode(TP_CS, OUTPUT);
  digitalWrite(TP_CS, HIGH);
  pinMode(TP_IRQ, INPUT);
  restoreSavedClock();
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.begin();
  // NTP synchronizes whenever Wi-Fi has internet; the ESP32 clock keeps
  // advancing during ordinary Wi-Fi outages using the last synchronized time.
  configTzTime("PST8PDT,M3.2.0,M11.1.0", "pool.ntp.org", "time.nist.gov");
  recordSample();
  loadApiConfig();
  loadCustomization();
  playBootAnimation();
  loadCalibration();
  if (!calibrationActive)
    paintDashboard();
}

void loop() {
  updateEarthClock();
  handleTouch();
  pollStatusEndpoint();
  updateCrewMessageDisplayTimer();
  pollCrewMessages();
  retryCrewMessageAcknowledgement();
  if (!menuOpen && millis() - lastDemo > 1800) {
    lastDemo = millis();
    float t = millis() / 1000.0f;
    if (!(vitalLiveMask & (1U << 0)))
      reading.hr = 72 + roundf(3 * sinf(t / 3));
    if (!(vitalLiveMask & (1U << 1)))
      reading.spo2 = 98 + roundf(sinf(t / 5));
    if (!(vitalLiveMask & (1U << 2)))
      reading.temp = 36.8f + 0.1f * sinf(t / 9);
    if (!(vitalLiveMask & (1U << 3))) {
      reading.sys = 118 + roundf(2 * sinf(t / 4));
      reading.dia = 76 + roundf(2 * cosf(t / 4));
    }
    if (!suitPressureFromApi)
      reading.suitPressure = 4.2f + 0.15f * sinf(t / 5);
    if (!suitTempFromApi)
      reading.suitTemp = 22.0f + 0.4f * cosf(t / 8);
    if (!navigationLiveData) {
      navReading.heading = fmodf(248 + 8 * sinf(t / 7) + 360, 360);
      navReading.gx = 0.04f * sinf(t / 2);
      navReading.gy = 0.07f * cosf(t / 3);
      navReading.gz = 0.05f * sinf(t / 4);
    }
    recordSample();
    refreshCurrentView();
  }
}
