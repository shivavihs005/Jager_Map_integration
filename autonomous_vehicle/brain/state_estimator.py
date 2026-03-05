"""
state_estimator.py
Central hub: reads all sensors, runs fusion, distributes state.
Runs in its own high-frequency background thread.
"""
import time
import threading
import math

from vehicle_config import (SENSOR_LOOP_HZ, STATIONARY_ACCEL_THRESHOLD,
                            STATIONARY_GPS_SPEED_KMH)


class StateEstimator:
    """
    Owns the sensor read + fusion cycle.
    Consumer modules call get_state() for a consistent snapshot.
    """

    def __init__(self, imu, magnetometer, gps, madgwick, ekf):
        self._imu  = imu
        self._mag  = magnetometer
        self._gps  = gps
        self._mw   = madgwick
        self._ekf  = ekf
        self._lock = threading.Lock()

        # State snapshot — updated every sensor tick
        self._state = {
            # Attitude
            "roll_deg":    0.0,
            "pitch_deg":   0.0,
            "yaw_deg":     0.0,

            # EKF fused position
            "x_m":         0.0,
            "y_m":         0.0,
            "heading_deg": 0.0,
            "velocity_ms": 0.0,
            "velocity_kmh":0.0,

            # GPS raw
            "latitude":    0.0,
            "longitude":   0.0,
            "gps_speed_kmh": 0.0,
            "gps_fix":     False,
            "satellites":  0,

            # IMU raw
            "acc_x": 0.0, "acc_y": 0.0, "acc_z": 0.0,
            "gyro_x": 0.0,"gyro_y": 0.0,"gyro_z": 0.0,
            "accel_magnitude": 0.0,

            # Status
            "is_moving":   False,
            "timestamp":   0.0,
        }

        # EKF GPS update gating — only update if fix
        self._last_gps_lat = None
        self._last_gps_lon = None

        self._running = False
        self._thread  = None
        self._dt = 1.0 / SENSOR_LOOP_HZ

    # ── Lifecycle ───────────────────────────────────────────────────────────
    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="StateEstimator")
        self._thread.start()
        print("[StateEst] Started")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)

    # ── Sensor loop ─────────────────────────────────────────────────────────
    def _loop(self):
        t_last = time.time()
        while self._running:
            t_now = time.time()
            dt    = t_now - t_last
            t_last = t_now

            # 1. Read raw sensors
            self._imu.update()
            self._mag.update()

            imu_data = self._imu.get_data()
            mag_data = self._mag.get_data()

            ax = imu_data["acc_x"]
            ay = imu_data["acc_y"]
            az = imu_data["acc_z"]
            gx = math.radians(imu_data["gyro_x"])
            gy = math.radians(imu_data["gyro_y"])
            gz = math.radians(imu_data["gyro_z"])

            # 2. Madgwick filter
            self._mw.update(dt, gx, gy, gz, ax, ay, az,
                            mag_data["mag_x"], mag_data["mag_y"], mag_data["mag_z"])
            roll_d, pitch_d, yaw_d = self._mw.get_euler_deg()
            yaw_rad = math.radians(yaw_d)

            # 3. EKF: predict + heading + GPS + accel
            self._ekf.predict(dt)
            self._ekf.update_heading(yaw_rad)

            gps_data = self._gps.get_data()
            if gps_data["fix"] and gps_data["latitude"] != 0:
                self._ekf.update_gps(gps_data["latitude"], gps_data["longitude"])

            # Forward accel estimation (projection along heading)
            ah = ax * math.cos(yaw_rad) + ay * math.sin(yaw_rad)
            self._ekf.update_acceleration(ah)

            ekf_s = self._ekf.get_state()
            fused_lat, fused_lon = self._ekf.get_gps_from_xy()

            # 4. Movement detection
            a_mag  = self._imu.get_magnitude()
            moving = (abs(a_mag - 9.81) > STATIONARY_ACCEL_THRESHOLD or
                      gps_data["speed_kmh"] > STATIONARY_GPS_SPEED_KMH)

            # 5. Publish snapshot
            with self._lock:
                s = self._state
                s["roll_deg"]    = roll_d
                s["pitch_deg"]   = pitch_d
                s["yaw_deg"]     = yaw_d

                s["x_m"]         = ekf_s["x"]
                s["y_m"]         = ekf_s["y"]
                s["heading_deg"] = ekf_s["heading_deg"]
                s["velocity_ms"] = ekf_s["velocity_ms"]
                s["velocity_kmh"]= ekf_s["velocity_kmh"]

                s["latitude"]    = fused_lat
                s["longitude"]   = fused_lon
                s["gps_speed_kmh"] = gps_data["speed_kmh"]
                s["gps_fix"]     = gps_data["fix"]
                s["satellites"]  = gps_data["satellites"]

                s["acc_x"]  = ax; s["acc_y"] = ay; s["acc_z"] = az
                s["gyro_x"] = math.degrees(gx)
                s["gyro_y"] = math.degrees(gy)
                s["gyro_z"] = math.degrees(gz)
                s["accel_magnitude"] = a_mag

                s["is_moving"] = moving
                s["timestamp"] = t_now

            # Pace the loop
            elapsed = time.time() - t_now
            sleep_t = self._dt - elapsed
            if sleep_t > 0:
                time.sleep(sleep_t)

    # ── Consumer API ────────────────────────────────────────────────────────
    def get_state(self):
        """Thread-safe snapshot of the full vehicle state."""
        with self._lock:
            return dict(self._state)

    def get_position(self):
        with self._lock:
            return self._state["latitude"], self._state["longitude"]

    def get_heading(self):
        with self._lock:
            return self._state["heading_deg"]

    def get_speed_kmh(self):
        with self._lock:
            return self._state["velocity_kmh"]

    def is_moving(self):
        with self._lock:
            return self._state["is_moving"]
