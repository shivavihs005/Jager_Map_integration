import sys
import math
import json
import networkx as nx

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot, QThread
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QGroupBox
)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWebChannel import QWebChannel


# -----------------------------
# Distance (meters)
# -----------------------------
def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


# -----------------------------
# Crescent Campus Road Graph (STARTER)
# You will expand nodes for 100% accuracy.
# -----------------------------
CRESCENT_NODES = {
    # Top main road points (Vandalur–Mambakkam–Kelambakkam road border)
    "T1": (12.87645, 80.08370),
    "T2": (12.87645, 80.08540),
    "T3": (12.87645, 80.08710),
    "T4": (12.87645, 80.08890),

    # Internal grid (approx based on screenshot roads)
    "I1": (12.87560, 80.08520),
    "I2": (12.87560, 80.08650),
    "I3": (12.87560, 80.08780),

    "I4": (12.87470, 80.08520),
    "I5": (12.87470, 80.08650),
    "I6": (12.87470, 80.08780),

    "I7": (12.87385, 80.08520),
    "I8": (12.87385, 80.08650),
    "I9": (12.87385, 80.08780),

    # Right side road (towards forest edge)
    "R1": (12.87580, 80.08890),
    "R2": (12.87460, 80.08890),
    "R3": (12.87360, 80.08890),

    # Bottom entry / connection towards bus area
    "B1": (12.87320, 80.08590),
    "B2": (12.87320, 80.08710),
}

# -----------------------------
# Build Graph with edges as real road segments
# -----------------------------
def build_crescent_graph():
    G = nx.Graph()
    for n, (lat, lon) in CRESCENT_NODES.items():
        G.add_node(n, lat=lat, lon=lon)

    def add_edge(a, b):
        lat1, lon1 = CRESCENT_NODES[a]
        lat2, lon2 = CRESCENT_NODES[b]
        G.add_edge(a, b, weight=haversine_m(lat1, lon1, lat2, lon2))

    # Top road chain
    add_edge("T1", "T2")
    add_edge("T2", "T3")
    add_edge("T3", "T4")

    # Internal horizontal streets
    add_edge("I1", "I2"); add_edge("I2", "I3")
    add_edge("I4", "I5"); add_edge("I5", "I6")
    add_edge("I7", "I8"); add_edge("I8", "I9")

    # Internal vertical streets
    add_edge("I1", "I4"); add_edge("I4", "I7")
    add_edge("I2", "I5"); add_edge("I5", "I8")
    add_edge("I3", "I6"); add_edge("I6", "I9")

    # Connections to top road
    add_edge("T2", "I1")
    add_edge("T3", "I3")

    # Right side road chain
    add_edge("T4", "R1")
    add_edge("R1", "R2")
    add_edge("R2", "R3")

    # Connect internal to right edge
    add_edge("I3", "R1")
    add_edge("I6", "R2")
    add_edge("I9", "R3")

    # Bottom entry connection
    add_edge("I7", "B1")
    add_edge("I8", "B2")
    add_edge("B1", "B2")

    return G


def nearest_node(G, lat, lon):
    best = None
    best_d = float("inf")
    for n, data in G.nodes(data=True):
        d = haversine_m(lat, lon, data["lat"], data["lon"])
        if d < best_d:
            best_d = d
            best = n
    return best, best_d


# -----------------------------
# Worker Thread (fast)
# -----------------------------
class PathWorker(QThread):
    success = pyqtSignal(list, float, str, str)
    fail = pyqtSignal(str)

    def __init__(self, G, s_lat, s_lon, e_lat, e_lon):
        super().__init__()
        self.G = G
        self.s_lat = s_lat
        self.s_lon = s_lon
        self.e_lat = e_lat
        self.e_lon = e_lon

    def run(self):
        try:
            s_node, _ = nearest_node(self.G, self.s_lat, self.s_lon)
            e_node, _ = nearest_node(self.G, self.e_lat, self.e_lon)

            # A* heuristic (straight line)
            def heuristic(a, b):
                a_lat, a_lon = self.G.nodes[a]["lat"], self.G.nodes[a]["lon"]
                b_lat, b_lon = self.G.nodes[b]["lat"], self.G.nodes[b]["lon"]
                return haversine_m(a_lat, a_lon, b_lat, b_lon)

            nodes = nx.astar_path(self.G, s_node, e_node, heuristic=heuristic, weight="weight")

            poly = []
            total_m = 0.0
            for i, n in enumerate(nodes):
                poly.append([self.G.nodes[n]["lat"], self.G.nodes[n]["lon"]])
                if i < len(nodes) - 1:
                    total_m += self.G.edges[nodes[i], nodes[i + 1]]["weight"]

            self.success.emit(poly, total_m / 1000.0, s_node, e_node)
        except Exception as e:
            self.fail.emit(str(e))


