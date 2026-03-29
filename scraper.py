
# Then…

# PHASE 3:
# Smart Filtering Pack

# Then…

# PHASE 4:
# Map Intelligence Pack (heatmap, clustering, routing — minus nearest rare finder)

# Then…

# PHASE 5:
# Compass Mode + Proximity Alerts (with toggle buttons)


import subprocess
import json
import re
import os
import datetime
import requests
from flask import Flask, jsonify, render_template_string
from dotenv import load_dotenv
import pytz

local_tz = pytz.timezone("America/Los_Angeles")

load_dotenv()
app = Flask(__name__)
channel_id = "348769770671308800"
user_token = os.getenv("DISCORD_TOKEN")
assets_dir = "static/assets"
os.makedirs(assets_dir, exist_ok=True)
active_spawns = []

# =======================
# Apple Maps Pro Pack UI
# =======================
HTML_TEMPLATE = r"""<!DOCTYPE html>
<html>
<head>
  <title>Live Pokémon Map</title>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0">

  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="https://unpkg.com/leaflet/dist/leaflet.css" />

  <style>
    html, body {
      height: 100%;
      margin: 0;
      padding: 0;
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      background: #000;
      overflow: hidden;
    }

    #map {
      height: 100vh;
      width: 100vw;
    }

    /* Light / Dark glass toggle */
    .mode-toggle {
      position: fixed;
      top: 12px;
      right: 12px;
      z-index: 9999;
      padding: 6px 12px;
      border-radius: 999px;
      font-size: 13px;
      font-weight: 500;
      background: rgba(30, 30, 30, 0.55);
      color: #f5f5f7;
      backdrop-filter: blur(18px);
      border: 1px solid rgba(255, 255, 255, 0.18);
      cursor: pointer;
      user-select: none;
      transition: 0.2s ease;
    }
    .mode-toggle span { opacity: 0.6; }
    .mode-toggle .mode-active { opacity: 1; }

    /* Compass */
    .compass-btn {
      position: fixed;
      top: 58px;
      right: 12px;
      z-index: 9999;
      width: 38px;
      height: 38px;
      background: rgba(30,30,30,0.45);
      backdrop-filter: blur(18px);
      border-radius: 10px;
      border: 1px solid rgba(255,255,255,0.18);
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      color: white;
      font-size: 18px;
    }

    /* Recenter */
    .recenter-btn {
      position: fixed;
      top: 104px;
      right: 12px;
      z-index: 9999;
      width: 38px;
      height: 38px;
      background: rgba(30,30,30,0.45);
      backdrop-filter: blur(18px);
      border-radius: 10px;
      border: 1px solid rgba(255,255,255,0.18);
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      color: white;
      font-size: 20px;
    }

    /* Pulsing location dot */
    .pulse-dot {
      width: 16px;
      height: 16px;
      background: #007aff;
      border-radius: 50%;
      box-shadow: 0 0 12px rgba(0,122,255,0.9);
      animation: pulse 2s infinite;
      border: 2px solid white;
    }
    @keyframes pulse {
      0% { transform: scale(1); opacity: 0.9; }
      50% { transform: scale(1.25); opacity: 0.6; }
      100% { transform: scale(1); opacity: 0.9; }
    }

    /* Countdown bubble */
    .countdown-bubble {
      font-size: 12px;
      font-weight: 600;
      padding: 3px 6px;
      border-radius: 6px;
      background: rgba(0,0,0,0.85);
      color: #fff;
      box-shadow: 0 2px 6px rgba(0,0,0,0.35);
      text-align: center;
      min-width: 32px;
    }

    /* ========== Liquid Glass Bottom Sheet ========== */

    #sheetBackdrop {
      position: fixed;
      inset: 0;
      background: rgba(0,0,0,0.28);
      opacity: 0;
      pointer-events: none;
      transition: opacity 0.25s ease;
      z-index: 9998;
    }
    #sheetBackdrop.visible {
      opacity: 1;
      pointer-events: auto;
    }

    #infoSheet {
      position: fixed;
      left: 0;
      right: 0;
      bottom: 0;
      margin: 0 auto;
      max-width: 640px;
      transform: translateY(100%);
      opacity: 0;
      transition: transform 0.28s cubic-bezier(0.22, 0.61, 0.36, 1), opacity 0.25s ease;
      z-index: 9999;
      padding: 12px 16px 20px;
      border-radius: 24px 24px 0 0;
      background:
        linear-gradient(135deg, rgba(255,255,255,0.92), rgba(245,245,247,0.88));
      backdrop-filter: blur(40px) saturate(1.4);
      box-shadow:
        0 -18px 45px rgba(0,0,0,0.55),
        inset 0 1px 0 rgba(255,255,255,0.8);
      border: 1px solid rgba(255,255,255,0.7);
    }
    #infoSheet.open {
      transform: translateY(0);
      opacity: 1;
    }

    .sheet-handle {
      width: 40px;
      height: 4px;
      border-radius: 999px;
      margin: 4px auto 10px;
      background: linear-gradient(to right, rgba(255,255,255,0.9), rgba(255,255,255,0.65));
      box-shadow: 0 1px 0 rgba(255,255,255,0.9);
    }

    .sheet-header {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 8px;
    }
    .sheet-icon-wrap {
      width: 44px;
      height: 44px;
      border-radius: 18px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: radial-gradient(circle at 30% 10%, rgba(255,255,255,0.85), rgba(255,255,255,0.1));
      box-shadow:
        0 4px 10px rgba(0,0,0,0.25),
        inset 0 0 0 0.5px rgba(255,255,255,0.9);
    }
    #sheetIcon {
      width: 38px;
      height: 38px;
      object-fit: contain;
    }
    .sheet-title-block {
      display: flex;
      flex-direction: column;
      gap: 2px;
    }
    #sheetName {
      font-size: 18px;
      font-weight: 600;
      letter-spacing: -0.01em;
      color: #111;
    }
    #sheetMeta {
      font-size: 13px;
      color: #666;
    }

    .sheet-section {
      margin-top: 10px;
      padding-top: 8px;
      border-top: 1px solid rgba(0,0,0,0.06);
      display: flex;
      flex-direction: column;
      gap: 6px;
    }

    .sheet-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 14px;
      color: #333;
    }
    .sheet-label {
      color: #555;
    }
    .sheet-value {
      font-weight: 500;
    }

    #sheetCountdown {
      font-variant-numeric: tabular-nums;
    }

    .sheet-actions {
      margin-top: 12px;
      display: flex;
      gap: 8px;
    }
    #sheetRouteBtn {
      flex: 1;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      padding: 10px 14px;
      border-radius: 999px;
      border: none;
      outline: none;
      background: linear-gradient(135deg, #0a84ff, #4facff);
      color: #fff;
      font-size: 15px;
      font-weight: 600;
      text-decoration: none;
      box-shadow: 0 6px 16px rgba(10,132,255,0.45);
    }

    /* ========== FILTER PANEL (Smart Filtering Pack) ========== */
    #filterPanel {
      position: fixed;
      top: 60px;
      left: 12px;
      width: 260px;
      max-width: 75vw;
      z-index: 9999;
      padding: 10px 12px 12px;
      border-radius: 18px;
      background: radial-gradient(circle at 0% 0%, rgba(255,255,255,0.9), rgba(240,242,247,0.85));
      backdrop-filter: blur(24px);
      box-shadow:
        0 10px 25px rgba(0,0,0,0.4),
        inset 0 0 0 0.5px rgba(255,255,255,0.9);
      border: 1px solid rgba(255,255,255,0.85);
      transition: transform 0.25s ease, opacity 0.25s ease;
      transform: scale(0.9);
      opacity: 0;
      pointer-events: none;
    }

    /* When open */
    #filterPanel.open {
      transform: scale(1);
      opacity: 1;
      pointer-events: auto;
    }

    /* FILTERS BUTTON */
    .filters-toggle-btn {
      position: fixed;
      top: 12px;
      left: 12px;
      z-index: 9999;
      padding: 8px 14px;
      border-radius: 12px;
      background: rgba(30,30,30,0.55);
      color: #fff;
      font-size: 14px;
      font-weight: 600;
      backdrop-filter: blur(18px);
      border: 1px solid rgba(255,255,255,0.2);
      cursor: pointer;
      user-select: none;
      transition: 0.2s;
    }
    .filters-toggle-btn:active {
      transform: scale(0.96);
    }

    .filter-header-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 6px;
    }
    .filter-title {
      font-size: 14px;
      font-weight: 600;
      color: #111;
    }
    .filter-clear-btn {
      border: none;
      background: transparent;
      color: #0a84ff;
      font-size: 12px;
      font-weight: 500;
      cursor: pointer;
      padding: 2px 4px;
    }

    .filter-group {
      margin-top: 6px;
    }

    .filter-label {
      font-size: 12px;
      font-weight: 500;
      color: #555;
      margin-bottom: 4px;
      display: block;
    }

    .filter-input {
      width: 100%;
      padding: 5px 8px;
      font-size: 12px;
      border-radius: 10px;
      border: 1px solid rgba(0,0,0,0.08);
      outline: none;
      background: rgba(255,255,255,0.9);
    }

    .chip-row {
      display: flex;
      flex-wrap: wrap;
      gap: 4px;
      margin-top: 4px;
    }
    .chip {
      border: none;
      border-radius: 999px;
      padding: 4px 8px;
      font-size: 11px;
      background: rgba(255,255,255,0.9);
      color: #333;
      cursor: pointer;
      box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }
    .chip-active {
      background: #0a84ff;
      color: #fff;
      box-shadow: 0 2px 6px rgba(10,132,255,0.5);
    }

    .toggle-row {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 12px;
      color: #333;
      margin-top: 4px;
    }
    .toggle-row input[type="checkbox"] {
      accent-color: #0a84ff;
    }
  </style>
</head>

<body>

<div id="map"></div>

<div class="mode-toggle" id="modeToggle">
  <span id="lightLabel" class="mode-active">Light</span> / <span id="darkLabel">Dark</span>
</div>

<div class="compass-btn" id="compassBtn">🧭</div>
<div class="recenter-btn" id="recenterBtn">⌖</div>

<div id="filtersToggleBtn" class="filters-toggle-btn">Filters ⚙️</div>

<!-- Smart Filtering Pack panel -->
<div id="filterPanel">
  <div class="filter-header-row">
    <span class="filter-title">Filters</span>
    <button id="clearFiltersBtn" class="filter-clear-btn">Reset</button>
  </div>

  <div class="filter-group">
    <label class="filter-label" for="speciesSearch">Species</label>
    <input id="speciesSearch" class="filter-input" type="text" placeholder="Search Pokémon">
    <div id="speciesChips" class="chip-row"></div>
  </div>

  <div class="filter-group">
    <label class="filter-label">Distance</label>
    <div id="distanceChips" class="chip-row">
      <button class="chip chip-active" data-distance="any">Any</button>
      <button class="chip" data-distance="500">≤ 500 m</button>
      <button class="chip" data-distance="1000">≤ 1 km</button>
      <button class="chip" data-distance="3000">≤ 3 km</button>
    </div>
  </div>

  <div class="filter-group">
    <label class="filter-label">Map clutter</label>
    <label class="toggle-row">
      <input type="checkbox" id="toggleIcons" checked>
      <span>Show Pokémon icons</span>
    </label>
    <label class="toggle-row">
      <input type="checkbox" id="toggleCountdowns" checked>
      <span>Show countdown badges</span>
    </label>
  </div>
</div>

<!-- Liquid glass bottom sheet (hidden until a Pokémon is tapped) -->
<div id="sheetBackdrop"></div>
<div id="infoSheet">
  <div class="sheet-handle"></div>
  <div class="sheet-header">
    <div class="sheet-icon-wrap">
      <img id="sheetIcon" src="" alt="Pokémon">
    </div>
    <div class="sheet-title-block">
      <div id="sheetName">Pokémon</div>
      <div id="sheetMeta"></div>
    </div>
  </div>

  <div class="sheet-section">
    <div class="sheet-row">
      <span class="sheet-label">Expires in</span>
      <span id="sheetCountdown" class="sheet-value">--:--</span>
    </div>
    <div class="sheet-row">
      <span class="sheet-label">Distance</span>
      <span id="sheetDistance" class="sheet-value">–</span>
    </div>
  </div>

  <div class="sheet-actions">
    <a id="sheetRouteBtn" href="#" target="_blank">Open in Apple Maps</a>
  </div>
</div>

{% raw %}
<script src="https://unpkg.com/leaflet/dist/leaflet.js"></script>
<script>
/* ---------------- MAP ---------------- */
let map = L.map('map', {
  zoomControl: false,
  inertia: true,
  inertiaDeceleration: 3000,
  inertiaMaxSpeed: 1500,
}).setView([37.32, -121.88], 14);

L.control.zoom({ position: 'bottomright' }).addTo(map);

/* ---------------- TILES ---------------- */
const lightLayer = L.tileLayer(
  "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
  {
    maxZoom: 20,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
    subdomains: 'abcd'
  }
);
const darkLayer = L.tileLayer(
  "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
  {
    maxZoom: 20,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
    subdomains: 'abcd'
  }
);

let isDark = false;
lightLayer.addTo(map);

/* ---------------- USER LOCATION ---------------- */
const pulseIcon = L.divIcon({
  className: "",
  html: "<div class='pulse-dot'></div>",
  iconSize: [20, 20],
  iconAnchor: [10, 10]
});

let userMarker = null;
let lastUserLat = null;
let lastUserLon = null;

/* ---------------- FILTER STATE ---------------- */
let lastSpawns = [];
let markers = [];
let countdownData = [];
let selectedSpawn = null; // for bottom sheet countdown

let filterState = {
  species: [],            // array of names
  distance: "any",        // "any" or numeric string
  showIcons: true,
  showCountdowns: true
};

const FILTER_STORAGE_KEY = "pokeFiltersV1";

/* ---------------- DOM REFS (Filters + Sheet) ---------------- */
const speciesSearchInput = document.getElementById("speciesSearch");
const speciesChipsEl = document.getElementById("speciesChips");
const distanceChipsEl = document.getElementById("distanceChips");
const toggleIconsEl = document.getElementById("toggleIcons");
const toggleCountdownsEl = document.getElementById("toggleCountdowns");
const clearFiltersBtn = document.getElementById("clearFiltersBtn");

const filterPanel = document.getElementById("filterPanel");
const filtersToggleBtn = document.getElementById("filtersToggleBtn");

const sheet = document.getElementById("infoSheet");
const sheetBackdrop = document.getElementById("sheetBackdrop");
const sheetName = document.getElementById("sheetName");
const sheetMeta = document.getElementById("sheetMeta");
const sheetIcon = document.getElementById("sheetIcon");
const sheetCountdownEl = document.getElementById("sheetCountdown");
const sheetDistanceEl = document.getElementById("sheetDistance");
const sheetRouteBtn = document.getElementById("sheetRouteBtn");

/* ---------------- UTIL: Load/save filter state ---------------- */
function loadFilterState() {
  try {
    const saved = localStorage.getItem(FILTER_STORAGE_KEY);
    if (!saved) return;
    const parsed = JSON.parse(saved);
    if (parsed && typeof parsed === "object") {
      if (Array.isArray(parsed.species)) filterState.species = parsed.species;
      if (parsed.distance) filterState.distance = parsed.distance;
      if (typeof parsed.showIcons === "boolean") filterState.showIcons = parsed.showIcons;
      if (typeof parsed.showCountdowns === "boolean") filterState.showCountdowns = parsed.showCountdowns;
    }
  } catch (e) {
    console.warn("Failed to load filter state:", e);
  }
}

function saveFilterState() {
  try {
    localStorage.setItem(FILTER_STORAGE_KEY, JSON.stringify(filterState));
  } catch (e) {
    console.warn("Failed to save filter state:", e);
  }
}

/* ---------------- COUNTDOWN + DIST UTILS ---------------- */
function formatCountdown(ms) {
  let sec = Math.floor(ms / 1000);
  let m = Math.floor(sec / 60);
  let s = sec % 60;
  return m + ":" + String(s).padStart(2, "0");
}

function computeDistanceMeters(lat1, lon1, lat2, lon2) {
  const R = 6371000;
  const toRad = x => x * Math.PI / 180;
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) *
    Math.sin(dLon / 2) * Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

/* ---------------- BOTTOM SHEET CONTROL ---------------- */
function openSheet(spawn) {
  selectedSpawn = spawn;

  sheetName.textContent = spawn.name;
  sheetIcon.src = spawn.icon || "";
  sheetCountdownEl.textContent = formatCountdown(spawn.expireTime - Date.now());

  sheetMeta.textContent = "Wild spawn";

  if (lastUserLat != null && lastUserLon != null) {
    const distM = computeDistanceMeters(lastUserLat, lastUserLon, spawn.lat, spawn.lon);
    if (distM < 1000) {
      sheetDistanceEl.textContent = Math.round(distM) + " m away";
    } else {
      sheetDistanceEl.textContent = (distM / 1000).toFixed(1) + " km away";
    }
  } else {
    sheetDistanceEl.textContent = "Unknown";
  }

  const mapsUrl =
    "https://maps.apple.com/?saddr=Current%20Location&daddr=" +
    encodeURIComponent(spawn.lat + "," + spawn.lon);
  sheetRouteBtn.href = mapsUrl;

  sheet.classList.add("open");
  sheetBackdrop.classList.add("visible");
}

function closeSheet() {
  selectedSpawn = null;
  sheet.classList.remove("open");
  sheetBackdrop.classList.remove("visible");
}

sheetBackdrop.addEventListener("click", closeSheet);

/* ---------------- FILTERS COLLAPSIBLE BUTTON ---------------- */
let filtersOpen = false;

filtersToggleBtn.addEventListener("click", () => {
  filtersOpen = !filtersOpen;
  if (filtersOpen) {
    filterPanel.classList.add("open");
    filtersToggleBtn.textContent = "Filters ❌";
  } else {
    filterPanel.classList.remove("open");
    filtersToggleBtn.textContent = "Filters ⚙️";
  }
});

/* ---------------- FILTER UI: species chips ---------------- */
function buildSpeciesChips() {
  if (!speciesChipsEl) return;
  speciesChipsEl.innerHTML = "";

  const term = (speciesSearchInput.value || "").trim().toLowerCase();
  const uniqueNames = Array.from(new Set(lastSpawns.map(s => s.name))).sort();

  uniqueNames.forEach(name => {
    if (term && !name.toLowerCase().includes(term)) return;

    const btn = document.createElement("button");
    btn.className = "chip";
    if (filterState.species.includes(name)) {
      btn.classList.add("chip-active");
    }
    btn.textContent = name;
    btn.dataset.name = name;
    btn.addEventListener("click", () => {
      const idx = filterState.species.indexOf(name);
      if (idx === -1) {
        filterState.species.push(name);
      } else {
        filterState.species.splice(idx, 1);
      }
      saveFilterState();
      buildSpeciesChips();
      renderSpawns();
    });
    speciesChipsEl.appendChild(btn);
  });
}

/* ---------------- FILTER UI: distance chips ---------------- */
function initDistanceChipsUI() {
  if (!distanceChipsEl) return;
  const buttons = distanceChipsEl.querySelectorAll(".chip");
  buttons.forEach(btn => {
    const val = btn.getAttribute("data-distance") || "any";
    if (val === filterState.distance) {
      btn.classList.add("chip-active");
    } else {
      btn.classList.remove("chip-active");
    }
    btn.addEventListener("click", () => {
      filterState.distance = val;
      saveFilterState();
      buttons.forEach(b => b.classList.remove("chip-active"));
      btn.classList.add("chip-active");
      renderSpawns();
    });
  });
}

/* ---------------- FILTER UI: toggles ---------------- */
function initToggleUI() {
  if (toggleIconsEl) {
    toggleIconsEl.checked = filterState.showIcons;
    toggleIconsEl.addEventListener("change", () => {
      filterState.showIcons = toggleIconsEl.checked;
      saveFilterState();
      renderSpawns();
    });
  }
  if (toggleCountdownsEl) {
    toggleCountdownsEl.checked = filterState.showCountdowns;
    toggleCountdownsEl.addEventListener("change", () => {
      filterState.showCountdowns = toggleCountdownsEl.checked;
      saveFilterState();
      renderSpawns();
    });
  }
}

/* ---------------- FILTER UI: search + reset ---------------- */
if (speciesSearchInput) {
  speciesSearchInput.addEventListener("input", () => {
    buildSpeciesChips();
  });
}

if (clearFiltersBtn) {
  clearFiltersBtn.addEventListener("click", () => {
    filterState = {
      species: [],
      distance: "any",
      showIcons: true,
      showCountdowns: true
    };
    saveFilterState();
    if (toggleIconsEl) toggleIconsEl.checked = true;
    if (toggleCountdownsEl) toggleCountdownsEl.checked = true;
    if (distanceChipsEl) {
      distanceChipsEl.querySelectorAll(".chip").forEach(btn => {
        const val = btn.getAttribute("data-distance") || "any";
        if (val === "any") btn.classList.add("chip-active");
        else btn.classList.remove("chip-active");
      });
    }
    buildSpeciesChips();
    renderSpawns();
  });
}

/* ---------------- RENDER SPAWNS USING FILTERS ---------------- */
function renderSpawns() {
  markers.forEach(m => map.removeLayer(m));
  markers = [];
  countdownData = [];

  const now = Date.now();
  const speciesSet = new Set(filterState.species || []);
  const distanceLimit =
    filterState.distance === "any" ? Infinity : parseFloat(filterState.distance);

  lastSpawns.forEach(spawn => {
    // species filter
    if (speciesSet.size > 0 && !speciesSet.has(spawn.name)) return;

    // distance filter
    if (distanceLimit !== Infinity && lastUserLat != null && lastUserLon != null) {
      const distM = computeDistanceMeters(lastUserLat, lastUserLon, spawn.lat, spawn.lon);
      if (distM > distanceLimit) return;
    }

    const expireTime = spawn.expireTime;

    // Pokémon icon marker
    let pokeMarker = null;
    if (filterState.showIcons) {
      const pokeIcon = L.icon({
        iconUrl: spawn.icon,
        iconSize: [48, 48],
        iconAnchor: [24, 24]
      });
      pokeMarker = L.marker([spawn.lat, spawn.lon], { icon: pokeIcon }).addTo(map);
      markers.push(pokeMarker);

      pokeMarker.on("click", () => {
        openSheet(spawn);
      });
    }

    // Countdown marker
    if (filterState.showCountdowns) {
      const initialStr = formatCountdown(expireTime - now);
      const countdownMarker = L.marker([spawn.lat, spawn.lon], {
        icon: L.divIcon({
          className: "",
          html: "<div class='countdown-bubble'>" + initialStr + "</div>",
          iconSize: [60, 30],
          iconAnchor: [30, 40]
        })
      }).addTo(map);
      markers.push(countdownMarker);
      countdownData.push({
        marker: countdownMarker,
        expires: expireTime
      });
    }
  });
}

/* ---------------- FETCH & CACHE SPAWNS ---------------- */
function fetchSpawns(userLat, userLon) {
  fetch("/data")
    .then(res => res.json())
    .then(spawns => {
      const now = Date.now();
      lastSpawns = spawns.map(spawn => ({
        name: spawn.name,
        lat: spawn.lat,
        lon: spawn.lon,
        icon: spawn.icon,
        expiresIso: spawn.expires,
        expireTime: new Date(spawn.expires).getTime()
      }));
      buildSpeciesChips();
      renderSpawns();
    });
}

/* ---------------- MAIN UPDATE LOOP ---------------- */
function updateMap() {
  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(
      pos => {
        lastUserLat = pos.coords.latitude;
        lastUserLon = pos.coords.longitude;

        if (!userMarker) {
          userMarker = L.marker([lastUserLat, lastUserLon], { icon: pulseIcon }).addTo(map);
          map.setView([lastUserLat, lastUserLon], 14);
        } else {
          userMarker.setLatLng([lastUserLat, lastUserLon]);
        }

        fetchSpawns(lastUserLat, lastUserLon);
      },
      err => {
        console.warn("Geolocation error:", err);
        fetchSpawns(null, null);
      },
      { enableHighAccuracy: true, timeout: 5000, maximumAge: 10000 }
    );
  } else {
    console.warn("Geolocation not supported or unavailable.");
    fetchSpawns(null, null);
  }
}

/* ---------------- INITIALIZE FILTER STATE & UI ---------------- */
loadFilterState();
initDistanceChipsUI();
initToggleUI();

/* Fetch new spawn data every 10 sec */
updateMap();
setInterval(updateMap, 10000);

/* ---------------- LIVE COUNTDOWN REFRESH ---------------- */
setInterval(() => {
  const now = Date.now();

  countdownData.forEach(entry => {
    const msRemaining = entry.expires - now;
    if (!entry.marker._icon) return;

    if (msRemaining <= 0) {
      entry.marker._icon.innerHTML =
        "<div class='countdown-bubble'>Expired</div>";
      return;
    }

    entry.marker._icon.innerHTML =
      "<div class='countdown-bubble'>" + formatCountdown(msRemaining) + "</div>";
  });

  // Update sheet countdown too
  if (selectedSpawn && sheetCountdownEl) {
    const msRemaining = selectedSpawn.expireTime - now;
    if (msRemaining <= 0) {
      sheetCountdownEl.textContent = "Expired";
    } else {
      sheetCountdownEl.textContent = formatCountdown(msRemaining);
    }
  }
}, 1000);

/* ---------------- COMPASS ---------------- */
const compassBtn = document.getElementById("compassBtn");
if (window.DeviceOrientationEvent) {
  window.addEventListener("deviceorientation", e => {
    const heading = e.webkitCompassHeading || e.alpha;
    if (heading != null)
      compassBtn.style.transform = "rotate(" + heading + "deg)";
  });
}

/* ---------------- RECENTER ---------------- */
document.getElementById("recenterBtn").addEventListener("click", () => {
  if (userMarker)
    map.flyTo(userMarker.getLatLng(), 15);
});

/* ---------------- LIGHT/DARK MODE ---------------- */
const modeToggle = document.getElementById("modeToggle");
const lightLabel = document.getElementById("lightLabel");
const darkLabel = document.getElementById("darkLabel");

modeToggle.addEventListener("click", () => {
  if (isDark) {
    map.removeLayer(darkLayer);
    lightLayer.addTo(map);
    lightLabel.classList.add("mode-active");
    darkLabel.classList.remove("mode-active");
  } else {
    map.removeLayer(lightLayer);
    darkLayer.addTo(map);
    darkLabel.classList.add("mode-active");
    lightLabel.classList.remove("mode-active");
  }
  isDark = !isDark;
});
</script>
{% endraw %}

</body>
</html>
"""






