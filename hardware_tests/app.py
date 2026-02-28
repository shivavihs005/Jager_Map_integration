"""
Standalone hardware testing application for Jager.
Uses the modular robotics stack: IMU (Madgwick), GPS, Fusion, State Machine.

Run from within the hardware_tests directory:
    cd hardware_tests
    python app.py
"""

import sys
import os
import time
import threading
from flask import Flask, render_template, request, jsonify

# Add parent directory to sys.path to import car_controller
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

try:
    from car_controller import car
except ImportError as e:
    print(f"Error importing car_controller: {e}")
    class MockCar:
        def set_speed(self, speed): pass
        def set_steering(self, angle): pass
        def stop(self): pass
    car = MockCar()

# --- Import Robotics Modules ---
from imu import IMU
from gps import GPS
from fusion import SensorFusion
from state_machine import StateMachine
from behavior_controller import BehaviorController

# --- Initialize Stack ---
imu = IMU()
gps = GPS()
fusion = SensorFusion()
sm = StateMachine()

data_lock = threading.Lock()

# --- Initialize Behavior Controller ---
controller = BehaviorController(car, fusion, data_lock)


def sensor_loop():
    """Main sensor loop running at ~100Hz for IMU updates."""
    while True:
        imu.update()

        execution_time = time.time()
        sleep_time = 0.01 - (time.time() - execution_time)
        if sleep_time > 0:
            time.sleep(sleep_time)


def gps_loop():
    """GPS loop reads serial at whatever rate the module outputs (~1-5Hz)."""
    while True:
        gps.update()
        time.sleep(0.05)  # Check at 20Hz, GPS outputs at 1-5Hz


def fusion_loop():
    """Fusion loop blends IMU + GPS at 20Hz."""
    while True:
        imu_yaw = imu.get_yaw()
        gps_data = gps.get_data()

        with data_lock:
            fusion.update(imu_yaw, gps_data["heading"], gps_data["speed"])
            sm.update(gps_data["speed"])

        time.sleep(0.05)  # 20Hz


def controller_loop():
    """Behavior controller loop runs at 20Hz."""
    while True:
        controller.update()
        time.sleep(0.05)  # 20Hz


# --- Flask App ---
app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/motor', methods=['POST'])
def control_motor():
    data = request.json
    speed = float(data.get('speed', 0.0))
    speed = max(-100.0, min(100.0, speed))
    car.set_speed(speed)
    return jsonify({"status": "success", "speed": speed})

@app.route('/api/servo', methods=['POST'])
def control_servo():
    data = request.json
    angle = float(data.get('angle', 90.0))
    angle = max(0.0, min(180.0, angle))
    angle_percent = (angle - 90) / 90.0
    car.set_steering(angle_percent)
    return jsonify({"status": "success", "angle": angle, "percent": angle_percent})

@app.route('/api/sensors', methods=['GET'])
def get_sensors():
    imu_data = imu.get_data()
    gps_data = gps.get_data()

    with data_lock:
        fusion_data = fusion.get_data()
        state_data = sm.get_data()

    controller_data = controller.get_data()

    return jsonify({
        "status": "success",
        "imu": imu_data,
        "gps": gps_data,
        "fusion": fusion_data,
        "state": state_data,
        "controller": controller_data
    })

@app.route('/api/stop', methods=['POST'])
def stop_all():
    controller.set_state("IDLE")
    car.stop()
    return jsonify({"status": "success", "message": "Stopped"})


@app.route('/api/state', methods=['POST'])
def set_behavior_state():
    """Set the behavior controller state (FORWARD, BACKWARD, IDLE, etc.)."""
    data = request.json
    state = data.get('state', 'IDLE').upper()

    # Pass user speed from request if provided
    speed = data.get('speed', None)
    if speed is not None:
        controller.user_speed = float(speed)

    controller.set_state(state)
    return jsonify({"status": "success", "state": state})


@app.route('/api/reset_imu', methods=['POST'])
def reset_imu():
    imu.q = [1.0, 0.0, 0.0, 0.0]
    with data_lock:
        fusion.yaw = 0.0
    return jsonify({"status": "success"})


if __name__ == '__main__':
    print("=" * 50)
    print(" JAGER HARDWARE TEST — ROBOTICS STACK")
    print("=" * 50)

    # Calibrate IMU at startup
    imu.calibrate()

    # Launch background threads
    threading.Thread(target=sensor_loop, daemon=True).start()
    threading.Thread(target=gps_loop, daemon=True).start()
    threading.Thread(target=fusion_loop, daemon=True).start()
    threading.Thread(target=controller_loop, daemon=True).start()

    print("[READY] All systems online. Behavior controller active.")
    print("Starting Hardware Test Server on port 5001...")
    app.run(host='0.0.0.0', port=5001, debug=True, use_reloader=False)
