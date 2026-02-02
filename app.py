from flask import Flask, render_template, jsonify, request
from gps_reader import gps_reader
from navigator import navigator
from car_controller import car
from state_machine import state_machine, CarMode
from display_manager import display_manager

app = Flask(__name__)

# Start GPS reading in background
# Note: On a PC without the GPS hardware, this will log connection errors but continue running.
gps_reader.start()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/location')
def get_location():
    location = gps_reader.get_location()
    return jsonify(location)

@app.route('/api/state')
def get_state():
    return jsonify(state_machine.get_state())

@app.route('/api/mode', methods=['POST'])
def set_mode():
    data = request.json
    mode_str = data.get('mode')
    if state_machine.set_mode(mode_str):
        # Stop navigation if switching away from SEMI_AUTONOMOUS
        if state_machine.current_mode != CarMode.AUTONOMOUS:
            navigator.stop_navigation()
        # Create a stop command when switching modes for safety
        car.stop()
        state_machine.update_motion_state(0, 0)
        return jsonify({"status": "success", "mode": state_machine.current_mode.value})
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
    # Only allow manual control in MANUAL or AUTONOMOUS (override)? 
    # Spec says MANUAL. Let's stick to MANUAL.
    if state_machine.current_mode != CarMode.MANUAL:
        # Optional: You might allow override, but for now strict.
        return jsonify({"status": "error", "message": "Not in MANUAL mode"}), 403

    data = request.json
    speed_input = float(data.get('speed', 0)) # -100 to 100
    angle_input = float(data.get('angle', 0)) # -1.0 to 1.0

    # Apply Limits
    # Max Speed reduces the effective output
    effective_speed = speed_input * (state_machine.max_speed / 100.0)
    
    # Max Turn reduces the effective angle
    effective_angle = angle_input * (state_machine.max_turn / 100.0)

    # Update Motion State
    state_machine.update_motion_state(effective_speed, effective_angle)
    
    # Drive Car
    car.set_speed(effective_speed)
    car.set_steering(effective_angle)

    return jsonify({"status": "success"})

@app.route('/api/navigate', methods=['POST'])
def start_navigation():
    if state_machine.current_mode != CarMode.AUTONOMOUS:
         return jsonify({"status": "error", "message": "Switch to Semi-Autonomous Mode first"}), 403

    data = request.json
    waypoints = data.get('waypoints')
    
    # Support legacy single destination
    if not waypoints:
        lat = data.get('lat')
        lng = data.get('lng')
        if lat is not None and lng is not None:
            waypoints = [{'lat': lat, 'lng': lng}]
    
    if not waypoints:
        return jsonify({"status": "error", "message": "Missing waypoints"}), 400
        
    navigator.set_route(waypoints)
    navigator.start_navigation()
    state_machine.update_motion_state(10, 0)
    
    return jsonify({"status": "success", "message": "Navigation started"})

@app.route('/api/stop', methods=['POST'])
def stop_navigation():
    navigator.stop_navigation()
    car.stop()
    state_machine.update_motion_state(0, 0)
    return jsonify({"status": "success", "message": "Navigation stopped"})

if __name__ == '__main__':
    # Helper to print the actual IP address for the user
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip_address = s.getsockname()[0]
        s.close()
        print(f"--------------------------------------------------")
        print(f" Server is running on your network!")
        print(f" Access it from other devices at: http://{ip_address}:5000")
        print(f"--------------------------------------------------")
        # Update LCD
        try:
            display_manager.display_ip()
        except:
            pass
    except Exception:
        print("Could not detect IP address. Check 'ifconfig' or 'hostname -I'")

    # Host='0.0.0.0' allows access from other devices on the network
    app.run(debug=True, host='0.0.0.0', use_reloader=False)