# ============================
# Flask Routes + Discord Logic
# ============================

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/data')
def data():
    update_spawns()
    now = datetime.datetime.now(local_tz)
    valid = []

    for s in active_spawns:
        if s["expires"] > now:
            s_copy = s.copy()
            s_copy["expires"] = s_copy["expires"].isoformat()
            valid.append(s_copy)

    return jsonify(valid)


# =======================
# Discord Message Fetching
# =======================

def fetch_recent_messages():
    url = f"https://discord.com/api/v9/channels/{channel_id}/messages?limit=100"
    
    # Ensure the token is treated as a string and handle missing tokens gracefully
    auth_header = str(user_token) if user_token else ""
    
    headers = {
        "Authorization": auth_header
    }
    
    try:
        response = requests.get(url, headers=headers)
        
        # This will trigger the except block below if Discord returns a 4xx or 5xx error
        response.raise_for_status() 
        
        return response.json()
        
    except requests.exceptions.RequestException as e:
        print(f"🚨 HTTP Error fetching Discord messages: {e}")
        if e.response is not None:
            # This will print the actual HTML or text Discord sent back (e.g., "401: Unauthorized")
            print(f"Discord replied with: {e.response.text}") 
        return []
        
    except ValueError as e:
        print(f"🚨 JSON Decode Error: {e}")
        print(f"Raw output was: {response.text}")
        return []


