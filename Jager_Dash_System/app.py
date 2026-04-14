from flask import Flask, render_template, request, jsonify, Response
from hardware.camera import CameraStream
from navigation.state_machine import StateMachine

app = Flask(__name__)

# Initialize singletons
camera = CameraStream()
state_machine = StateMachine()

@app.route('/')
def home():
    """Render the main SPA dashboard."""
    return render_template('index.html')

@app.route('/api/start', methods=['POST'])
def start_system():
    data = request.json
    mode = data.get("mode", "STOP")
    
    # Initialize sensors and sub-processes
    state_machine.sensors.calibrate()
    state_machine.set_mode(mode)
    state_machine.start()
    
    return jsonify({"status": "success", "message": f"{mode} mode started."})

@app.route('/api/stop', methods=['POST'])
def stop_system():
    state_machine.set_mode("STOP")
    return jsonify({"status": "success", "message": "System stopped."})

@app.route('/api/reset', methods=['POST'])
def reset_system():
    state_machine.stop()
    return jsonify({"status": "success", "message": "System reset."})

@app.route('/api/control', methods=['POST'])
def manual_control():
    """Accepts x, y coordinates from joystick."""
    data = request.json
    x = data.get("x", 0)
    y = data.get("y", 0)
    
    state_machine.manual_joystick(x, y)
    return jsonify({"status": "success", "x": x, "y": y})

@app.route('/api/sensors', methods=['GET'])
def get_sensors():
    data = state_machine.sensors.get_all()
    # Add current state
    data['mode'] = state_machine.mode
    data['motor_state'] = state_machine.motor.state
    data['motor_speed'] = state_machine.motor.speed
    return jsonify(data)

@app.route('/api/route', methods=['POST'])
def get_route():
    data = request.json
    lat1 = data.get("start_lat")
    lon1 = data.get("start_lon")
    lat2 = data.get("end_lat")
    lon2 = data.get("end_lon")
    
    waypoints = state_machine.fetch_osrm_route(lat1, lon1, lat2, lon2)
    if waypoints:
        return jsonify({"status": "success", "waypoints": waypoints})
    else:
        return jsonify({"status": "error", "message": "Route generation failed"}), 400

@app.route('/video')
def video_feed():
    """Video streaming route for OpenCV camera feed."""
    return Response(camera.generate_mjpeg_stream(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    # Typically runs on port 5050 to avoid conflicts
    app.run(host='0.0.0.0', port=5050, debug=True, threaded=True)
