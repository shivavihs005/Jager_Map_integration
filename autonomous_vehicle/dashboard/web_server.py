"""
web_server.py
Flask + Flask-SocketIO dashboard server.
REST endpoints:
    POST /api/navigate   {lat, lon}
    POST /api/abort
    GET  /api/state
WebSocket events pushed to client: vehicle_state
"""
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO

from vehicle_config import DASHBOARD_HOST, DASHBOARD_PORT

app = Flask(__name__)
app.config["SECRET_KEY"] = "jager_autonomous"
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# Injected by main_autonomous.py
_mission  = None
_state_est = None
_path     = None
_stream   = None


# ── REST Routes ──────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/navigate", methods=["POST"])
def navigate():
    data = request.get_json()
    lat  = float(data.get("lat",  0))
    lon  = float(data.get("lon",  0))
    if _mission:
        _mission.navigate_to(lat, lon)
    return jsonify({"status": "ok", "destination": [lat, lon]})

@app.route("/api/abort", methods=["POST"])
def abort():
    if _mission:
        _mission.abort()
    return jsonify({"status": "aborted"})

@app.route("/api/state", methods=["GET"])
def get_state():
    if _state_est:
        return jsonify(_state_est.get_state())
    return jsonify({})

@app.route("/api/mission", methods=["GET"])
def get_mission():
    if _mission:
        return jsonify({
            "state":      _mission.get_state(),
            "waypoints":  _path.get_all_waypoints() if _path else [],
            "trajectory": _mission.get_trajectory()[-200:]
        })
    return jsonify({})

@app.route("/api/set_servo", methods=["POST"])
def set_servo():
    """Manual servo override from dashboard slider."""
    data = request.get_json()
    pulse = int(data.get("pulse", 1060))
    from vehicle_config import SERVO_MAX_LEFT, SERVO_MAX_RIGHT
    pulse = max(SERVO_MAX_LEFT, min(SERVO_MAX_RIGHT, pulse))
    # The servo is accessed via the mission manager's internal reference
    # Expose it if you wish; here we broadcast and let main.py handle it
    socketio.emit("manual_servo", {"pulse": pulse})
    return jsonify({"status": "ok", "pulse": pulse})


# ── Factory ───────────────────────────────────────────────────────────────────
def create_server(mission, state_estimator, path_planner, stream):
    global _mission, _state_est, _path, _stream
    _mission   = mission
    _state_est = state_estimator
    _path      = path_planner
    _stream    = stream
    return app, socketio


def run_server():
    print(f"[Web] Dashboard at http://{DASHBOARD_HOST}:{DASHBOARD_PORT}")
    socketio.run(app, host=DASHBOARD_HOST, port=DASHBOARD_PORT,
                 debug=False, use_reloader=False, log_output=False)
