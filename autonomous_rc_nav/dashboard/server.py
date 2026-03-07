from flask import Flask, jsonify, render_template, request

from config import APP


def create_app(system):
    app = Flask(__name__, template_folder="templates")

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.get("/api/state")
    def state():
        return jsonify(system.get_snapshot())

    @app.post("/api/calibrate")
    def calibrate():
        return jsonify(system.calibrate())

    @app.post("/api/destination")
    def destination():
        payload = request.get_json(force=True)
        return jsonify(system.set_destination(float(payload["lat"]), float(payload["lon"])))

    @app.post("/api/route")
    def route():
        return jsonify(system.calculate_path())

    @app.post("/api/navigation/start")
    def start_navigation():
        return jsonify(system.start_navigation())

    @app.post("/api/navigation/stop")
    def stop_navigation():
        return jsonify(system.stop_navigation())

    @app.post("/api/reset")
    def reset():
        return jsonify(system.reset())

    return app


def run_dashboard(system):
    app = create_app(system)
    app.run(host=APP.host, port=APP.port, debug=False, use_reloader=False)