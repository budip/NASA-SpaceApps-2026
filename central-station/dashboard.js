"use strict";

const STATUS_SYMBOLS = {
  LEARNING: "…",
  NORMAL: "✓",
  CAUTION: "!",
  ALERT: "!!",
  OFFLINE: "×",
};

const SENSOR_META = {
  temperature_c: { label: "Temperature", unit: "°C", decimals: 1 },
  humidity_pct: { label: "Humidity", unit: "%", decimals: 1 },
  pressure_hpa: { label: "Pressure", unit: "hPa", decimals: 1 },
};

const TASK_PRIORITY_WEIGHT = {
  INFO: 0,
  ADVISORY: 1,
  CAUTION: 2,
  ALERT: 3,
};

const state = {
  history: [],
  latest: null,
  sensor: "temperature_c",
  connected: false,
  crew: [],
  messages: [],
};

const byId = (id) => document.getElementById(id);

function formatReading(value, decimals = 1) {
  return Number.isFinite(value) ? value.toFixed(decimals) : "--";
}

function updateVector(prefix, vector, fields = ["x", "y", "z"], decimals = 3) {
  fields.forEach((field) => {
    byId(`${prefix}-${field}`).textContent = formatReading(vector?.[field], decimals);
  });
}

function hasFiniteSensorValue(value) {
  if (Number.isFinite(value)) return true;
  if (!value || typeof value !== "object") return false;
  return Object.values(value).some(hasFiniteSensorValue);
}

function sampleAge(timestamp) {
  const seconds = Math.max(0, (Date.now() - new Date(timestamp).getTime()) / 1000);
  if (!Number.isFinite(seconds)) return "--";
  if (seconds < 2) return "NOW";
  if (seconds < 60) return `${Math.round(seconds)} SEC`;
  return `${Math.floor(seconds / 60)} MIN`;
}

function setConnection(connected) {
  state.connected = connected;
  const pill = byId("connection-pill");
  pill.classList.toggle("pill-online", connected);
  pill.classList.toggle("pill-offline", !connected);
  pill.classList.remove("pill-connecting");
  byId("connection-label").textContent = connected ? "BACKPACK LINK" : "LINK LOST";
  ["node-pi", "node-link"].forEach((id) => {
    byId(id).classList.toggle("online", connected);
  });
}

function setOffline() {
  setConnection(false);
  const card = byId("status-card");
  card.dataset.status = "OFFLINE";
  byId("status-symbol").textContent = STATUS_SYMBOLS.OFFLINE;
  byId("status-label").textContent = "OFFLINE";
  byId("status-summary").textContent = "Central station cannot reach the backpack computer.";
  byId("source-badge").textContent = "STALE DATA";
  byId("health-status").textContent = "OFFLINE";
  byId("health-status").className = "health-offline";
  byId("imu-availability").textContent = "STALE";
  byId("imu-availability").classList.remove("imu-live");
  byId("biometric-source").textContent = "STALE";
  byId("task-source").textContent = "STALE";
}

function updateStatus(payload) {
  state.latest = payload;
  setConnection(true);
  const status = STATUS_SYMBOLS[payload.status] ? payload.status : "OFFLINE";
  const card = byId("status-card");
  card.dataset.status = status;
  byId("status-symbol").textContent = STATUS_SYMBOLS[status];
  byId("status-label").textContent = status;
  byId("status-summary").textContent = payload.summary || "No local summary available.";
  byId("source-badge").textContent = String(payload.source || "unknown").toUpperCase();
  byId("score-value").textContent = Number.isFinite(payload.score)
    ? payload.score.toFixed(2)
    : "--";
  byId("sample-age").textContent = sampleAge(payload.timestamp);

  const sensors = payload.sensors || {};
  byId("temperature-value").textContent = formatReading(sensors.temperature_c);
  byId("humidity-value").textContent = formatReading(sensors.humidity_pct);
  byId("pressure-value").textContent = formatReading(sensors.pressure_hpa);
  updateVector("acceleration", sensors.acceleration_g);
  updateVector("gyroscope", sensors.gyroscope_rps);
  updateVector("magnetic", sensors.magnetic_uT, ["x", "y", "z"], 2);
  updateVector(
    "orientation",
    sensors.orientation_deg,
    ["pitch", "roll", "yaw"],
    1,
  );
  const imuAvailable = [
    sensors.acceleration_g,
    sensors.gyroscope_rps,
    sensors.magnetic_uT,
    sensors.orientation_deg,
  ].some(hasFiniteSensorValue);
  byId("imu-availability").textContent = imuAvailable ? "LIVE" : "UNAVAILABLE";
  byId("imu-availability").classList.toggle("imu-live", imuAvailable);

  const biometrics = payload.biometrics || {};
  const bloodPressure = biometrics.blood_pressure || {};
  byId("heart-rate-value").textContent = formatReading(
    biometrics.heart_rate_bpm,
    0,
  );
  byId("blood-pressure-value").textContent = [
    formatReading(bloodPressure.systolic_mm_hg, 0),
    formatReading(bloodPressure.diastolic_mm_hg, 0),
  ].join("/");
  byId("oxygen-saturation-value").textContent = formatReading(
    biometrics.oxygen_saturation_pct,
    1,
  );
  byId("body-temperature-value").textContent = formatReading(
    biometrics.body_temperature_c,
    2,
  );
  byId("biometric-source").textContent = String(
    biometrics.source || "unavailable",
  ).toUpperCase();

  renderTasks(Array.isArray(payload.tasks) ? payload.tasks : []);
  byId("node-sensor").classList.toggle(
    "online",
    hasFiniteSensorValue(sensors),
  );
  updateMetricChanges();
}

