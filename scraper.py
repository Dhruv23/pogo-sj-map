# PHASE 2:
# iOS Place Sheet Pack

# (sliding bottom sheet like Apple Maps)

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
HTML_TEMPLATE = r"""
<!DOCTYPE html>
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
  "https://tiles.stadiamaps.com/tiles/alidade_smooth/{z}/{x}/{y}{r}.png",
  { maxZoom: 20 }
);
const darkLayer = L.tileLayer(
  "https://tiles.stadiamaps.com/tiles/alidade_smooth_dark/{z}/{x}/{y}{r}.png",
  { maxZoom: 20 }
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

/* ---------------- POKEMON MARKERS ---------------- */
let markers = [];
let countdownData = [];

function updateMap() {
  navigator.geolocation.getCurrentPosition(
    pos => {
      lastUserLat = pos.coords.latitude;
      lastUserLon = pos.coords.longitude;

      if (!userMarker) {
        userMarker = L.marker([lastUserLat, lastUserLon], { icon: pulseIcon }).addTo(map);
      } else {
        userMarker.setLatLng([lastUserLat, lastUserLon]);
      }

      fetchSpawns(lastUserLat, lastUserLon);
    },
    err => {
      fetchSpawns(null, null);
    }
  );
}

/* Format countdown as M:SS */
function formatCountdown(ms) {
  let sec = Math.floor(ms / 1000);
  let m = Math.floor(sec / 60);
  let s = sec % 60;
  return m + ":" + String(s).padStart(2, "0");
}

function fetchSpawns(userLat, userLon) {
  fetch("/data")
    .then(res => res.json())
    .then(spawns => {
      markers.forEach(m => map.removeLayer(m));
      markers = [];
      countdownData = [];

      const now = Date.now();

      spawns.forEach(spawn => {
        const expireTime = new Date(spawn.expires).getTime();
        const countdownStr = formatCountdown(expireTime - now);

        /* ---- Pokémon marker (original size) ---- */
        const pokeIcon = L.icon({
          iconUrl: spawn.icon,
          iconSize: [48, 48],
          iconAnchor: [24, 24]
        });

        const pokeMarker = L.marker([spawn.lat, spawn.lon], { icon: pokeIcon }).addTo(map);
        markers.push(pokeMarker);

        /* ---- Countdown marker ---- */
        const countdownMarker = L.marker([spawn.lat, spawn.lon], {
          icon: L.divIcon({
            className: "",
            html: "<div class='countdown-bubble'>" + countdownStr + "</div>",
            iconSize: [60, 30],
            iconAnchor: [30, 40]
          })
        }).addTo(map);

        markers.push(countdownMarker);

        /* store countdown for live ticking */
        countdownData.push({
          marker: countdownMarker,
          expires: expireTime
        });

        /* ---- Popup with Apple Maps routing ---- */
        let mapsUrl =
          "https://maps.apple.com/?saddr=" +
          encodeURIComponent((userLat ?? "Current Location") + "," + (userLon ?? "")) +
          "&daddr=" +
          encodeURIComponent(spawn.lat + "," + spawn.lon);

        pokeMarker.bindPopup(
          "<b>" + spawn.name + "</b><br>" +
          "Expires at: " + new Date(spawn.expires).toLocaleTimeString() + "<br><br>" +
          "<a href='" + mapsUrl + "' target='_blank' style='color:#0a84ff'>Open in Apple Maps →</a>"
        );
      });
    });
}

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
    command = (
        f'curl -s -H "Authorization: {user_token}" '
        f'"https://discord.com/api/v10/channels/{channel_id}/messages?limit=100"'
    )
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"curl error: {result.stderr}")
        return []
    return json.loads(result.stdout)


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

        time_str = time_match.group(1).strip()
        now = datetime.datetime.now(local_tz)

        expire_dt = datetime.datetime.strptime(time_str, "%I:%M:%S %p").replace(
            year=now.year, month=now.month, day=now.day
        )
        expire_dt = local_tz.localize(expire_dt)

        # Fix 24h misalignment from Discord embed quirks
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
