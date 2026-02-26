"""
Standalone hardware testing application for Jager.
Provides a simple web interface to test the motor and steering servo directly.

Run this file from within the hardware_tests directory:
    cd hardware_tests
    python app.py
"""

import sys
import os
from flask import Flask, render_template, request, jsonify

# Add parent directory to sys.path to import car_controller
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

try:
    from car_controller import car
except ImportError as e:
    print(f"Error importing car_controller: {e}")
    # Create a mock if it fails 
    class MockCar:
        def set_speed(self, speed): print(f"Mock Motor Speed: {speed}")
        def set_steering(self, angle): print(f"Mock Steering: {angle}")
        def stop(self): print("Mock Stop")
    car = MockCar()

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/motor', methods=['POST'])
def control_motor():
    """Endpoint vertical slider (Speed -100 to 100)"""
    data = request.json
    speed = float(data.get('speed', 0.0))
    # Clamp -100 to 100
    speed = max(-100.0, min(100.0, speed))
    
    # Send directly to hardware
    car.set_speed(speed)
    return jsonify({"status": "success", "speed": speed})

@app.route('/api/servo', methods=['POST'])
def control_servo():
    """Endpoint for horizontal slider (Angle 0 to 180).
    The car_controller.py expects an angle_percent from -1.0 to 1.0.
    We'll map 0-180 to -1.0 to 1.0.
    90 = 0.0 (Center)
    0 = -1.0 (Left)
    180 = 1.0 (Right)
    """
    data = request.json
    angle = float(data.get('angle', 90.0))
    
    # Clamp 0 to 180
    angle = max(0.0, min(180.0, angle))
    
    # Map to -1.0 to 1.0
    # angle_percent = (angle - 90) / 90
    angle_percent = (angle - 90) / 90.0
    
    # Send directly to hardware
    car.set_steering(angle_percent)
    return jsonify({"status": "success", "angle": angle, "percent": angle_percent})

@app.route('/api/stop', methods=['POST'])
def stop_all():
    car.stop()
    return jsonify({"status": "success", "message": "Stopped"})

if __name__ == '__main__':
    print("Starting Hardware Test Server on port 5001...")
    # Use port 5001 to avoid conflicting with the main app if it happens to be running
    app.run(host='0.0.0.0', port=5001, debug=True, use_reloader=False)

