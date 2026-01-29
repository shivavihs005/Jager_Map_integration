import sys
import os
import time
from flask import Flask, render_template, jsonify, request

# Add parent directory to path to import car_controller
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from car_controller import car

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('motors_index.html')

@app.route('/api/control', methods=['POST'])
def control():
    try:
        data = request.json
        # Speed: -100 to 100
        speed = float(data.get('speed', 0))
        # Angle: -1.0 to 1.0
        angle = float(data.get('angle', 0))
        
        print(f"Set Speed: {speed}, Angle: {angle}")
        
        car.set_speed(speed)
        car.set_steering(angle)
        
        return jsonify({"status": "success", "speed": speed, "angle": angle})
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/api/stop', methods=['POST'])
def stop():
    car.stop()
    return jsonify({"status": "stopped"})

if __name__ == '__main__':
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip_address = s.getsockname()[0]
        s.close()
        print(f"--------------------------------------------------")
        print(f" Motors Test Server is running!")
        print(f" Access it at: http://{ip_address}:5002")
        print(f"--------------------------------------------------")
    except Exception:
        print("Could not detect IP address.")

    app.run(debug=True, host='0.0.0.0', port=5002, use_reloader=False)
