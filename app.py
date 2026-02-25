import socket
from flask import Flask, render_template, jsonify, request
from sensor import sensor_system
from motor import motor
from navigator import navigator
from state_machine import state_machine, CarMode
from display_manager import display_manager

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
        'desired_heading': navigator.desired_heading,
        'heading_error': navigator.heading_error,
        'distance_to_next_waypoint': navigator.distance_to_next_waypoint,
        'gps_lock': s_data['has_fix']
    })

@app.route('/api/state')
def get_state():
    return jsonify(state_machine.get_state())

@app.route('/api/mode', methods=['POST'])
def set_mode():
    data = request.json
    mode_str = data.get('mode')
    if state_machine.set_mode(mode_str):
        state = state_machine.get_state()
        if state['mode'] not in [CarMode.SEMI_AUTO.value, CarMode.AUTO.value]:
            navigator.stop_navigation()
        motor.stop()
        return jsonify({"status": "success", "mode": state['mode']})
    return jsonify({"status": "error", "message": "Invalid mode"}), 400

@app.route('/api/config', methods=['POST'])
def set_config():
    data = request.json
    max_speed = data.get('max_speed')
    max_turn = data.get('max_turn')
    if max_speed is not None and max_turn is not None:
        state_machine.set_limits(max_speed, max_turn)
        return jsonify({"status": "success", "message": "Limits updated"})
    return jsonify({"status": "error", "message": "Missing parameters"}), 400

@app.route('/api/control', methods=['POST'])
def manual_control():
    state = state_machine.get_state()
    if state['mode'] != CarMode.MANUAL.value:
        return jsonify({"status": "error", "message": "Not in MANUAL mode"}), 403

    data = request.json
    speed_input = float(data.get('speed', 0)) # -100 to 100
    angle_input = float(data.get('angle', 0)) # -1.0 to 1.0

    effective_speed = speed_input * (state['max_speed'] / 100.0)
    effective_angle = angle_input * (state['max_turn'] / 100.0) * 30.0 # Map to -30 to 30 deg
    
    if effective_speed >= 0:
        motor.drive_forward(effective_speed, effective_angle)
    else:
        motor.drive_backward(effective_speed, effective_angle)

    return jsonify({"status": "success"})

@app.route('/api/navigate', methods=['POST'])
def start_navigation():
    state = state_machine.get_state()
    if state['mode'] not in [CarMode.SEMI_AUTO.value, CarMode.AUTO.value]:
         return jsonify({"status": "error", "message": "Switch to Semi-Autonomous Mode first"}), 403

    data = request.json
    waypoints = data.get('waypoints')
    
    if not waypoints:
        lat = data.get('lat')
        lng = data.get('lng')
        if lat is not None and lng is not None:
            waypoints = [{'lat': lat, 'lng': lng}]
            
    if not waypoints:
        return jsonify({"status": "error", "message": "Missing waypoints"}), 400
        
    navigator.set_route(waypoints)
    navigator.start_navigation()
    
    return jsonify({"status": "success", "message": "Navigation started"})

@app.route('/api/stop', methods=['POST'])
def stop_navigation():
    navigator.stop_navigation()
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
        try: display_manager.display_ip()
        except: pass
    except Exception:
        print("Could not detect IP address.")

    app.run(debug=True, host='0.0.0.0', use_reloader=False)