def extract_data(message):
    try:
        embed = message["embeds"][0]
        title = embed.get("title", "")
        description = embed.get("description", "")

        name_match = re.match(r'100% ([A-Za-z\-]+)', title)
        if not name_match:
            return None

        name = name_match.group(1).lower()

        coord_match = (
            re.search(r'coordinate=([-+]?\d+\.\d+),([-+]?\d+\.\d+)', description)
            or re.search(r'q=([-+]?\d+\.\d+),([-+]?\d+\.\d+)', description)
        )
        if not coord_match:
            return None

        lat, lon = map(float, coord_match.groups())

        time_match = re.search(r'End: ([0-9:APM ]+)', description)
        if not time_match:
            return None

        # Parse expiration datetime from message timestamp directly
        # Example timestamp: '2026-03-28T07:29:05.343000+00:00'
        msg_timestamp = message.get("timestamp")
        if not msg_timestamp:
            return None

        # Parse the ISO format string correctly.
        # Python 3.11's fromisoformat handles standard Z/+00:00 well.
        # But we can also use datetime.strptime if needed.
        # It's an ISO8601 string, we can use datetime.datetime.fromisoformat
        dt_utc = datetime.datetime.fromisoformat(msg_timestamp)
        now = datetime.datetime.now(local_tz)

        # The discord timestamp is when the message was sent.
        # The embed says: End: 12:57:49 AM (**28m 44s**)
        # Let's extract the exact remaining time from the string
        duration_match = re.search(r'\*\*(?:(\d+)m\s*)?(?:(\d+)s)?\*\*', description)
        if duration_match:
            mins = int(duration_match.group(1) or 0)
            secs = int(duration_match.group(2) or 0)
            expire_dt = dt_utc + datetime.timedelta(minutes=mins, seconds=secs)
            expire_dt = expire_dt.astimezone(local_tz)
        else:
            # Fallback to older logic just in case
            time_str = time_match.group(1).strip()
            expire_dt = datetime.datetime.strptime(time_str, "%I:%M:%S %p").replace(
                year=now.year, month=now.month, day=now.day
            )
            expire_dt = local_tz.localize(expire_dt)
            # Fix 24h misalignment
            diff = expire_dt - now
            if datetime.timedelta(hours=23, minutes=59) < diff < datetime.timedelta(hours=24, minutes=1):
                expire_dt -= datetime.timedelta(days=1)

        sprite_path = download_sprite(name)

        return {
            "name": name.title(),
            "lat": lat,
            "lon": lon,
            "expires": expire_dt,
            "expires_str": expire_dt.strftime("%a, %d %b %Y %I:%M:%S %p %Z"),
            "icon": sprite_path
        }

    except Exception as e:
        print(f"Parsing error: {e}")
        return None


