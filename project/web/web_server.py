"""
web_server.py — Flask app to provide REST APIs and serve the UI
"""
import threading
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# Global component references (to be set by main.py before running)
motor_controller = None
steering_servo = None
sensors = {}
fusion = None
data_lock = threading.Lock()

@app.route('/')
def index():
    return render_template('index.html')

# --- API Endpoints ---

@app.route('/api/forward', methods=['POST'])
def forward():
    data = request.json
    speed = float(data.get('speed', 50.0))
    if motor_controller: motor_controller.move_forward(speed)
    if steering_servo: steering_servo.center()
    return jsonify({"status": "success", "action": "forward"})

@app.route('/api/backward', methods=['POST'])
def backward():
    data = request.json
    speed = float(data.get('speed', 50.0))
    if motor_controller: motor_controller.move_backward(speed)
    if steering_servo: steering_servo.center()
    return jsonify({"status": "success", "action": "backward"})

@app.route('/api/turn_left', methods=['POST'])
def turn_left():
    data = request.json
    speed = float(data.get('speed', 50.0))
    if steering_servo: steering_servo.steer_left()
    if motor_controller: motor_controller.turn_left(speed)
    return jsonify({"status": "success", "action": "turn_left"})

@app.route('/api/turn_right', methods=['POST'])
def turn_right():
    data = request.json
    speed = float(data.get('speed', 50.0))
    if steering_servo: steering_servo.steer_right()
    if motor_controller: motor_controller.turn_right(speed)
    return jsonify({"status": "success", "action": "turn_right"})

@app.route('/api/set_servo', methods=['POST'])
def set_servo():
    data = request.json
    angle = float(data.get('angle', 90.0))
    if steering_servo: steering_servo.set_angle(angle)
    return jsonify({"status": "success", "action": "set_servo"})

@app.route('/api/reverse_turn', methods=['POST'])
def reverse_turn():
    data = request.json
    speed = float(data.get('speed', 50.0))
    # Reverse turn keeps current steering angle but moves backwards
    if motor_controller: motor_controller.reverse_turn(speed)
    return jsonify({"status": "success", "action": "reverse_turn"})

@app.route('/api/stop', methods=['POST'])
def stop():
    if motor_controller: motor_controller.stop()
    return jsonify({"status": "success", "action": "stop"})

@app.route('/api/sensors', methods=['GET'])
def get_sensors():
    with data_lock:
        s_data = {}
        for name, sensor in sensors.items():
            if hasattr(sensor, "get_data"):
                s_data[name] = sensor.get_data()
            
        f_data = fusion.get_orientation() if fusion else {}
        
        motor_speed = 0.0 # Just a placeholder since motor_controller doesn't track current_speed cleanly yet
        servo_angle = steering_servo.current_angle if steering_servo else 90.0

    return jsonify({
        "status": "success",
        "sensors": s_data,
        "fusion": f_data,
        "actuators": {
            "motor_speed": motor_speed,
            "servo_angle": servo_angle
        }
    })

def start_server(motors, servo, sensor_dict, fusion_module, lock, port=5000):
    global motor_controller, steering_servo, sensors, fusion, data_lock
    motor_controller = motors
    steering_servo = servo
    sensors = sensor_dict
    fusion = fusion_module
    data_lock = lock
    print(f"[Web] Starting server on port {port}...")
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
