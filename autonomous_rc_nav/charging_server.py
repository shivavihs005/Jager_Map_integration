from flask import Flask, render_template
from flask_socketio import SocketIO
from gpiozero import DigitalInputDevice
import time

app = Flask(__name__)
socketio = SocketIO(app)

coil_detect = DigitalInputDevice(18)

@app.route("/")
def index():
    return render_template("dashboard.html")

def monitor_coil():

    last_state = None

    while True:

        state = coil_detect.value

        if state != last_state:

            if state == 1:
                socketio.emit("charging", {"status":"on"})
                print("Charging ON")

            else:
                socketio.emit("charging", {"status":"off"})
                print("Charging OFF")

            last_state = state

        time.sleep(0.2)

@socketio.on("connect")
def connect():
    socketio.start_background_task(monitor_coil)

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
