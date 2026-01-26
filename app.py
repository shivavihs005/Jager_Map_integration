from flask import Flask, render_template, jsonify, request
from gps_reader import gps_reader
from navigator import navigator

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

@app.route('/api/navigate', methods=['POST'])
def start_navigation():
    data = request.json
    lat = data.get('lat')
    lng = data.get('lng')
    
    if lat is None or lng is None:
        return jsonify({"status": "error", "message": "Missing coordinates"}), 400
        
    navigator.set_destination(lat, lng)
    navigator.start_navigation()
    
    return jsonify({"status": "success", "message": "Navigation started"})

@app.route('/api/stop', methods=['POST'])
def stop_navigation():
    navigator.stop_navigation()
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
    except Exception:
        print("Could not detect IP address. Check 'ifconfig' or 'hostname -I'")

    # Host='0.0.0.0' allows access from other devices on the network
    app.run(debug=True, host='0.0.0.0', use_reloader=False)