def download_sprite(name):
    sprite_file = f"{assets_dir}/{name}.png"

    if os.path.exists(sprite_file):
        return f"/{sprite_file}"

    try:
        poke_api = f"https://pokeapi.co/api/v2/pokemon/{name}"
        poke_data = requests.get(poke_api).json()
        poke_id = poke_data["id"]

        sprite_url = (
            f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/{poke_id}.png"
        )

        img_data = requests.get(sprite_url).content
        with open(sprite_file, "wb") as f:
            f.write(img_data)

        return f"/{sprite_file}"

    except Exception:
        return "https://cdn-icons-png.flaticon.com/512/188/188987.png"


def update_spawns():
    global active_spawns
    new_spawns = []

    messages = fetch_recent_messages()
    for msg in messages:
        parsed = extract_data(msg)
        if parsed:
            # Avoid duplicates by coordinates
            if all(
                existing["lat"] != parsed["lat"] or existing["lon"] != parsed["lon"]
                for existing in active_spawns
            ):
                new_spawns.append(parsed)

    now = datetime.datetime.now(local_tz)
    active_spawns = [s for s in active_spawns if s["expires"] > now] + new_spawns


if __name__ == '__main__':
    print("🌍 Open https://localhost:5000 in your browser")
    app.run(ssl_context=('localhost.pem', 'localhost-key.pem'))
