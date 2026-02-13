const statusDot = document.getElementById("statusDot");
const statusText = document.getElementById("statusText");
const coordsEl = document.getElementById("coords");
const tempEl = document.getElementById("temperature");
const humiditeEl = document.getElementById("humidite");
const pressionEl = document.getElementById("pression");
const battEl = document.getElementById("batterie");
const distanceEl = document.getElementById("distance");
const distanceTotalEl = document.getElementById("distanceTotal");
const tsEl = document.getElementById("timestamp");
const loadHistoryBtn = document.getElementById("loadHistory");
const collectNowBtn = document.getElementById("collectNow");

const backend = "/api/backend";
const sessionId = window.SESSION_ID || null;

const map = L.map("map", { zoomControl: false }).setView([0, 0], 2);
L.control.zoom({ position: "bottomright" }).addTo(map);

L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19,
  attribution: "&copy; OpenStreetMap contributors",
}).addTo(map);

const marker = L.marker([0, 0]).addTo(map);
const path = L.polyline([], { color: "#47e1d6", weight: 3 }).addTo(map);

let lastUpdate = 0;
let collectInFlight = false;
let lastCollectTs = 0;
let lastCollectError = "";
const COLLECT_INTERVAL_MS = 2500;

function formatCoord(value) {
  if (Number.isFinite(value)) {
    return value.toFixed(5);
  }
  return "--";
}

function updateStatus(state, message) {
  statusDot.classList.toggle("live", state === "live");
  statusText.textContent = message;
}

function setFallbackCards() {
  coordsEl.textContent = "--";
  tempEl.textContent = "--";
  humiditeEl.textContent = "--";
  pressionEl.textContent = "--";
  battEl.textContent = "--";
  distanceEl.textContent = "--";
  tsEl.textContent = "--";
}

async function parseJsonSafe(response) {
  const text = await response.text();
  if (!text) {
    return {};
  }
  try {
    return JSON.parse(text);
  } catch (err) {
    return { detail: text };
  }
}

async function triggerCollect(force = false) {
  const now = Date.now();
  if (!force && now - lastCollectTs < COLLECT_INTERVAL_MS) {
    return;
  }
  if (collectInFlight) {
    return;
  }
  collectInFlight = true;
  lastCollectTs = now;
  try {
    const res = await fetch(`${backend}/collect`, { method: "POST" });
    if (!res.ok) {
      const payload = await parseJsonSafe(res);
      const reason = payload.detail || payload.error || `HTTP ${res.status}`;
      if (res.status === 401 || reason.toLowerCase().includes("session expired")) {
        window.location.href = "/login";
        return;
      }
      lastCollectError = reason;
      return;
    }
    lastCollectError = "";
  } catch (err) {
    lastCollectError = "backend indisponible";
  } finally {
    collectInFlight = false;
  }
}

async function refresh() {
  try {
    triggerCollect().catch(() => {});
    const response = await fetch(`${backend}/latest`, { cache: "no-store" });
    if (!response.ok) {
      const payload = await parseJsonSafe(response);
      const reason = (payload.detail || payload.error || "").toLowerCase();
      if (response.status === 401 || reason.includes("session")) {
        window.location.href = "/login";
        return;
      }
      updateStatus("error", "Backend indisponible");
      setFallbackCards();
      return;
    }
    const data = await parseJsonSafe(response);
    if (!data || !data.gps) {
      updateStatus("idle", "Aucune donnée capteur reçue");
      setFallbackCards();
      return;
    }

    const lat = Number(data.gps.latitude);
    const lng = Number(data.gps.longitude);
    if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
      updateStatus("idle", "Position invalide");
      setFallbackCards();
      return;
    }

    marker.setLatLng([lat, lng]);
    path.addLatLng([lat, lng]);
    if (Date.now() - lastUpdate > 4000) {
      map.setView([lat, lng], 15, { animate: true });
    } else {
      map.panTo([lat, lng], { animate: true });
    }

    coordsEl.textContent = `${formatCoord(lat)}, ${formatCoord(lng)}`;
    tempEl.textContent = data.temperature !== null && data.temperature !== undefined
      ? `${Number(data.temperature).toFixed(1)} °C`
      : "--";
    humiditeEl.textContent = data.humidite !== null && data.humidite !== undefined
      ? `${Number(data.humidite).toFixed(1)} %`
      : "--";
    pressionEl.textContent = data.pression !== null && data.pression !== undefined
      ? `${Number(data.pression).toFixed(0)} hPa`
      : "--";
    battEl.textContent = data.batterie !== null && data.batterie !== undefined
      ? `${Number(data.batterie).toFixed(0)} %`
      : "--";
    distanceEl.textContent = data.distance_m !== null && data.distance_m !== undefined
      ? `${Number(data.distance_m).toFixed(1)} m`
      : "--";
    tsEl.textContent = data.ts
      ? new Date(data.ts * 1000).toLocaleTimeString("fr-FR")
      : "--";

    const statusMessage = lastCollectError
      ? `Flux partiel: ${lastCollectError}`
      : "Flux capteurs actif";
    updateStatus("live", statusMessage);
    lastUpdate = Date.now();
    if (sessionId) {
      loadSessionMeta();
    }
  } catch (err) {
    updateStatus("error", "Erreur réseau avec le backend");
    setFallbackCards();
  }
}

async function loadHistory() {
  if (!sessionId) {
    alert("Aucune session active. Enregistre un coureur.");
    return;
  }
  try {
    const res = await fetch(`${backend}/sessions/${sessionId}/measures`);
    if (!res.ok) {
      throw new Error("history");
    }
    const measures = await res.json();
    const latlngs = measures.map((m) => [m.lat, m.lon]);
    path.setLatLngs(latlngs);
    if (latlngs.length > 0) {
      map.fitBounds(path.getBounds(), { padding: [30, 30] });
    }
  } catch (err) {
    alert("Impossible de charger l'historique.");
  }
}

if (loadHistoryBtn) {
  loadHistoryBtn.addEventListener("click", loadHistory);
}

async function collectNow() {
  try {
    await triggerCollect(true);
    if (lastCollectError) {
      alert(`Collect impossible: ${lastCollectError}`);
    }
  } catch (err) {
    alert("Collect impossible.");
  }
}

if (collectNowBtn) {
  collectNowBtn.addEventListener("click", collectNow);
}

async function loadSessionMeta() {
  if (!sessionId) {
    return;
  }
  try {
    const res = await fetch(`${backend}/sessions/${sessionId}`);
    if (!res.ok) {
      return;
    }
    const session = await res.json();
    distanceTotalEl.textContent = `Total: ${Number(session.total_distance_m).toFixed(1)} m`;
  } catch (err) {
    // ignore
  }
}

setInterval(refresh, 1000);
refresh();
loadSessionMeta();
if (sessionId) {
  loadHistory();
}
