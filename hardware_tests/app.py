"""
Standalone hardware testing application for Jager.
Provides a simple web interface to test the motor, steering servo, gyro, and accel directly.

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
    class MockCar:
        def set_speed(self, speed): print(f"Mock Motor Speed: {speed}")
        def set_steering(self, angle): print(f"Mock Steering: {angle}")
        def stop(self): print("Mock Stop")
    car = MockCar()

# MPU6500 integration for hardware tests
try:
    from smbus2 import SMBus
    SMBUS_AVAILABLE = True
    bus = SMBus(1)
    mpu_address = 0x68
    bus.write_byte_data(mpu_address, 0x6B, 0) # Wake up
    # Set Gyro to +/- 250 deg/s
    bus.write_byte_data(mpu_address, 0x1B, 0x00)
    # Set Accel to +/- 2g
    bus.write_byte_data(mpu_address, 0x1C, 0x00)
except Exception as e:
    SMBUS_AVAILABLE = False
    print(f"IMU not available for hardware tests: {e}")

app = Flask(__name__)

def read_word_2c(addr):
    try:
        high = bus.read_byte_data(mpu_address, addr)
        low = bus.read_byte_data(mpu_address, addr+1)
        val = (high << 8) + low
        if val >= 0x8000:
            return -((65535 - val) + 1)
        else:
            return val
    except Exception:
        return 0

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/motor', methods=['POST'])
def control_motor():
    """Endpoint for Motor (-100 to 100)"""
    data = request.json
    speed = float(data.get('speed', 0.0))
    speed = max(-100.0, min(100.0, speed))
    
    car.set_speed(speed)
    return jsonify({"status": "success", "speed": speed})

@app.route('/api/servo', methods=['POST'])
def control_servo():
    """Endpoint for horizontal slider (Angle 0 to 180)"""
    data = request.json
    angle = float(data.get('angle', 90.0))
    angle = max(0.0, min(180.0, angle))
    
    angle_percent = (angle - 90) / 90.0
    car.set_steering(angle_percent)
    return jsonify({"status": "success", "angle": angle, "percent": angle_percent})

@app.route('/api/sensors', methods=['GET'])
def get_sensors():
    """Endpoint to fetch raw IMU values"""
    if not SMBUS_AVAILABLE:
        # Mock values if no I2C is available
        import random
        return jsonify({
            "status": "mock",
            "accel": {"x": 0.0, "y": 0.0, "z": 1.0},
            "gyro": {"x": 0.0, "y": 0.0, "z": round(random.uniform(-0.5, 0.5), 2)}
        })
    
    # Read Accelerometer (±2g = 16384 LSB/g)
    ax = read_word_2c(0x3B) / 16384.0
    ay = read_word_2c(0x3D) / 16384.0
    az = read_word_2c(0x3F) / 16384.0
    
    # Read Gyroscope (±250°/s = 131 LSB/°/s)
    gx = read_word_2c(0x43) / 131.0
    gy = read_word_2c(0x45) / 131.0
    gz = read_word_2c(0x47) / 131.0
    
    return jsonify({
        "status": "success",
        "accel": {"x": round(ax,2), "y": round(ay,2), "z": round(az,2)},
        "gyro": {"x": round(gx,2), "y": round(gy,2), "z": round(gz,2)}
    })

@app.route('/api/stop', methods=['POST'])
def stop_all():
    car.stop()
    return jsonify({"status": "success", "message": "Stopped"})

if __name__ == '__main__':
    print("Starting Hardware Test Server on port 5001...")
    app.run(host='0.0.0.0', port=5001, debug=True, use_reloader=False)

