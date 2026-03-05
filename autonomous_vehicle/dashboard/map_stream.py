"""
map_stream.py
Background thread that reads vehicle state and pushes it to all
connected WebSocket clients at DASHBOARD_PUSH_HZ.
"""
import time
import threading
from vehicle_config import DASHBOARD_PUSH_HZ


class MapStream:
    def __init__(self, socketio, state_estimator, mission_manager, path_planner):
        self._sio     = socketio
        self._state   = state_estimator
        self._mission = mission_manager
        self._path    = path_planner
        self._running = False
        self._dt = 1.0 / DASHBOARD_PUSH_HZ

    def start(self):
        self._running = True
        threading.Thread(target=self._loop, daemon=True, name="MapStream").start()
        print("[MapStream] Started")

    def stop(self):
        self._running = False

    def _loop(self):
        while self._running:
            t = time.time()
            try:
                s = self._state.get_state()
                payload = {
                    "lat":         s["latitude"],
                    "lon":         s["longitude"],
                    "heading":     s["heading_deg"],
                    "speed_kmh":   round(s["velocity_kmh"], 2),
                    "gps_fix":     s["gps_fix"],
                    "satellites":  s["satellites"],
                    "is_moving":   s["is_moving"],
                    "mission":     self._mission.get_state(),
                    "roll":        round(s["roll_deg"],    1),
                    "pitch":       round(s["pitch_deg"],   1),
                    "yaw":         round(s["yaw_deg"],     1),
                    "acc_mag":     round(s["accel_magnitude"], 3),
                    "trajectory":  self._mission.get_trajectory()[-100:],  # last 100 pts
                    "waypoints":   self._path.get_all_waypoints(),
                }
                self._sio.emit("vehicle_state", payload)
            except Exception as e:
                print(f"[MapStream] Error: {e}")

            elapsed = time.time() - t
            sleep_t = self._dt - elapsed
            if sleep_t > 0:
                time.sleep(sleep_t)
