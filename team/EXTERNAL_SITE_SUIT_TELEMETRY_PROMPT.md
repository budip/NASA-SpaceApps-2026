# Prompt for the external-site implementation agent

Copy the prompt below into the agent working on the external Central Station
site. The ASTRA Pi backend is already deployed; do not modify the Pi-hosted
dashboard or wearable UI for this task.

---

Add ASTRA suit-environment telemetry to the existing external Central Station
site as a strictly additive feature. Preserve every existing page, component,
route, data model, style, and behavior. Do not delete, rename, or repurpose any
current implementation.

The Raspberry Pi is currently available on the private LAN at:

```text
http://10.0.201.67:8000
```

API references:

```text
GET http://10.0.201.67:8000/api/v1/status
GET http://10.0.201.67:8000/api/v1/history?limit=120
GET http://10.0.201.67:8000/openapi.json
Swagger: http://10.0.201.67:8000/docs
```

Implementation requirements:

1. Extend the external site's existing ASTRA data types/parser with these
   additive objects from `/api/v1/status`:

```json
{
  "suit_pressure": {
    "timestamp": "2026-11-15T00:11:53.288612Z",
    "pressure_hpa": 293.7,
    "pressure_psi": 4.26,
    "status": "NOMINAL",
    "source": "simulated",
    "thresholds": {
      "critical_low_hpa": 248.0,
      "warn_low_hpa": 276.0,
      "nominal_hpa": 296.0,
      "warn_high_hpa": 365.0,
      "critical_high_hpa": 455.0
    },
    "flags": [
      "simulated_suit_pressure",
      "sense_hat_pressure_is_ambient_not_suit_pressure",
      "prototype_thresholds_not_certified_alarms"
    ]
  },
  "suit_temperature": {
    "timestamp": "2026-11-15T00:11:53.288612Z",
    "temperature_c": 24.0,
    "status": "COMFORT",
    "source": "simulated",
    "thresholds": {
      "critical_low_c": 10.0,
      "comfort_low_c": 20.0,
      "comfort_high_c": 30.0,
      "critical_high_c": 43.0
    },
    "flags": [
      "simulated_suit_air_temperature",
      "critical_limits_adapted_from_internal_touch_temperature",
      "prototype_thresholds_not_certified_alarms"
    ]
  },
  "biometrics": {
    "heart_rate_bpm": 73.4,
    "heart_rate_status": "NOMINAL",
    "heart_rate_thresholds": {
      "warn_high_bpm": 120.0,
      "critical_high_bpm": 140.0
    },
    "source": "simulated"
  }
}
```

2. Add new suit-pressure and suit-air-temperature UI elements to the external
   site only. Clearly show the value, unit, returned status, and returned
   source. Label simulated data visibly. Use the API's returned status instead
   of creating different alarm calculations in the frontend.

3. Treat every new object and value as optional. If a field is missing, null,
   invalid, or the Pi is unreachable, render `Unavailable`/the site's existing
   offline state. Never replace missing data with zero and never imply that
   stale data is safe.

4. Keep these concepts separate:

   - `sensors.pressure_hpa` is real Sense HAT ambient barometric pressure and
     may be around 900–1020 hPa on Earth. It is not suit pressure.
   - `suit_pressure.pressure_hpa` is the explicitly simulated suit-pressure
     feed, normally around 296 hPa.
   - `sensors.temperature_c` is the Sense HAT/backpack ambient reading and may
     be biased upward by Pi heat.
   - `suit_temperature.temperature_c` is explicitly simulated suit-air
     temperature.
   - `biometrics.body_temperature_c` is simulated body temperature and is not
     suit-air temperature.

5. Supported status values:

   - Suit pressure: `CRITICAL_LOW`, `WARN_LOW`, `NOMINAL`, `WARN_HIGH`,
     `CRITICAL_HIGH`, `UNAVAILABLE`.
   - Suit temperature: `CRITICAL_LOW`, `WARN_LOW`, `COMFORT`, `WARN_HIGH`,
     `CRITICAL_HIGH`, `UNAVAILABLE`.
   - Heart rate: `UNAVAILABLE`, `NOMINAL`, `WARN_HIGH`, `CRITICAL_HIGH`.

   Reuse the site's existing semantic colors: normal/comfort green, warning
   amber, critical red, unavailable grey. Always include text so meaning does
   not depend on color.

6. Preserve the existing overall ASTRA state. Do not overwrite the top-level
   `status`, `score`, or `summary` with suit status. Suit telemetry is an
   additional subsystem display.

7. For trend data, use `/api/v1/history?limit=120`. It returns the same
   `suit_pressure`, `suit_temperature`, and biometric fields in chronological
   order. Do not invent client-side history when persisted Pi history is
   available.

8. Network integration:

   - The browser/client must be on the same private LAN as the Pi.
   - Prefer an existing server-side API/proxy layer in the external site to
     request the Pi. Direct browser requests from a different origin can be
     blocked by CORS, and an HTTPS page cannot safely fetch an HTTP Pi endpoint
     due to mixed-content rules.
   - Do not expose port 8000 to the public internet. There is currently no API
     authentication.
   - Keep the Pi address configurable; DHCP may change it.
   - Use a short telemetry timeout (about five seconds), no-store caching, and
     the site's existing retry/backoff behavior.

9. Include these honest prototype notes near the new UI or its information
   tooltip:

   - Suit values and biometrics are simulated hackathon data, not measured by
     the Sense HAT.
   - Thresholds are prototype interpretations, not certified NASA alarm
     limits, medical guidance, or flight-qualified safety logic.
   - The 10/43 °C outer temperature limits are adapted from internal
     touch-temperature material and are not validated suit-air alarm limits.

10. Test without changing existing behavior:

    - valid current payload;
    - missing suit objects (backward-compatible server);
    - null values;
    - every returned status value;
    - Pi unreachable/stale response;
    - responsive layout;
    - existing UI and tests still pass.

Deliver the smallest additive patch, list the files changed, and show evidence
that the existing external site still works. Do not make any changes to the
Pi-hosted dashboard, wearable firmware, backend routes, or existing payload
fields.