function renderTasks(tasks) {
  const list = byId("task-list");
  list.replaceChildren();
  byId("task-count").textContent = `${tasks.length} ${tasks.length === 1 ? "TASK" : "TASKS"}`;

  if (!tasks.length) {
    const empty = document.createElement("li");
    empty.className = "task-empty";
    empty.textContent = "No simulated mission tasks available.";
    list.append(empty);
    byId("task-panel").dataset.priority = "INFO";
    byId("task-source").textContent = "UNAVAILABLE";
    return;
  }

  const highestPriority = tasks.reduce((highest, task) => (
    (TASK_PRIORITY_WEIGHT[task.priority] ?? 0) >
    (TASK_PRIORITY_WEIGHT[highest] ?? 0)
      ? task.priority
      : highest
  ), "INFO");
  byId("task-panel").dataset.priority = highestPriority;
  byId("task-source").textContent = String(
    tasks[0]?.source || "unavailable",
  ).toUpperCase();

  tasks.slice(0, 3).forEach((task) => {
    const item = document.createElement("li");
    item.className = "task-item";
    item.dataset.priority = task.priority || "INFO";

    const badges = document.createElement("div");
    const priority = document.createElement("span");
    priority.className = "task-priority";
    priority.textContent = task.priority || "INFO";
    const category = document.createElement("span");
    category.className = "task-category";
    category.textContent = String(task.category || "system").toUpperCase();
    badges.append(priority, category);

    const text = document.createElement("p");
    text.textContent = task.text || "No task text available.";
    const id = document.createElement("small");
    id.textContent = task.id || "TASK ---";
    item.append(badges, text, id);
    list.append(item);
  });
}

function updateMetricChanges() {
  const pairs = [
    ["temperature_c", "temperature-change"],
    ["humidity_pct", "humidity-change"],
    ["pressure_hpa", "pressure-change"],
  ];
  pairs.forEach(([sensor, elementId]) => {
    const values = state.history
      .map((item) => item.sensors?.[sensor])
      .filter(Number.isFinite);
    const element = byId(elementId);
    if (values.length < 2) {
      element.textContent = "Collecting baseline";
      return;
    }
    const delta = values.at(-1) - values.at(-2);
    if (Math.abs(delta) < 0.05) {
      element.textContent = "Stable since prior sample";
      return;
    }
    element.textContent = `${delta > 0 ? "↑" : "↓"} ${Math.abs(delta).toFixed(2)} since prior sample`;
  });
}

function updateHealth(health) {
  const label = String(health.status || "degraded").toUpperCase();
  const element = byId("health-status");
  element.textContent = label;
  element.className = label === "OK" ? "health-ok" : "health-degraded";
  byId("service-version").textContent = health.version || "--";
  byId("sensor-mode").textContent = health.sensor_mode || "--";
  byId("baseline-size").textContent = `${health.baseline_samples ?? "--"} samples`;
  byId("failure-count").textContent = String(health.consecutive_failures ?? "--");
}

function chartValues(sensor) {
  return state.history
    .map((item) => ({
      time: new Date(item.timestamp),
      value: item.sensors?.[sensor],
    }))
    .filter((item) => Number.isFinite(item.value) && !Number.isNaN(item.time.getTime()));
}

