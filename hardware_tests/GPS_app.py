import sys
import os
import time
from flask import Flask, render_template, jsonify

# Add parent directory to path to import gps_reader
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from gps_reader import gps_reader

app = Flask(__name__)

# Start GPS reading in background
try:
    gps_reader.start()
except Exception as e:
    print(f"Failed to start GPS: {e}")

@app.route('/')
def index():
    return render_template('gps_index.html')

@app.route('/api/gps')
def get_gps():
    location = gps_reader.get_location()
    return jsonify(location)

if __name__ == '__main__':
    # Helper to print the actual IP address for the user
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip_address = s.getsockname()[0]
        s.close()
        print(f"--------------------------------------------------")
        print(f" GPS Test Server is running!")
        print(f" Access it at: http://{ip_address}:5001")
        print(f"--------------------------------------------------")
    except Exception:
        print("Could not detect IP address.")

    app.run(debug=True, host='0.0.0.0', port=5001, use_reloader=False)
