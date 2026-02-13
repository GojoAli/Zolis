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
const params = new URLSearchParams(window.location.search);
const sessionId = params.get("session_id") || localStorage.getItem("zolis_session_id");

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
const COLLECT_INTERVAL_MS = 2500;

function formatCoord(value) {
  if (Number.isFinite(value)) {
    return value.toFixed(5);
  }
  return "--";
}

function updateStatus(isLive) {
  statusDot.classList.toggle("live", isLive);
  statusText.textContent = isLive ? "Flux MQTT actif" : "En attente de données";
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
    await fetch(`${backend}/collect`, { method: "POST" });
  } catch (err) {
    // ignore; latest data endpoint remains authoritative for UI display
  } finally {
    collectInFlight = false;
  }
}

async function refresh() {
  try {
    triggerCollect().catch(() => {});
    const response = await fetch(`${backend}/latest`, { cache: "no-store" });
    const data = await response.json();
    if (!data || !data.gps) {
      updateStatus(false);
      return;
    }

    const lat = Number(data.gps.latitude);
    const lng = Number(data.gps.longitude);
    if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
      updateStatus(false);
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

    updateStatus(true);
    lastUpdate = Date.now();
    if (sessionId) {
      loadSessionMeta();
    }
  } catch (err) {
    updateStatus(false);
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
