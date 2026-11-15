#pragma once

#include <Arduino.h>

constexpr char ASTRA_PI_HOST[] = "10.0.201.67";
constexpr uint16_t ASTRA_PI_PORT = 8000;
constexpr char ASTRA_STATUS_PATH[] = "/api/v1/status";
constexpr char ASTRA_MESSAGES_PATH[] = "/api/v1/messages";
constexpr char ASTRA_ASTRONAUT_ID[] = "astronaut-1";

constexpr unsigned long ASTRA_POLL_INTERVAL_MS = 1000;
constexpr unsigned long ASTRA_MESSAGE_POLL_INTERVAL_MS = 1500;
constexpr unsigned long ASTRA_MESSAGE_DISPLAY_MS = 10000;
constexpr unsigned long ASTRA_HTTP_TIMEOUT_MS = 1500;
constexpr unsigned long ASTRA_STALE_AFTER_MS = 5000;
constexpr unsigned long ASTRA_WIFI_RETRY_MS = 5000;
