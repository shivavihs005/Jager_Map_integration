import socket
from flask import Flask, render_template, jsonify, request
from sensor import sensor_system
from manual_controller import manual_controller

app = Flask(__name__)

# Start sensors
sensor_system.start()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/location')
def get_location():
    data = sensor_system.get_data()
    return jsonify({
        'lat': data['lat'],
        'lng': data['lng'],
        'heading': data['gps_heading'], # Backwards compatibility
        'speed': data['speed']
    })

@app.route('/api/telemetry')
def get_telemetry():
    s_data = sensor_system.get_data()
    return jsonify({
        'current_yaw': s_data['current_yaw'],
        'desired_heading': 0.0,
        'heading_error': 0.0,
        'distance_to_next_waypoint': 0.0,
        'gps_lock': s_data['has_fix']
    })

@app.route('/api/state')
def get_state():
    return jsonify(manual_controller.get_state())

@app.route('/api/mode', methods=['POST'])
def set_mode():
    data = request.json
    mode_str = data.get('mode')
    manual_controller.set_mode(mode_str)
    state = manual_controller.get_state()
    return jsonify({"status": "success", "mode": state['mode']})

@app.route('/api/config', methods=['POST'])
def set_config():
    data = request.json
    max_speed = data.get('max_speed')
    max_turn = data.get('max_turn')
    if max_speed is not None and max_turn is not None:
        manual_controller.set_limits(max_speed, max_turn)
        return jsonify({"status": "success", "message": "Limits updated"})
    return jsonify({"status": "error", "message": "Missing parameters"}), 400

@app.route('/api/control', methods=['POST'])
def manual_control():
    data = request.json
    speed_input = float(data.get('speed', 0)) # -100 to 100
    angle_input = float(data.get('angle', 0)) # -1.0 to 1.0

    if manual_controller.execute_control(speed_input, angle_input):
        return jsonify({"status": "success"})
    else:
        return jsonify({"status": "error", "message": "Not in MANUAL mode"}), 403

@app.route('/api/navigate', methods=['POST'])
def start_navigation():
    # Stubbed out since autonomous mode is removed
    return jsonify({"status": "success", "message": "Navigation started (Simulated)"})

@app.route('/api/stop', methods=['POST'])
def stop_navigation():
    # Stubbed out since autonomous mode is removed
    manual_controller.stop()
    return jsonify({"status": "success", "message": "Navigation stopped"})

if __name__ == '__main__':
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip_address = s.getsockname()[0]
        s.close()
        print(f"--------------------------------------------------")
        print(f" Server is running on your network!")
        print(f" Access it from other devices at: http://{ip_address}:5000")
        print(f"--------------------------------------------------")
    except Exception:
        print("Could not detect IP address.")

    app.run(debug=True, host='0.0.0.0', use_reloader=False)
