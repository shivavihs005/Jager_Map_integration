from flask import Flask, render_template, jsonify
from gps_reader import gps_reader

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

if __name__ == '__main__':
    # Host='0.0.0.0' allows access from other devices on the network
    app.run(debug=True, host='0.0.0.0', use_reloader=False)
