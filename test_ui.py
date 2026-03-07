from flask import Flask, render_template, jsonify, request
app = Flask(__name__, template_folder='templates', static_folder='static')

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/state')
def api_state(): return jsonify({"motion_state": "STOPPED", "mode": "AUTONOMOUS"})

@app.route('/api/location')
def api_location(): return jsonify({"lat": 13.08, "lng": 80.27, "speed": 15.5})

@app.route('/api/sensors')
def api_sensors(): return jsonify({
    "gps": {"latitude": 13.08, "longitude": 80.27, "altitude": 10, "speed_kmh": 15.5, "satellites": 8, "fix": True},
    "imu": {"acc_x": 0.1, "acc_y": 0.2, "acc_z": 9.8, "gyro_x": 0, "gyro_y": 0, "gyro_z": 0.5, "temp": 32.5},
    "mag": {"mag_x": 10, "mag_y": 20, "mag_z": -5, "heading": 45, "compass_direction": "NE"}
})

@app.route('/api/config', methods=['POST'])
def api_config(): return jsonify({"status": "ok"})

@app.route('/api/mode', methods=['POST'])
def api_mode(): return jsonify({"status": "ok", "mode": request.json.get('mode', 'AUTONOMOUS')})

@app.route('/api/control', methods=['POST'])
def api_control(): return jsonify({"status": "ok"})

@app.route('/api/navigate', methods=['POST'])
def api_navigate(): return jsonify({"status": "ok"})

@app.route('/api/pause', methods=['POST'])
def api_pause(): return jsonify({"status": "ok"})

@app.route('/api/continue', methods=['POST'])
def api_continue(): return jsonify({"status": "ok"})

@app.route('/api/stop', methods=['POST'])
def api_stop(): return jsonify({"status": "ok"})

if __name__ == '__main__':
    print("Testing server running at http://127.0.0.1:5005")
    app.run(host='0.0.0.0', port=5005, debug=False)
