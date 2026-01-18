import sys
import json
import urllib.request
import math

from PyQt5.QtCore import QObject, pyqtSlot, pyqtSignal, QThread
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QGroupBox, QTextEdit
)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWebChannel import QWebChannel


# -------------------------
# Utils
# -------------------------
def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def http_get_json(url, timeout=10):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


# -------------------------
# OSRM Advanced: SNAP POINT
# -------------------------
def osrm_nearest(lat, lon, profile="foot"):
    # OSRM expects lon,lat
    url = f"https://router.project-osrm.org/nearest/v1/{profile}/{lon},{lat}"
    data = http_get_json(url, timeout=10)

    if data.get("code") != "Ok":
        raise RuntimeError("OSRM nearest failed")

    wp = data["waypoints"][0]
    # location = [lon, lat]
    snapped_lon, snapped_lat = wp["location"][0], wp["location"][1]
    name = (wp.get("name") or "").strip()
    dist_m = wp.get("distance", 0)

    return snapped_lat, snapped_lon, name, dist_m


# -------------------------
# OSRM Advanced: ROUTE + STEPS
# -------------------------
def osrm_route_with_steps(start_lat, start_lon, end_lat, end_lon, profile="foot"):
    url = (
        f"https://router.project-osrm.org/route/v1/{profile}/"
        f"{start_lon},{start_lat};{end_lon},{end_lat}"
        "?overview=full&geometries=geojson&steps=true"
    )

    data = http_get_json(url, timeout=12)
    if data.get("code") != "Ok":
        raise RuntimeError("OSRM route failed")

    route = data["routes"][0]
    distance_km = route["distance"] / 1000.0
    duration_min = route["duration"] / 60.0

    coords = route["geometry"]["coordinates"]  # [lon,lat]
    leaflet_coords = [[c[1], c[0]] for c in coords]  # [lat,lon]

    steps_out = []
    legs = route.get("legs", [])
    if legs:
        steps = legs[0].get("steps", [])
        for s in steps:
            name = (s.get("name") or "").strip()
            maneuver = s.get("maneuver", {})
            mtype = maneuver.get("type", "move")
            modifier = maneuver.get("modifier", "")
            dist_m = s.get("distance", 0)
            dur_s = s.get("duration", 0)

            road = name if name else "(unnamed path)"
            extra = f" ({modifier})" if modifier else ""
            steps_out.append({
                "instruction": f"{mtype.upper()}{extra} on {road}",
                "distance_m": dist_m,
                "duration_s": dur_s
            })

    return leaflet_coords, distance_km, duration_min, steps_out


# -------------------------
# Worker Thread (Snap + Route)
# -------------------------
class RouteWorker(QThread):
    success = pyqtSignal(dict)  # payload dict
    fail = pyqtSignal(str)

    def __init__(self, raw_start, raw_end):
        super().__init__()
        self.raw_start = raw_start
        self.raw_end = raw_end

    def run(self):
        try:
            # Snap both points for precision
            s_lat, s_lon = self.raw_start
            e_lat, e_lon = self.raw_end

            ss_lat, ss_lon, ss_name, ss_snap_m = osrm_nearest(s_lat, s_lon, profile="foot")
            ee_lat, ee_lon, ee_name, ee_snap_m = osrm_nearest(e_lat, e_lon, profile="foot")

            # Route between snapped points
            route_coords, route_km, route_min, steps = osrm_route_with_steps(
                ss_lat, ss_lon, ee_lat, ee_lon, profile="foot"
            )

            straight_km = haversine_km(ss_lat, ss_lon, ee_lat, ee_lon)

            payload = {
                "snapped_start": (ss_lat, ss_lon, ss_name, ss_snap_m),
                "snapped_end": (ee_lat, ee_lon, ee_name, ee_snap_m),
                "route_coords": route_coords,
                "route_km": route_km,
                "route_min": route_min,
                "straight_km": straight_km,
                "steps": steps
            }

            self.success.emit(payload)

        except Exception as e:
            self.fail.emit(str(e))


