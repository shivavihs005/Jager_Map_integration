"""
web_server.py
Flask + Flask-SocketIO dashboard server.
REST endpoints:
    POST /api/navigate   {lat, lon}
    POST /api/abort
    POST /api/mode       {mode: 'AUTO'|'MANUAL'}
    POST /api/control    {speed: -100..100, angle: -1.0..1.0}
    GET  /api/state
WebSocket events pushed to client: vehicle_state
"""
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO

from vehicle_config import (DASHBOARD_HOST, DASHBOARD_PORT,
                            SERVO_MAX_LEFT, SERVO_MAX_RIGHT, SERVO_CENTER)

app = Flask(__name__)
app.config["SECRET_KEY"] = "jager_autonomous"
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# Injected by main_autonomous.py
_mission      = None
_state_est    = None
_path         = None
_stream       = None
_motor        = None     # MotorController — for manual drive
_servo        = None     # SteeringServo   — for manual steer
_current_mode = "AUTO"
_max_speed_pct = 60.0    # 0-100, runtime speed cap (set by dashboard slider)


# ── REST Routes ──────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/navigate", methods=["POST"])
def navigate():
    data = request.get_json()
    lat  = float(data.get("lat", 0))
    lon  = float(data.get("lon", 0))
    if _mission:
        _mission.navigate_to(lat, lon)
    return jsonify({"status": "ok", "destination": [lat, lon]})


@app.route("/api/abort", methods=["POST"])
def abort():
    if _mission:
        _mission.abort()
    if _motor:
        _motor.stop()
    if _servo:
        _servo.center()
    return jsonify({"status": "aborted"})


@app.route("/api/mode", methods=["POST"])
def set_mode():
    """Switch between AUTO (autonomous) and MANUAL (joystick) modes."""
    global _current_mode
    data = request.get_json()
    mode = data.get("mode", "AUTO").upper()
    _current_mode = mode

    if mode == "MANUAL":
        # Safety: abort any ongoing autonomous mission
        if _mission:
            _mission.abort()
    else:
        # Returning to AUTO — stop and centre
        if _motor:
            _motor.stop()
        if _servo:
            _servo.center()

    print(f"[Web] Mode → {_current_mode}")
    return jsonify({"status": "ok", "mode": _current_mode})


@app.route("/api/control", methods=["POST"])
def control():
    """
    Manual joystick drive command.
    Only executes in MANUAL mode.
    Body: {speed: -100..100, angle: -1.0..1.0}
    """
    if _current_mode != "MANUAL":
        return jsonify({"status": "ignored", "reason": "not in MANUAL mode"})

    data  = request.get_json()
    speed = float(data.get("speed", 0))
    angle = float(data.get("angle", 0))

    # Apply runtime speed cap
    if speed > 0:
        speed = min(speed, _max_speed_pct)
    elif speed < 0:
        speed = max(speed, -_max_speed_pct)

    if _motor:
        _motor.set_speed(speed)
    if _servo:
        _servo.set_normalised(angle)   # -1.0..1.0 → 680–1060–1460 µs


    return jsonify({"status": "ok", "speed": speed, "angle": angle})


@app.route("/api/config", methods=["POST"])
def set_config():
    """
    Set runtime configuration from dashboard.
    Body: {max_speed: 0..100}
    Updates both manual drive cap and autonomous BASE_SPEED_PCT.
    """
    global _max_speed_pct
    data = request.get_json()
    if "max_speed" in data:
        _max_speed_pct = max(0.0, min(100.0, float(data["max_speed"])))
        # Push to mission manager if available
        if _mission:
            _mission.set_max_speed(_max_speed_pct)
        print(f"[Web] Max speed → {_max_speed_pct:.0f}%")
    return jsonify({"status": "ok", "max_speed": _max_speed_pct})


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
def set_servo_endpoint():
    """Direct servo pulse from dashboard slider."""
    data  = request.get_json()
    pulse = int(data.get("pulse", SERVO_CENTER))
    pulse = max(SERVO_MAX_LEFT, min(SERVO_MAX_RIGHT, pulse))
    if _servo:
        _servo.set_pulse(pulse)
    socketio.emit("manual_servo", {"pulse": pulse})
    return jsonify({"status": "ok", "pulse": pulse})


# ── Factory ───────────────────────────────────────────────────────────────────
def create_server(mission, state_estimator, path_planner, stream,
                  motor=None, servo=None):
    global _mission, _state_est, _path, _stream, _motor, _servo
    _mission   = mission
    _state_est = state_estimator
    _path      = path_planner
    _stream    = stream
    _motor     = motor
    _servo     = servo
    return app, socketio


def run_server():
    print(f"[Web] Dashboard at http://{DASHBOARD_HOST}:{DASHBOARD_PORT}")
    socketio.run(app, host=DASHBOARD_HOST, port=DASHBOARD_PORT,
                 debug=False, use_reloader=False, log_output=False)