function drawChart() {
  const svg = byId("trend-chart");
  const empty = byId("chart-empty");
  const meta = SENSOR_META[state.sensor];
  const values = chartValues(state.sensor);
  if (values.length < 2) {
    svg.innerHTML = "";
    empty.hidden = false;
    byId("chart-stat").textContent = "--";
    byId("chart-range").textContent = "LAST -- MIN";
    return;
  }

  empty.hidden = true;
  const width = 820;
  const height = 280;
  const margin = { top: 22, right: 62, bottom: 32, left: 16 };
  const plotWidth = width - margin.left - margin.right;
  const plotHeight = height - margin.top - margin.bottom;
  const rawMin = Math.min(...values.map((item) => item.value));
  const rawMax = Math.max(...values.map((item) => item.value));
  const spread = Math.max(rawMax - rawMin, state.sensor === "pressure_hpa" ? 0.4 : 0.2);
  const min = rawMin - spread * 0.18;
  const max = rawMax + spread * 0.18;
  const x = (index) => margin.left + (index / (values.length - 1)) * plotWidth;
  const y = (value) => margin.top + (1 - (value - min) / (max - min)) * plotHeight;
  const points = values.map((item, index) => `${x(index)},${y(item.value)}`).join(" ");
  const areaPoints = `${margin.left},${margin.top + plotHeight} ${points} ${margin.left + plotWidth},${margin.top + plotHeight}`;

  const grid = [0, 0.25, 0.5, 0.75, 1].map((fraction) => {
    const gridY = margin.top + fraction * plotHeight;
    const label = max - fraction * (max - min);
    return `<line class="chart-grid" x1="${margin.left}" y1="${gridY}" x2="${margin.left + plotWidth}" y2="${gridY}"></line>
      <text class="chart-label" x="${width - 4}" y="${gridY + 4}" text-anchor="end">${label.toFixed(meta.decimals)}</text>`;
  }).join("");

  const latest = values.at(-1);
  const description = `${meta.label} ranged from ${rawMin.toFixed(meta.decimals)} to ${rawMax.toFixed(meta.decimals)} ${meta.unit} across ${values.length} samples.`;
  svg.innerHTML = `
    <title id="chart-title">${meta.label} history</title>
    <desc id="chart-description">${description}</desc>
    <defs>
      <linearGradient id="chart-area-gradient" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="#52d9ef" stop-opacity="0.22"></stop>
        <stop offset="100%" stop-color="#52d9ef" stop-opacity="0"></stop>
      </linearGradient>
    </defs>
    ${grid}
    <polygon class="chart-area" points="${areaPoints}"></polygon>
    <polyline class="chart-line" points="${points}"></polyline>
    <circle class="chart-endpoint" cx="${x(values.length - 1)}" cy="${y(latest.value)}" r="5"></circle>
    <text class="chart-label" x="${margin.left}" y="${height - 4}">${values[0].time.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</text>
    <text class="chart-label" x="${margin.left + plotWidth}" y="${height - 4}" text-anchor="end">${latest.time.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</text>`;

  const elapsedMinutes = Math.max(
    1,
    Math.round((latest.time.getTime() - values[0].time.getTime()) / 60000),
  );
  byId("chart-range").textContent = `LAST ${elapsedMinutes} MIN`;
  byId("chart-stat").textContent = `${meta.label.toUpperCase()} ${latest.value.toFixed(meta.decimals)} ${meta.unit}`;
}

function renderHistory() {
  byId("history-count").textContent = `${state.history.length} records`;
  const rows = state.history.slice(-8).reverse();
  byId("sample-rows").innerHTML = rows.length
    ? rows.map((item) => {
        const sensors = item.sensors || {};
        const time = new Date(item.timestamp).toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        });
        return `<tr>
          <td>${time}</td>
          <td><span class="table-state" data-state="${item.status}">${item.status}</span></td>
          <td>${formatReading(sensors.temperature_c)} °C</td>
          <td>${formatReading(sensors.humidity_pct)} %</td>
          <td>${formatReading(sensors.pressure_hpa)} hPa</td>
          <td>${String(item.source || "--").toUpperCase()}</td>
        </tr>`;
      }).join("")
    : `<tr><td colspan="6" class="empty-row">Waiting for telemetry…</td></tr>`;
  updateMetricChanges();
  drawChart();
}

async function requestJson(url, options = {}) {
  const response = await fetch(url, { cache: "no-store", ...options });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}

function crewName(recipientId) {
  return state.crew.find((member) => member.id === recipientId)?.name
    || recipientId;
}

