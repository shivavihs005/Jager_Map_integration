"""
gps_test.py
Standalone GPS test server — reads NEO6M via serial, shows live GPS
on a Leaflet.js web page, and prints raw NMEA + parsed data to console.

Usage:
    sudo pigpiod  (not needed for GPS, but keeps same boot pattern)
    source ~/my-projects/Jager_Map_integration/env/bin/activate
    cd ~/my-projects/Jager_Map_integration/project
    python gps_test.py

Then open http://<pi-ip>:5050
"""
import threading
import time
import math
from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO

# ── GPS Serial ────────────────────────────────────────────────────────────────
GPS_PORT   = "/dev/serial0"
GPS_BAUD   = 9600
EARTH_R    = 6_371_000.0

try:
    import serial
    SERIAL_OK = True
except ImportError:
    SERIAL_OK = False
    print("[GPS Test] pyserial not found — mock mode")

# ── Flask App ─────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.config["SECRET_KEY"] = "gps_test_jager"
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# ── Shared State ──────────────────────────────────────────────────────────────
gps_state = {
    "latitude":   0.0,
    "longitude":  0.0,
    "altitude":   0.0,
    "speed_kmh":  0.0,
    "satellites": 0,
    "fix":        False,
    "raw_nmea":   "",
    "fix_quality": 0,
}
_lock = threading.Lock()
_prev_lat = _prev_lon = _prev_time = None


def nmea_to_decimal(val_str, direction):
    if not val_str:
        return 0.0
    dot = val_str.index(".")
    deg  = float(val_str[:dot - 2])
    mins = float(val_str[dot - 2:])
    dec  = deg + mins / 60.0
    if direction in ("S", "W"):
        dec = -dec
    return dec


def haversine_m(lat1, lon1, lat2, lon2):
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlon/2)**2
    return 2 * EARTH_R * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def parse_gga(sentence):
    global _prev_lat, _prev_lon, _prev_time
    parts = sentence.split(",")
    if len(parts) < 10:
        return

    try:
        lat = nmea_to_decimal(parts[2], parts[3])
        lon = nmea_to_decimal(parts[4], parts[5])
        fix_q = int(parts[6]) if parts[6] else 0
        sats  = int(parts[7]) if parts[7] else 0
        alt   = float(parts[9]) if parts[9] else 0.0
    except (ValueError, IndexError):
        return

    now = time.time()
    speed = 0.0
    if fix_q > 0 and _prev_lat is not None and _prev_time is not None:
        dist = haversine_m(_prev_lat, _prev_lon, lat, lon)
        dt   = now - _prev_time
        if dt > 0:
            speed = (dist / dt) * 3.6

    with _lock:
        gps_state["latitude"]    = lat
        gps_state["longitude"]   = lon
        gps_state["altitude"]    = alt
        gps_state["satellites"]  = sats
        gps_state["fix"]         = fix_q > 0
        gps_state["fix_quality"] = fix_q
        gps_state["speed_kmh"]   = round(speed, 2)

    if fix_q > 0:
        _prev_lat, _prev_lon, _prev_time = lat, lon, now


def gps_reader():
    """Background thread — reads serial port and prints + parses NMEA."""
    if not SERIAL_OK:
        _mock_gps()
        return

    try:
        ser = serial.Serial(GPS_PORT, GPS_BAUD, timeout=1)
        print(f"[GPS] Opened {GPS_PORT} @ {GPS_BAUD} baud")
    except Exception as e:
        print(f"[GPS] Serial error: {e} — running mock")
        _mock_gps()
        return

    while True:
        try:
            raw = ser.readline().decode("ascii", errors="ignore").strip()
            if not raw:
                continue

            # Always print raw to console
            print(f"[NMEA] {raw}")

            with _lock:
                gps_state["raw_nmea"] = raw

            if raw.startswith("$GPGGA") or raw.startswith("$GNGGA"):
                parse_gga(raw)
        except Exception as e:
            print(f"[GPS] Read error: {e}")
            time.sleep(0.5)


def _mock_gps():
    """Simulates GPS movement in Chennai for testing without hardware."""
    lat, lon = 13.082680, 80.270721
    print("[GPS] Mock mode — simulating Chennai GPS fix")
    while True:
        lat += 0.00002
        lon += 0.00001
        with _lock:
            gps_state["latitude"]   = lat
            gps_state["longitude"]  = lon
            gps_state["altitude"]   = 12.0
            gps_state["satellites"] = 7
            gps_state["fix"]        = True
            gps_state["fix_quality"] = 1
            gps_state["speed_kmh"]  = 1.2
        time.sleep(1)


def pusher():
    """Push GPS data to all WebSocket clients every 1 second."""
    while True:
        with _lock:
            payload = dict(gps_state)
        socketio.emit("gps_update", payload)
        time.sleep(1)


# ── Routes ────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("gps_test.html")


@app.route("/api/gps")
def api_gps():
    with _lock:
        return jsonify(dict(gps_state))


# ── Entry ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    threading.Thread(target=gps_reader, daemon=True).start()
    threading.Thread(target=pusher,     daemon=True).start()
    print("[GPS Test] Dashboard → http://0.0.0.0:5050")
    socketio.run(app, host="0.0.0.0", port=5050, debug=False, use_reloader=False)
