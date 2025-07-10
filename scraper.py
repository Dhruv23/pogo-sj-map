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

# HTML with live location + reload every 60s
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
  <title>Live Pokémon Map</title>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>html, body, #map { height: 100%; margin: 0; }</style>
  <link rel="stylesheet" href="https://unpkg.com/leaflet/dist/leaflet.css" />
</head>
<body>
<div id="map"></div>
{% raw %}
<script src="https://unpkg.com/leaflet/dist/leaflet.js"></script>
<script>
let map = L.map('map').setView([37.32, -121.88], 14);
L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors'
}).addTo(map);

let markers = [];
let userMarker = null;

function updateMap() {
  navigator.geolocation.getCurrentPosition(pos => {
    const userLat = pos.coords.latitude;
    const userLon = pos.coords.longitude;

    if (!userMarker) {
      userMarker = L.marker([userLat, userLon], {
        icon: L.icon({
          iconUrl: 'https://cdn-icons-png.flaticon.com/512/149/149060.png',
          iconSize: [32, 32]
        }),
        title: "You are here"
      }).addTo(map);
    } else {
      userMarker.setLatLng([userLat, userLon]);
    }

    fetch('/data')
      .then(res => res.json())
      .then(spawns => {
        markers.forEach(m => map.removeLayer(m));
        markers = [];
        spawns.forEach(spawn => {
          const icon = L.icon({
            iconUrl: spawn.icon,
            iconSize: [48, 48]
          });
          const expireDate = new Date(spawn.expires).toLocaleTimeString("en-US", {
            hour: "numeric",
            minute: "2-digit",
            second: "2-digit",
            timeZone: "America/Los_Angeles",
            timeZoneName: "short"
          });
          const popup = `<b>${spawn.name}</b><br>Expires at: ${expireDate}<br><a href="https://maps.apple.com/?saddr=${userLat},${userLon}&daddr=${spawn.lat},${spawn.lon}" target="_blank">Apple Maps Route</a>`;

          const marker = L.marker([spawn.lat, spawn.lon], { icon }).bindPopup(popup).addTo(map);
          markers.push(marker);
        });
      });
  });
}

updateMap();
setInterval(updateMap, 60000);
</script>
{% endraw %}
</body>
</html>
"""


@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/data')
def data():
    update_spawns()
    now = datetime.datetime.now(pytz.timezone("America/Los_Angeles"))
    valid = []
    for s in active_spawns:
        print(f"NOW: {now}, checking spawn: {s['name']} expires {s['expires']}")
        if s["expires"] > now:
            # clone and convert for frontend
            s_copy = s.copy()
            s_copy["expires"] = s_copy["expires"].isoformat()
            valid.append(s_copy)

    return jsonify(valid)


def fetch_recent_messages():
    command = f'curl -s -H "Authorization: {user_token}" "https://discord.com/api/v10/channels/{channel_id}/messages?limit=100"'
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

        coord_match = re.search(r'coordinate=([-+]?\d+\.\d+),([-+]?\d+\.\d+)', description) or \
                      re.search(r'q=([-+]?\d+\.\d+),([-+]?\d+\.\d+)', description)
        if not coord_match:
            return None
        lat, lon = map(float, coord_match.groups())

        time_match = re.search(r'End: ([0-9:APM ]+)', description)
        if not time_match:
            return None

        time_str = time_match.group(1).strip()
        now = datetime.datetime.now(pytz.timezone("America/Los_Angeles"))
        expire_dt = datetime.datetime.strptime(time_str, "%I:%M:%S %p").replace(year=now.year, month=now.month, day=now.day)
        expire_dt = local_tz.localize(expire_dt)
        # Fix cases where Discord timestamp might be mis-parsed as next day
        # If the expiration is exactly 24 hours ahead, shift it back
        diff = expire_dt - now
        if datetime.timedelta(hours=23, minutes=59) < diff < datetime.timedelta(hours=24, minutes=1):
            print(f"Adjusting future-drifted time back 24h: {expire_dt} -> ", end="")
            expire_dt -= datetime.timedelta(days=1)
            print(f"{expire_dt}")

        sprite_path = download_sprite(name)
        return {
          "name": name.title(),
          "lat": lat,
          "lon": lon,
          "expires": expire_dt,  # keep as datetime for filtering
          "expires_str": expire_dt.strftime("%a, %d %b %Y %I:%M:%S %p %Z"),  # for display
          "icon": sprite_path
      }


    except Exception as e:
        print(f"Error parsing: {e}")
        return None

def download_sprite(name):
    sprite_file = f"{assets_dir}/{name}.png"
    if os.path.exists(sprite_file):
        return f"/{sprite_file}"
    try:
        poke_api = f"https://pokeapi.co/api/v2/pokemon/{name}"
        poke_data = requests.get(poke_api).json()
        poke_id = poke_data["id"]
        sprite_url = f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/{poke_id}.png"
        img_data = requests.get(sprite_url).content
        with open(sprite_file, "wb") as f:
            f.write(img_data)
        return f"/{sprite_file}"
    except:
        return "https://cdn-icons-png.flaticon.com/512/188/188987.png"

def update_spawns():
    global active_spawns
    new_spawns = []
    messages = fetch_recent_messages()
    for msg in messages:
        parsed = extract_data(msg)
        if parsed:
            if all(existing["lat"] != parsed["lat"] or existing["lon"] != parsed["lon"] for existing in active_spawns):
                new_spawns.append(parsed)
    now = datetime.datetime.now(local_tz)
    active_spawns = [s for s in active_spawns if s["expires"] > now] + new_spawns


if __name__ == '__main__':
    print("🌍 Open http://localhost:5000 in your browser")
    app.run(debug=False)