# -------------------------
# WebChannel Bridge
# -------------------------
class Bridge(QObject):
    pointSelected = pyqtSignal(str, float, float)  # kind, lat, lon

    @pyqtSlot(str, float, float)
    def sendPoint(self, kind, lat, lon):
        self.pointSelected.emit(kind, lat, lon)


# -------------------------
# Main App
# -------------------------
class CrescentOSRMAdvanced(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Crescent Maps PRO (Advanced OSRM)")
        self.resize(1450, 800)

        # Campus lock bounds
        self.center_lat = 12.8746
        self.center_lon = 80.0862
        self.bounds_south = 12.8715
        self.bounds_west  = 80.0830
        self.bounds_north = 12.8775
        self.bounds_east  = 80.0895

        self.start_raw = None
        self.end_raw = None
        self.mode = None
        self.worker = None

        root = QWidget()
        self.setCentralWidget(root)
        layout = QHBoxLayout(root)

        # Sidebar
        sidebar = QVBoxLayout()
        sidebar.setSpacing(10)

        head = QLabel("🧭 Crescent Maps PRO")
        head.setStyleSheet("font-size:20px; font-weight:900;")
        sidebar.addWidget(head)

        box = QGroupBox("Route Planner (Accurate)")
        box_layout = QVBoxLayout(box)

        self.btn_pick_start = QPushButton("📍 Pick Start (Precise)")
        self.btn_pick_end = QPushButton("🎯 Pick End (Precise)")
        self.btn_route = QPushButton("🚶 Calculate Walking Route")
        self.btn_clear = QPushButton("🧹 Clear")

        for b in [self.btn_pick_start, self.btn_pick_end, self.btn_route, self.btn_clear]:
            b.setStyleSheet("padding:10px; font-size:13px;")

        box_layout.addWidget(self.btn_pick_start)
        box_layout.addWidget(self.btn_pick_end)
        box_layout.addWidget(self.btn_route)
        box_layout.addWidget(self.btn_clear)

        self.lbl_start = QLabel("Start (raw): not set")
        self.lbl_end = QLabel("End (raw): not set")

        self.lbl_snap_start = QLabel("Start (snapped): -")
        self.lbl_snap_end = QLabel("End (snapped): -")

        self.lbl_summary = QLabel("Distance: - | ETA: - | Straight: -")
        self.lbl_status = QLabel("Status: Ready")

        for l in [self.lbl_start, self.lbl_end, self.lbl_snap_start, self.lbl_snap_end, self.lbl_summary]:
            l.setStyleSheet("font-size:12px;")

        self.lbl_status.setStyleSheet("font-size:13px; font-weight:900;")

        box_layout.addWidget(self.lbl_start)
        box_layout.addWidget(self.lbl_end)
        box_layout.addWidget(self.lbl_snap_start)
        box_layout.addWidget(self.lbl_snap_end)
        box_layout.addWidget(self.lbl_summary)
        box_layout.addWidget(self.lbl_status)

        sidebar.addWidget(box)

        directions_box = QGroupBox("Turn-by-turn (OSRM)")
        directions_layout = QVBoxLayout(directions_box)

        self.txt_dir = QTextEdit()
        self.txt_dir.setReadOnly(True)
        self.txt_dir.setStyleSheet("font-size:12px;")
        directions_layout.addWidget(self.txt_dir)

        sidebar.addWidget(directions_box)

        # Map
        self.web = QWebEngineView()

        self.bridge = Bridge()
        self.channel = QWebChannel()
        self.channel.registerObject("bridge", self.bridge)
        self.web.page().setWebChannel(self.channel)

        self.bridge.pointSelected.connect(self.on_point_selected)
        self.web.setHtml(self.html())

        layout.addLayout(sidebar, 1)
        layout.addWidget(self.web, 2)

        # events
        self.btn_pick_start.clicked.connect(self.pick_start)
        self.btn_pick_end.clicked.connect(self.pick_end)
        self.btn_route.clicked.connect(self.calc_route)
        self.btn_clear.clicked.connect(self.clear_all)

    def pick_start(self):
        self.mode = "start"
        self.lbl_status.setText("Status: Click map to set START")
        self.web.page().runJavaScript("setMode('start');")

    def pick_end(self):
        self.mode = "end"
        self.lbl_status.setText("Status: Click map to set END")
        self.web.page().runJavaScript("setMode('end');")

    def clear_all(self):
        self.mode = None
        self.start_raw = None
        self.end_raw = None
        self.lbl_start.setText("Start (raw): not set")
        self.lbl_end.setText("End (raw): not set")
        self.lbl_snap_start.setText("Start (snapped): -")
        self.lbl_snap_end.setText("End (snapped): -")
        self.lbl_summary.setText("Distance: - | ETA: - | Straight: -")
        self.lbl_status.setText("Status: Ready")
        self.txt_dir.setText("")
        self.web.page().runJavaScript("resetAll();")

    def on_point_selected(self, kind, lat, lon):
        if kind == "start":
            self.start_raw = (lat, lon)
            self.lbl_start.setText(f"Start (raw): {lat:.6f}, {lon:.6f}")
            self.lbl_status.setText("Status: ✅ Start set (raw)")
        elif kind == "end":
            self.end_raw = (lat, lon)
            self.lbl_end.setText(f"End (raw): {lat:.6f}, {lon:.6f}")
            self.lbl_status.setText("Status: ✅ End set (raw)")

    def calc_route(self):
        if not self.start_raw or not self.end_raw:
            self.lbl_status.setText("Status: ❌ Set Start + End first")
            return

        self.lbl_status.setText("Status: ⏳ Snapping to roads + routing...")
        self.lbl_summary.setText("Distance: calculating...")
        self.txt_dir.setText("Loading directions...")
        self.web.page().runJavaScript("showRouting();")

        self.worker = RouteWorker(self.start_raw, self.end_raw)
        self.worker.success.connect(self.on_route_ready)
        self.worker.fail.connect(self.on_route_fail)
        self.worker.start()

    def on_route_ready(self, payload):
        ss_lat, ss_lon, ss_name, ss_snap_m = payload["snapped_start"]
        ee_lat, ee_lon, ee_name, ee_snap_m = payload["snapped_end"]

        route_km = payload["route_km"]
        route_min = payload["route_min"]
        straight_km = payload["straight_km"]
        coords = payload["route_coords"]
        steps = payload["steps"]

        self.lbl_snap_start.setText(
            f"Start (snapped): {ss_lat:.6f}, {ss_lon:.6f} | snap={ss_snap_m:.1f}m"
        )
        self.lbl_snap_end.setText(
            f"End (snapped): {ee_lat:.6f}, {ee_lon:.6f} | snap={ee_snap_m:.1f}m"
        )

        self.lbl_summary.setText(
            f"Distance: {route_km:.3f} km | ETA: {route_min:.1f} min | Straight: {straight_km:.3f} km"
        )
        self.lbl_status.setText("Status: ✅ Accurate route ready")

        js_poly = json.dumps(coords)
        self.web.page().runJavaScript(f"drawRoadRoute({js_poly}, {route_km:.3f}, {route_min:.1f});")

        lines = []
        for i, s in enumerate(steps, 1):
            lines.append(
                f"{i}. {s['instruction']}  |  {s['distance_m']:.0f} m  |  {(s['duration_s']/60):.1f} min"
            )
        self.txt_dir.setText("\n".join(lines) if lines else "No step details returned.")

    def on_route_fail(self, err):
        self.lbl_status.setText("Status: ❌ Routing failed")
        self.lbl_summary.setText("Distance: - | ETA: - | Straight: -")
        self.txt_dir.setText(f"Error: {err}")
        self.web.page().runJavaScript("showRouteError();")

    def html(self):
        return f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">

  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script src="qrc:///qtwebchannel/qwebchannel.js"></script>

  <style>
    html, body {{ height:100%; margin:0; }}
    #map {{ width:100%; height:100%; }}
    .labelbox {{
      background: white;
      padding: 6px 10px;
      border-radius: 10px;
      border: 1px solid rgba(0,0,0,0.3);
      font-weight: bold;
      box-shadow: 0px 2px 6px rgba(0,0,0,0.25);
    }}
  </style>
</head>
<body>
<div id="map"></div>

<script>
  let bridge = null;
  new QWebChannel(qt.webChannelTransport, function(channel) {{
    bridge = channel.objects.bridge;
  }});

  const bounds = L.latLngBounds([[{self.bounds_south}, {self.bounds_west}], [{self.bounds_north}, {self.bounds_east}]]);

  const map = L.map('map', {{
    center: [{self.center_lat}, {self.center_lon}],
    zoom: 17,
    minZoom: 17,
    maxZoom: 19,

    dragging: false,
    scrollWheelZoom: false,
    doubleClickZoom: false,
    touchZoom: false,
    boxZoom: false,
    keyboard: false,
    zoomControl: false,
  }});

  map.setMaxBounds(bounds);

  L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
    maxZoom: 20,
    attribution: '© OpenStreetMap contributors'
  }}).addTo(map);

  let mode = null;
  let startMarker = null;
  let endMarker = null;
  let routeLine = null;
  let popup = null;

  function setMode(m) {{
    mode = m;
  }}

  function resetAll() {{
    mode = null;
    if(startMarker) map.removeLayer(startMarker);
    if(endMarker) map.removeLayer(endMarker);
    if(routeLine) map.removeLayer(routeLine);
    if(popup) map.removeLayer(popup);
    startMarker = null;
    endMarker = null;
    routeLine = null;
    popup = null;
  }}

  function showRouting() {{
    if(popup) map.removeLayer(popup);
    popup = L.popup({{closeButton:false, autoClose:false, closeOnClick:false, className:"labelbox"}})
      .setLatLng(map.getCenter())
      .setContent("⏳ Snapping + Routing...")
      .openOn(map);
  }}

  function showRouteError() {{
    if(popup) map.removeLayer(popup);
    popup = L.popup({{closeButton:false, autoClose:false, closeOnClick:false, className:"labelbox"}})
      .setLatLng(map.getCenter())
      .setContent("❌ Route failed")
      .openOn(map);
  }}

  function drawRoadRoute(routeCoords, km, mins) {{
    if(routeLine) map.removeLayer(routeLine);
    if(popup) map.removeLayer(popup);

    routeLine = L.polyline(routeCoords, {{
      color: "blue",
      weight: 6,
      opacity: 0.95
    }}).addTo(map);

    const mid = routeCoords[Math.floor(routeCoords.length/2)];

    popup = L.popup({{closeButton:false, autoClose:false, closeOnClick:false, className:"labelbox"}})
      .setLatLng(mid)
      .setContent("📏 " + km.toFixed(3) + " km | ⏱ " + mins.toFixed(1) + " min")
      .openOn(map);
  }}

  map.on('click', function(e) {{
    const lat = e.latlng.lat;
    const lon = e.latlng.lng;
    if(!bounds.contains([lat, lon])) return;
    if(!bridge) return;

    if(mode === "start") {{
      if(startMarker) map.removeLayer(startMarker);
      startMarker = L.marker([lat, lon]).addTo(map).bindPopup("Start (raw)").openPopup();
      bridge.sendPoint("start", lat, lon);
      return;
    }}

    if(mode === "end") {{
      if(endMarker) map.removeLayer(endMarker);
      endMarker = L.marker([lat, lon]).addTo(map).bindPopup("End (raw)").openPopup();
      bridge.sendPoint("end", lat, lon);
      return;
    }}
  }});
</script>

</body>
</html>
        """


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = CrescentOSRMAdvanced()
    w.show()
    sys.exit(app.exec_())
