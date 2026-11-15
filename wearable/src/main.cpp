#include <Arduino.h>
#include <ArduinoJson.h>
#include <HTTPClient.h>
#include <TFT_eSPI.h>
#include <WiFi.h>
#include <cmath>

#include "app_config.h"

#if __has_include("secrets.h")
#include "secrets.h"
#else
#include "secrets.example.h"
#warning "Using placeholder Wi-Fi credentials; copy secrets.example.h to secrets.h"
#endif

namespace {

TFT_eSPI display;

struct StatusPayload {
  String timestamp;
  String status = "OFFLINE";
  float score = 0.0F;
  String summary = "Backpack not connected.";
  float temperatureC = NAN;
  float humidityPct = NAN;
  float pressureHpa = NAN;
  String source = "simulated";
};

struct CrewMessage {
  uint32_t id = 0;
  String priority = "INFO";
  String text;
};

StatusPayload payload;
CrewMessage activeMessage;
unsigned long lastPollMs = 0;
unsigned long lastMessagePollMs = 0;
unsigned long lastMessageReceivedMs = 0;
unsigned long lastWifiAttemptMs = 0;
unsigned long lastFreshPayloadMs = 0;
uint32_t lastMessageId = 0;
String lastRemoteTimestamp;
bool screenDirty = true;

bool isKnownStatus(const String &status) {
  return status == "LEARNING" || status == "NORMAL" || status == "CAUTION" ||
         status == "ALERT" || status == "OFFLINE";
}

uint16_t stateColor(const String &status) {
  if (status == "NORMAL") return TFT_GREEN;
  if (status == "LEARNING") return TFT_CYAN;
  if (status == "CAUTION") return TFT_YELLOW;
  if (status == "ALERT") return TFT_RED;
  return TFT_LIGHTGREY;
}

uint16_t priorityColor(const String &priority) {
  if (priority == "ALERT") return TFT_RED;
  if (priority == "CAUTION") return TFT_YELLOW;
  if (priority == "ADVISORY") return TFT_MAGENTA;
  return TFT_CYAN;
}

const char *stateSymbol(const String &status) {
  if (status == "NORMAL") return "[OK]";
  if (status == "LEARNING") return "[...]";
  if (status == "CAUTION") return "[!]";
  if (status == "ALERT") return "[!!]";
  return "[X]";
}

String reading(float value, uint8_t decimals, const char *unit) {
  if (std::isnan(value)) return String("-- ") + unit;
  return String(value, static_cast<unsigned int>(decimals)) + " " + unit;
}

void drawWrappedSummary(const String &text) {
  display.setTextFont(2);
  display.setTextColor(TFT_WHITE, TFT_BLACK);
  display.setCursor(12, 116);

  constexpr size_t maxLineLength = 34;
  String remaining = text;
  for (uint8_t line = 0; line < 3 && !remaining.isEmpty(); ++line) {
    size_t split = remaining.length();
    if (split > maxLineLength) {
      split = maxLineLength;
      while (split > 0 && remaining.charAt(split) != ' ') --split;
      if (split == 0) split = maxLineLength;
    }
    display.println(remaining.substring(0, split));
    remaining = remaining.substring(split);
    remaining.trim();
  }
}

void drawWrappedMessage(const String &text) {
  display.setTextFont(2);
  display.setTextColor(TFT_WHITE, TFT_BLACK);
  display.setCursor(14, 82);

  constexpr size_t maxLineLength = 38;
  String remaining = text;
  for (uint8_t line = 0; line < 6 && !remaining.isEmpty(); ++line) {
    size_t split = remaining.length();
    if (split > maxLineLength) {
      split = maxLineLength;
      while (split > 0 && remaining.charAt(split) != ' ') --split;
      if (split == 0) split = maxLineLength;
    }
    display.println(remaining.substring(0, split));
    remaining = remaining.substring(split);
    remaining.trim();
  }
}

void renderMessage() {
  display.fillScreen(TFT_BLACK);
  display.setTextDatum(TL_DATUM);
  display.setTextFont(2);
  display.setTextColor(TFT_CYAN, TFT_BLACK);
  display.drawString("CENTRAL STATION MESSAGE", 12, 10);
  display.setTextColor(TFT_LIGHTGREY, TFT_BLACK);
  display.drawRightString("#" + String(activeMessage.id), 308, 10, 2);
  display.drawFastHLine(10, 33, 300, TFT_DARKGREY);

  display.setTextColor(priorityColor(activeMessage.priority), TFT_BLACK);
  display.drawString(activeMessage.priority, 12, 47, 4);
  display.setTextColor(TFT_LIGHTGREY, TFT_BLACK);
  display.drawRightString(ASTRA_ASTRONAUT_ID, 308, 54, 2);
  drawWrappedMessage(activeMessage.text);

  display.drawFastHLine(10, 212, 300, TFT_DARKGREY);
  display.setTextColor(TFT_GREEN, TFT_BLACK);
  display.drawString("RECEIVED BY WEARABLE", 12, 220, 2);
  screenDirty = false;
}

void render() {
  if (activeMessage.id != 0) {
    renderMessage();
    return;
  }
  display.fillScreen(TFT_BLACK);
  display.setTextDatum(TL_DATUM);

  display.setTextFont(2);
  display.setTextColor(TFT_WHITE, TFT_BLACK);
  display.drawString("ASTRA", 12, 8);
  display.setTextColor(
      WiFi.status() == WL_CONNECTED ? TFT_GREEN : TFT_LIGHTGREY, TFT_BLACK);
  display.drawRightString(
      WiFi.status() == WL_CONNECTED ? "LOCAL LINK" : "NO LINK", 308, 8, 2);

  display.drawFastHLine(10, 30, 300, TFT_DARKGREY);
  display.setTextColor(stateColor(payload.status), TFT_BLACK);
  display.drawCentreString(
      String(stateSymbol(payload.status)) + " " + payload.status, 160, 50, 4);

  drawWrappedSummary(payload.summary);

  display.drawFastHLine(10, 180, 300, TFT_DARKGREY);
  display.setTextFont(2);
  display.setTextColor(TFT_WHITE, TFT_BLACK);
  display.drawString("TEMP  " + reading(payload.temperatureC, 1, "C"), 12, 190);
  display.drawString("HUM   " + reading(payload.humidityPct, 1, "%"), 12, 210);
  display.drawString("PRESS " + reading(payload.pressureHpa, 1, "hPa"), 166, 190);
  display.setTextColor(TFT_LIGHTGREY, TFT_BLACK);
  display.drawString("SOURCE: " + payload.source, 166, 210);
  screenDirty = false;
}

void markOffline(const String &reason) {
  if (payload.status == "OFFLINE" && payload.summary == reason) return;
  payload.status = "OFFLINE";
  payload.summary = reason;
  payload.temperatureC = NAN;
  payload.humidityPct = NAN;
  payload.pressureHpa = NAN;
  screenDirty = true;
}

bool parsePayload(const String &body, StatusPayload &next) {
  JsonDocument document;
  DeserializationError error = deserializeJson(document, body);
  if (error) {
    Serial.printf("JSON parse error: %s\n", error.c_str());
    return false;
  }

  if (!document["timestamp"].is<const char *>() ||
      !document["status"].is<const char *>() ||
      !document["summary"].is<const char *>() ||
      !document["source"].is<const char *>()) {
    Serial.println("JSON missing a required status field");
    return false;
  }

  next.timestamp = document["timestamp"].as<String>();
  next.status = document["status"].as<String>();
  next.summary = document["summary"].as<String>();
  next.source = document["source"].as<String>();
  next.score = document["score"] | 0.0F;

  if (!isKnownStatus(next.status)) {
    Serial.printf("Unknown status: %s\n", next.status.c_str());
    return false;
  }
  if (next.source != "live" && next.source != "cached" &&
      next.source != "simulated") {
    Serial.printf("Unknown source: %s\n", next.source.c_str());
    return false;
  }

  JsonVariantConst sensors = document["sensors"];
  next.temperatureC = sensors["temperature_c"].is<float>()
                          ? sensors["temperature_c"].as<float>()
                          : NAN;
  next.humidityPct = sensors["humidity_pct"].is<float>()
                         ? sensors["humidity_pct"].as<float>()
                         : NAN;
  next.pressureHpa = sensors["pressure_hpa"].is<float>()
                         ? sensors["pressure_hpa"].as<float>()
                         : NAN;
  return true;
}

void connectWifiIfNeeded(unsigned long now) {
  if (WiFi.status() == WL_CONNECTED) return;
  if (now - lastWifiAttemptMs < ASTRA_WIFI_RETRY_MS) return;

  lastWifiAttemptMs = now;
  Serial.printf("Connecting to Wi-Fi SSID '%s'\n", WIFI_SSID);
  WiFi.disconnect();
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
}

bool fetchStatus(unsigned long now) {
  if (WiFi.status() != WL_CONNECTED) return false;

  HTTPClient http;
  const String url = "http://" + String(ASTRA_PI_HOST) + ":" +
                     String(ASTRA_PI_PORT) + ASTRA_STATUS_PATH;
  http.setConnectTimeout(ASTRA_HTTP_TIMEOUT_MS);
  http.setTimeout(ASTRA_HTTP_TIMEOUT_MS);

  if (!http.begin(url)) {
    Serial.println("HTTP client could not open status URL");
    return false;
  }

  const int responseCode = http.GET();
  if (responseCode != HTTP_CODE_OK) {
    Serial.printf("Status request failed: HTTP %d\n", responseCode);
    http.end();
    return false;
  }

  StatusPayload next;
  const bool valid = parsePayload(http.getString(), next);
  http.end();
  if (!valid) return false;

  if (next.timestamp != lastRemoteTimestamp) {
    lastRemoteTimestamp = next.timestamp;
    lastFreshPayloadMs = now;
  }

  payload = next;
  screenDirty = true;
  Serial.printf("Status updated: %s (%s)\n", payload.status.c_str(),
                payload.source.c_str());
  return true;
}

bool acknowledgeMessage(uint32_t messageId) {
  HTTPClient http;
  const String url = "http://" + String(ASTRA_PI_HOST) + ":" +
                     String(ASTRA_PI_PORT) + ASTRA_MESSAGES_PATH + "/" +
                     String(messageId) + "/ack";
  http.setConnectTimeout(ASTRA_HTTP_TIMEOUT_MS);
  http.setTimeout(ASTRA_HTTP_TIMEOUT_MS);
  if (!http.begin(url)) return false;

  http.addHeader("Content-Type", "application/json");
  const String body = "{\"recipient_id\":\"" + String(ASTRA_ASTRONAUT_ID) +
                      "\"}";
  const int responseCode = http.POST(body);
  http.end();
  if (responseCode != HTTP_CODE_OK) {
    Serial.printf("Message acknowledgement failed: HTTP %d\n", responseCode);
    return false;
  }
  Serial.printf("Message #%lu acknowledged\n",
                static_cast<unsigned long>(messageId));
  return true;
}

bool fetchMessage(unsigned long now) {
  if (WiFi.status() != WL_CONNECTED) return false;

  HTTPClient http;
  const String url = "http://" + String(ASTRA_PI_HOST) + ":" +
                     String(ASTRA_PI_PORT) + ASTRA_MESSAGES_PATH +
                     "?recipient_id=" + ASTRA_ASTRONAUT_ID +
                     "&pending_only=true&limit=1";
  http.setConnectTimeout(ASTRA_HTTP_TIMEOUT_MS);
  http.setTimeout(ASTRA_HTTP_TIMEOUT_MS);
  if (!http.begin(url)) return false;

  const int responseCode = http.GET();
  if (responseCode != HTTP_CODE_OK) {
    Serial.printf("Message request failed: HTTP %d\n", responseCode);
    http.end();
    return false;
  }

  JsonDocument document;
  const DeserializationError error = deserializeJson(document, http.getString());
  http.end();
  if (error || !document.is<JsonArray>()) {
    Serial.println("Message response is not a valid JSON array");
    return false;
  }

  JsonArray messages = document.as<JsonArray>();
  if (messages.isNull() || messages.size() == 0) return true;
  JsonObject message = messages[0];
  if (!message["id"].is<uint32_t>() ||
      !message["priority"].is<const char *>() ||
      !message["text"].is<const char *>()) {
    Serial.println("Message response is missing required fields");
    return false;
  }

  const uint32_t messageId = message["id"].as<uint32_t>();
  if (messageId != lastMessageId) {
    activeMessage.id = messageId;
    activeMessage.priority = message["priority"].as<String>();
    activeMessage.text = message["text"].as<String>();
    lastMessageId = messageId;
    lastMessageReceivedMs = now;
    screenDirty = true;
    Serial.printf("Message #%lu received: %s\n",
                  static_cast<unsigned long>(messageId),
                  activeMessage.priority.c_str());
  }
  acknowledgeMessage(messageId);
  return true;
}

}  // namespace

