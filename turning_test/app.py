
from flask import Flask, render_template, request, jsonify
from turn_manager import turn_manager

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/turn', methods=['POST'])
def turn():
    data = request.json
    direction = data.get('direction', 'NORTH')
    turn_manager.set_direction(direction)
    return jsonify({"status": "turning", "target": direction})

@app.route('/status')
def status():
    return jsonify({
        "current_heading": turn_manager.current_heading,
        "target_heading": turn_manager.target_heading,
        "is_turning": turn_manager.turning
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
