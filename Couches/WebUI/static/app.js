const statusDot = document.getElementById("statusDot");
const statusText = document.getElementById("statusText");
const coordsEl = document.getElementById("coords");
const tempEl = document.getElementById("temperature");
const humiditeEl = document.getElementById("humidite");
const pressionEl = document.getElementById("pression");
const battEl = document.getElementById("batterie");
const tsEl = document.getElementById("timestamp");

const map = L.map("map", { zoomControl: false }).setView([0, 0], 2);
L.control.zoom({ position: "bottomright" }).addTo(map);

L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19,
  attribution: "&copy; OpenStreetMap contributors",
}).addTo(map);

const marker = L.marker([0, 0]).addTo(map);
const path = L.polyline([], { color: "#47e1d6", weight: 3 }).addTo(map);

let lastUpdate = 0;

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

async function refresh() {
  try {
    const response = await fetch("/api/latest", { cache: "no-store" });
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
    tsEl.textContent = data.ts
      ? new Date(data.ts * 1000).toLocaleTimeString("fr-FR")
      : "--";

    updateStatus(true);
    lastUpdate = Date.now();
  } catch (err) {
    updateStatus(false);
  }
}

setInterval(refresh, 1000);
refresh();