# -----------------------------
# JS Bridge
# -----------------------------
class Bridge(QObject):
    pointSelected = pyqtSignal(str, float, float)

    @pyqtSlot(str, float, float)
    def sendPoint(self, kind, lat, lon):
        self.pointSelected.emit(kind, lat, lon)


# -----------------------------
# Main App
# -----------------------------
class CrescentDedicatedRouter(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Crescent Dedicated Router (Campus Accurate)")
        self.resize(1450, 800)

        self.center_lat = 12.8746
        self.center_lon = 80.0862

        # Campus bounds (soft lock)
        self.bounds_south = 12.8718
        self.bounds_west  = 80.0830
        self.bounds_north = 12.8778
        self.bounds_east  = 80.0898

        self.G = build_crescent_graph()

        self.mode = None
        self.start_point = None
        self.end_point = None
        self.worker = None

        root = QWidget()
        self.setCentralWidget(root)
        main = QHBoxLayout(root)

        # Sidebar
        side = QVBoxLayout()
        title = QLabel("🧠 Crescent Campus Router")
        title.setStyleSheet("font-size:20px; font-weight:900;")
        side.addWidget(title)

        box = QGroupBox("Navigation")
        bl = QVBoxLayout(box)

        self.btn_s = QPushButton("📍 Set Start")
        self.btn_e = QPushButton("🎯 Set End")
        self.btn_r = QPushButton("🚀 Shortest Path")
        self.btn_c = QPushButton("🧹 Clear")

        for b in [self.btn_s, self.btn_e, self.btn_r, self.btn_c]:
            b.setStyleSheet("padding:10px; font-size:13px;")

        self.lbl_s = QLabel("Start: not set")
        self.lbl_e = QLabel("End: not set")
        self.lbl_d = QLabel("Distance: -")
        self.lbl_status = QLabel("Status: Ready")

        self.lbl_d.setStyleSheet("font-size:14px; font-weight:900;")
        self.lbl_status.setStyleSheet("font-size:13px; font-weight:800;")

        bl.addWidget(self.btn_s)
        bl.addWidget(self.btn_e)
        bl.addWidget(self.btn_r)
        bl.addWidget(self.btn_c)
        bl.addWidget(self.lbl_s)
        bl.addWidget(self.lbl_e)
        bl.addWidget(self.lbl_d)
        bl.addWidget(self.lbl_status)

        side.addWidget(box)
        side.addStretch(1)

        # Map
        self.web = QWebEngineView()

        self.bridge = Bridge()
        channel = QWebChannel()
        channel.registerObject("bridge", self.bridge)
        self.web.page().setWebChannel(channel)

        self.bridge.pointSelected.connect(self.on_point_selected)

        self.web.setHtml(self.html())

        main.addLayout(side, 1)
        main.addWidget(self.web, 2)

        # Events
        self.btn_s.clicked.connect(self.set_start_mode)
        self.btn_e.clicked.connect(self.set_end_mode)
        self.btn_r.clicked.connect(self.route_now)
        self.btn_c.clicked.connect(self.clear_all)

    def set_start_mode(self):
        self.mode = "start"
        self.lbl_status.setText("Status: Click map to set START")
        self.web.page().runJavaScript("setMode('start');")

    def set_end_mode(self):
        self.mode = "end"
        self.lbl_status.setText("Status: Click map to set END")
        self.web.page().runJavaScript("setMode('end');")

    def clear_all(self):
        self.mode = None
        self.start_point = None
        self.end_point = None
        self.lbl_s.setText("Start: not set")
        self.lbl_e.setText("End: not set")
        self.lbl_d.setText("Distance: -")
        self.lbl_status.setText("Status: Ready")
        self.web.page().runJavaScript("resetAll();")

    def on_point_selected(self, kind, lat, lon):
        if kind == "start":
            self.start_point = (lat, lon)
            self.lbl_s.setText(f"Start: {lat:.6f}, {lon:.6f}")
            self.lbl_status.setText("Status: ✅ Start set")
        elif kind == "end":
            self.end_point = (lat, lon)
            self.lbl_e.setText(f"End: {lat:.6f}, {lon:.6f}")
            self.lbl_status.setText("Status: ✅ End set")

    def route_now(self):
        if not self.start_point or not self.end_point:
            self.lbl_status.setText("Status: ❌ Select start & end first")
            return

        self.lbl_status.setText("Status: ⏳ Computing shortest campus path...")
        self.lbl_d.setText("Distance: calculating...")

        self.worker = PathWorker(self.G,
                                 self.start_point[0], self.start_point[1],
                                 self.end_point[0], self.end_point[1])
        self.worker.success.connect(self.on_route_success)
        self.worker.fail.connect(self.on_route_fail)
        self.worker.start()

    def on_route_success(self, polyline, km, s_node, e_node):
        self.lbl_status.setText(f"Status: ✅ Route done ({s_node} → {e_node})")
        self.lbl_d.setText(f"Distance: {km:.3f} km")
        js_poly = json.dumps(polyline)
        self.web.page().runJavaScript(f"drawPath({js_poly}, {km:.3f});")

    def on_route_fail(self, err):
        self.lbl_status.setText("Status: ❌ Routing failed")
        self.lbl_d.setText("Distance: -")
        self.web.page().runJavaScript("showError();")

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
    #map {{ height:100%; width:100%; cursor: crosshair; }}
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
  const map = L.map("map", {{
    center: [{self.center_lat}, {self.center_lon}],
    zoom: 17,
    minZoom: 16,
    maxZoom: 20,
    dragging: true,
    scrollWheelZoom: true,
    doubleClickZoom: true,
    touchZoom: true,
    keyboard: true,
    zoomControl: true,
  }});

  map.setMaxBounds(bounds);
  map.options.maxBoundsViscosity = 1.0;

  L.tileLayer("https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png", {{
    maxZoom: 20,
    attribution: "© OpenStreetMap contributors"
  }}).addTo(map);

  let mode = null;
  let startMarker = null;
  let endMarker = null;
  let routeLine = null;
  let popup = null;

  function setMode(m) {{ mode = m; }}

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

  function showError() {{
    if(popup) map.removeLayer(popup);
    popup = L.popup({{closeButton:false, autoClose:true, className:"labelbox"}})
      .setLatLng(map.getCenter())
      .setContent("❌ No route found in campus graph")
      .openOn(map);
  }}

  function drawPath(polyline, distKm) {{
    if(routeLine) map.removeLayer(routeLine);
    if(popup) map.removeLayer(popup);

    routeLine = L.polyline(polyline, {{
      color: "blue",
      weight: 7,
      opacity: 0.95
    }}).addTo(map);

    const mid = polyline[Math.floor(polyline.length/2)];
    popup = L.popup({{closeButton:false, autoClose:false, closeOnClick:false, className:"labelbox"}})
      .setLatLng(mid)
      .setContent("📏 " + distKm.toFixed(3) + " km")
      .openOn(map);
  }}

  map.on("click", function(e) {{
    if(!bridge) return;

    const lat = e.latlng.lat;
    const lon = e.latlng.lng;

    if(!bounds.contains([lat, lon])) return;

    if(mode === "start") {{
      if(startMarker) map.removeLayer(startMarker);
      startMarker = L.marker([lat, lon]).addTo(map).bindPopup("Start").openPopup();
      bridge.sendPoint("start", lat, lon);
      return;
    }}

    if(mode === "end") {{
      if(endMarker) map.removeLayer(endMarker);
      endMarker = L.marker([lat, lon]).addTo(map).bindPopup("End").openPopup();
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
    w = CrescentDedicatedRouter()
    w.show()
    sys.exit(app.exec_())