function renderOutbox() {
  const list = byId("message-outbox-list");
  byId("message-outbox-count").textContent = `${state.messages.length} messages`;
  list.replaceChildren();
  if (!state.messages.length) {
    const empty = document.createElement("li");
    empty.className = "message-empty";
    empty.textContent = "No messages sent during this mission.";
    list.append(empty);
    return;
  }

  state.messages.slice(-8).reverse().forEach((message) => {
    const item = document.createElement("li");
    item.className = "message-item";
    item.dataset.priority = message.priority;

    const heading = document.createElement("div");
    heading.className = "message-item-heading";
    const recipient = document.createElement("strong");
    recipient.textContent = crewName(message.recipient_id);
    const status = document.createElement("span");
    status.className = `delivery-status delivery-${message.status}`;
    status.textContent = String(message.status || "queued").toUpperCase();
    heading.append(recipient, status);

    const text = document.createElement("p");
    text.textContent = message.text;
    const meta = document.createElement("small");
    const time = new Date(message.created_at).toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
    meta.textContent = `${message.priority} · #${message.id} · ${time}`;
    item.append(heading, text, meta);
    list.append(item);
  });
}

async function loadCrew() {
  try {
    const crew = await requestJson("/api/v1/crew");
    state.crew = Array.isArray(crew) ? crew : [];
    const select = byId("message-recipient");
    select.replaceChildren();
    state.crew.forEach((member) => {
      const option = document.createElement("option");
      option.value = member.id;
      option.textContent = member.name;
      select.append(option);
    });
    select.disabled = state.crew.length === 0;
    renderOutbox();
  } catch (error) {
    console.warn("Crew request failed", error);
    byId("message-feedback").textContent = "Crew roster is unavailable.";
    byId("message-feedback").dataset.state = "error";
  }
}

async function pollMessages() {
  try {
    const messages = await requestJson("/api/v1/messages?limit=50");
    state.messages = Array.isArray(messages) ? messages : [];
    renderOutbox();
  } catch (error) {
    console.warn("Message outbox request failed", error);
  }
}

async function sendMessage(event) {
  event.preventDefault();
  const button = byId("message-send");
  const feedback = byId("message-feedback");
  const text = byId("message-text").value.trim();
  const recipientId = byId("message-recipient").value;
  if (!recipientId || !text) return;

  button.disabled = true;
  feedback.dataset.state = "sending";
  feedback.textContent = "Queueing message on the Pi…";
  try {
    const message = await requestJson("/api/v1/messages", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        recipient_id: recipientId,
        priority: byId("message-priority").value,
        text,
      }),
    });
    byId("message-text").value = "";
    byId("message-count").textContent = "0 / 240";
    feedback.dataset.state = "success";
    feedback.textContent = `Message #${message.id} queued for ${crewName(recipientId)}.`;
    await pollMessages();
  } catch (error) {
    console.warn("Message send failed", error);
    feedback.dataset.state = "error";
    feedback.textContent = "Message was not queued. Check the backpack connection.";
  } finally {
    button.disabled = false;
  }
}

async function pollStatus() {
  try {
    updateStatus(await requestJson("/api/v1/status"));
  } catch (error) {
    console.warn("Status request failed", error);
    setOffline();
  }
}

async function pollHealth() {
  try {
    updateHealth(await requestJson("/health"));
  } catch (error) {
    console.warn("Health request failed", error);
    byId("health-status").textContent = "OFFLINE";
    byId("health-status").className = "health-offline";
  }
}

async function pollHistory() {
  try {
    const history = await requestJson("/api/v1/history?limit=120");
    state.history = Array.isArray(history) ? history : [];
    renderHistory();
  } catch (error) {
    console.warn("History request failed", error);
  }
}

function updateClock() {
  const now = new Date();
  const clock = byId("station-clock");
  clock.dateTime = now.toISOString();
  clock.textContent = now.toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
  if (state.latest) byId("sample-age").textContent = sampleAge(state.latest.timestamp);
}

document.querySelectorAll(".trend-tab").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".trend-tab").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    state.sensor = button.dataset.sensor;
    drawChart();
  });
});

byId("message-form").addEventListener("submit", sendMessage);
byId("message-text").addEventListener("input", (event) => {
  byId("message-count").textContent = `${event.target.value.length} / 240`;
});

updateClock();
pollStatus();
pollHealth();
pollHistory();
loadCrew();
pollMessages();
setInterval(updateClock, 1000);
setInterval(pollStatus, 1000);
setInterval(pollHealth, 5000);
setInterval(pollHistory, 5000);
setInterval(pollMessages, 2000);