void setup() {
  Serial.begin(115200);
  pinMode(TFT_BL, OUTPUT);
  digitalWrite(TFT_BL, TFT_BACKLIGHT_ON);

  display.init();
  display.setRotation(1);
  display.fillScreen(TFT_BLACK);

  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  lastWifiAttemptMs = millis() - ASTRA_WIFI_RETRY_MS;
  render();
}

void loop() {
  const unsigned long now = millis();
  connectWifiIfNeeded(now);

  if (now - lastPollMs >= ASTRA_POLL_INTERVAL_MS) {
    lastPollMs = now;
    fetchStatus(now);
  }

  if (activeMessage.id == 0 &&
      now - lastMessagePollMs >= ASTRA_MESSAGE_POLL_INTERVAL_MS) {
    lastMessagePollMs = now;
    fetchMessage(now);
  }

  if (activeMessage.id != 0 &&
      now - lastMessageReceivedMs >= ASTRA_MESSAGE_DISPLAY_MS) {
    activeMessage = CrewMessage{};
    screenDirty = true;
  }

  const bool neverReceivedPayload = lastFreshPayloadMs == 0;
  const bool payloadIsStale = now - lastFreshPayloadMs > ASTRA_STALE_AFTER_MS;
  if (neverReceivedPayload || payloadIsStale) {
    markOffline(WiFi.status() == WL_CONNECTED ? "Backpack data is stale."
                                              : "Backpack not connected.");
  }

  if (screenDirty) render();
  delay(10);
}
