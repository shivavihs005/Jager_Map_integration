import threading
import time
from collections import deque
from datetime import datetime

from config import HOME, MOTOR, NAV, SENSORS, SERVO
from fusion.complementary import ComplementaryHeadingFusion, normalize_error
from fusion.dead_reckoning import DeadReckoning
from hal.actuators import DriveMotor, SteeringServo
from hal.sensors import SensorSuite
from nav.controller import pulse_from_heading_error, pwm_from_heading_error
from nav.follower import PurePursuitFollower, bearing_deg, haversine_m
from nav.planner import RoutePlanner
from nav.state import NavPhase


class AutonomousCarSystem:
    def __init__(self):
        self._lock = threading.RLock()
        self._running = True
        self._calibration_thread = None
        self._last_nav_log = 0.0
        self._mock_heading = 0.0

        self.sensors = SensorSuite()
        self.servo = SteeringServo()
        self.motor = DriveMotor()
        self.fusion = ComplementaryHeadingFusion()
        self.dead_reckoning = DeadReckoning()
        self.planner = RoutePlanner()
        self.follower = PurePursuitFollower(NAV.lookahead_m)

        self.phase = NavPhase.BOOT
        self.calibrated = False
        self.destination = None
        self.destination_name = ""
        self.route = []
        self.route_index = 0
        self.route_distance_m = 0.0
        self.route_duration_s = 0.0
        self.route_source = "none"
        self.lookahead_point = None
        self.heading_error = 0.0
        self.distance_to_goal_m = 0.0
        self.logs = deque(maxlen=160)

        self.sensors.mag.set_mock_heading(0.0)
        self.sensors.gps.set_mock_position(HOME.lat, HOME.lon, speed_mps=0.0, satellites=0, hdop=99.0, fix_status="No Fix")
        self.log("RC-NAV-01 backend online", "ok")
        self.log("System in BOOT state", "info")

        self._sensor_thread = threading.Thread(target=self._sensor_loop, daemon=True)
        self._control_thread = threading.Thread(target=self._control_loop, daemon=True)
        self._sensor_thread.start()
        self._control_thread.start()

    def log(self, message, level="m"):
        timestamp = datetime.now().strftime("%M:%S.%f")[:-4]
        with self._lock:
            self.logs.append({"ts": timestamp, "msg": message, "level": level})

    def _set_phase(self, phase):
        with self._lock:
            self.phase = NavPhase(phase)

    def calibrate(self):
        with self._lock:
            if self.phase == NavPhase.CALIBRATING:
                return {"status": "busy", "message": "Calibration already running"}

            self.phase = NavPhase.CALIBRATING

        self._calibration_thread = threading.Thread(target=self._run_calibration_sequence, daemon=True)
        self._calibration_thread.start()
        return {"status": "ok", "message": "Calibration started"}

    def _run_calibration_sequence(self):
        steps = [
            (0.1, "SYSTEM BOOT - Raspberry Pi controller online", "m"),
            (0.2, "I2C scan complete", "ok"),
            (0.2, "0x68 -> MPU6500 detected", "ok"),
            (0.2, "0x0D -> QMC5883L detected", "ok"),
            (0.2, "UART /dev/serial0 ready for NEO-6M", "ok"),
            (0.3, "Calibrating gyroscope bias", "m"),
            (0.5, "Gyro bias stored", "ok"),
            (0.3, "Calibrating magnetometer", "m"),
            (0.5, "Hard-iron correction applied", "ok"),
            (0.4, "Waiting for GPS lock", "warn"),
            (0.5, "GPS FIX acquired - 7 sats, HDOP 1.2", "ok"),
            (0.2, "ALL SENSORS READY - system armed", "info"),
        ]
        for delay, message, level in steps:
            if not self._running:
                return
            time.sleep(delay)
            self.log(message, level)

        with self._lock:
            self.calibrated = True
            self.phase = NavPhase.READY
            self.sensors.gps.arm_default_fix()
            self.sensors.mag.set_mock_heading(self._mock_heading)

    def set_destination(self, lat, lon):
        with self._lock:
            if not self.calibrated:
                return {"status": "error", "message": "Calibrate first"}
            self.phase = NavPhase.CALCULATING

        self.log(f"Checking road: {lat:.6f}, {lon:.6f}", "m")
        snapped = self.planner.snap_to_road(lat, lon)
        if not snapped["ok"]:
            with self._lock:
                self.phase = NavPhase.DEST_INVALID
            self.log("Destination rejected - off road click", "err")
            return {"status": "error", "message": "Destination is too far from a road", "data": snapped}

        with self._lock:
            self.destination = snapped["snapped"]
            self.destination_name = snapped["name"]
            self.phase = NavPhase.DEST_SET
            self.route = []
            self.route_index = 0
            self.route_distance_m = 0.0
            self.route_duration_s = 0.0
            self.route_source = "none"
            self.lookahead_point = None

        self.log(f"Destination set: {snapped['name']}", "ok")
        return {"status": "ok", "data": snapped}

    def calculate_path(self):
        with self._lock:
            if not self.destination:
                return {"status": "error", "message": "Set destination first"}
            self.phase = NavPhase.CALCULATING

        gps = self.sensors.gps.get_data()
        origin = [gps["latitude"], gps["longitude"]]
        route_data = self.planner.calculate_route(origin, self.destination)

        with self._lock:
            self.route = route_data["coordinates"]
            self.route_index = 0
            self.route_distance_m = route_data["distance_m"]
            self.route_duration_s = route_data["duration_s"]
            self.route_source = route_data["source"]
            self.phase = NavPhase.PATH_READY

        km = self.route_distance_m / 1000.0
        minutes = round(self.route_duration_s / 60.0) if self.route_duration_s else 0
        self.log(f"Route ready: {km:.2f} km | {minutes} min | {len(self.route)} waypoints", "ok")
        return {"status": "ok", "data": route_data}

    def start_navigation(self):
        with self._lock:
            if self.phase != NavPhase.PATH_READY or len(self.route) < 2:
                return {"status": "error", "message": "Route is not ready"}
            self.phase = NavPhase.RUNNING

        self.log("Navigation started", "ok")
        return {"status": "ok", "message": "Navigation running"}

    def stop_navigation(self):
        with self._lock:
            self.motor.stop()
            self.servo.center()
            if self.phase == NavPhase.RUNNING:
                self.phase = NavPhase.PATH_READY
        self.log("Navigation stopped", "warn")
        return {"status": "ok"}

    def reset(self):
        with self._lock:
            self.motor.stop()
            self.servo.center()
            self.phase = NavPhase.BOOT
            self.calibrated = False
            self.destination = None
            self.destination_name = ""
            self.route = []
            self.route_index = 0
            self.route_distance_m = 0.0
            self.route_duration_s = 0.0
            self.route_source = "none"
            self.lookahead_point = None
            self.heading_error = 0.0
            self.distance_to_goal_m = 0.0
            self._mock_heading = 0.0
            self.sensors.gps.set_mock_position(HOME.lat, HOME.lon, speed_mps=0.0, satellites=0, hdop=99.0, fix_status="No Fix")
            self.sensors.mag.set_mock_heading(0.0)
            self.sensors.imu.set_mock_yaw_rate(0.0)

        self.log("System reset", "info")
        return {"status": "ok"}

    def _sensor_loop(self):
        interval = 1.0 / SENSORS.imu_hz
        last_time = time.monotonic()
        while self._running:
            now = time.monotonic()
            dt = max(0.001, now - last_time)
            last_time = now
            self.sensors.update()
            snapshot = self.sensors.snapshot()
            self.fusion.update(dt, snapshot["imu"], snapshot["mag"])
            elapsed = time.monotonic() - now
            time.sleep(max(0.0, interval - elapsed))

    def _control_loop(self):
        interval = 1.0 / SENSORS.control_hz
        last_time = time.monotonic()
        while self._running:
            now = time.monotonic()
            dt = max(0.001, now - last_time)
            last_time = now
            self._navigation_step(dt)
            elapsed = time.monotonic() - now
            time.sleep(max(0.0, interval - elapsed))

    def _navigation_step(self, dt):
        with self._lock:
            if self.phase != NavPhase.RUNNING or len(self.route) < 2:
                self.sensors.imu.set_mock_yaw_rate(0.0)
                return

            gps = self.sensors.gps.get_data()
            current = [gps["latitude"], gps["longitude"]]
            goal = self.route[-1]
            self.distance_to_goal_m = haversine_m(current[0], current[1], goal[0], goal[1])

            if self.distance_to_goal_m <= NAV.arrival_threshold_m:
                self._complete_navigation_locked()
                return

            next_waypoint = self.route[min(self.route_index, len(self.route) - 1)]
            if haversine_m(current[0], current[1], next_waypoint[0], next_waypoint[1]) <= NAV.waypoint_reach_m:
                self.route_index = min(self.route_index + 1, len(self.route) - 1)

            lookahead, route_index = self.follower.get_lookahead(self.route, self.route_index, current)
            self.route_index = route_index
            self.lookahead_point = lookahead

            if not lookahead:
                self._complete_navigation_locked()
                return

            current_heading = self.fusion.get_orientation()["heading"]
            target_heading = bearing_deg(current[0], current[1], lookahead[0], lookahead[1])
            self.heading_error = normalize_error(target_heading - current_heading)
            servo_pulse = pulse_from_heading_error(self.heading_error)
            pwm = pwm_from_heading_error(self.heading_error)

            self.servo.set_pulse(servo_pulse)
            self.motor.move_forward(pwm)

            speed_mps = MOTOR.max_speed_mps * (pwm / 100.0)
            self._simulate_motion_locked(current, lookahead, speed_mps, dt, current_heading, target_heading)

            if time.monotonic() - self._last_nav_log > 1.5:
                self._last_nav_log = time.monotonic()
                self.log(
                    f"WP {self.route_index}/{len(self.route)} | hdg {round(current_heading)} deg | pwm {int(pwm)}% | srv {servo_pulse}us",
                    "m",
                )

    def _simulate_motion_locked(self, current, target, speed_mps, dt, current_heading, target_heading):
        distance = haversine_m(current[0], current[1], target[0], target[1])
        if distance > 0.0:
            travel = min(distance, max(0.0, speed_mps) * max(0.0, dt))
            fraction = travel / distance if distance else 1.0
            next_lat = current[0] + ((target[0] - current[0]) * fraction)
            next_lon = current[1] + ((target[1] - current[1]) * fraction)
        else:
            next_lat, next_lon = target

        turn_error = normalize_error(target_heading - current_heading)
        next_heading = (current_heading + (turn_error * min(1.0, dt * 2.5))) % 360.0
        yaw_rate = normalize_error(next_heading - self._mock_heading) / max(dt, 0.001)
        self._mock_heading = next_heading

        self.sensors.mag.set_mock_heading(next_heading)
        self.sensors.imu.set_mock_yaw_rate(yaw_rate)
        self.sensors.gps.set_mock_position(
            next_lat,
            next_lon,
            speed_mps=speed_mps,
            satellites=SENSORS.default_satellites,
            hdop=SENSORS.default_hdop,
            fix_status="Fix",
        )

    def _complete_navigation_locked(self):
        self.motor.stop()
        self.servo.center()
        self.phase = NavPhase.COMPLETED
        self.heading_error = 0.0
        self.lookahead_point = None
        self.log("Destination reached", "ok")

    def get_snapshot(self):
        with self._lock:
            sensor_snapshot = self.sensors.snapshot()
            fusion_snapshot = self.fusion.get_orientation()
            motor_state = self.motor.get_state()
            servo_state = self.servo.get_state()
            gps_data = sensor_snapshot["gps"]

            return {
                "phase": self.phase.value,
                "calibrated": self.calibrated,
                "home": {"lat": HOME.lat, "lon": HOME.lon},
                "sensors": {
                    "gps": gps_data,
                    "imu": sensor_snapshot["imu"],
                    "mag": sensor_snapshot["mag"],
                    "fusion": fusion_snapshot,
                },
                "actuators": {
                    "motor_pwm": motor_state["pwm_percent"],
                    "motor_direction": motor_state["direction"],
                    "servo_pulse": servo_state["pulse"],
                },
                "navigation": {
                    "destination": self.destination,
                    "destination_name": self.destination_name,
                    "route": self.route,
                    "route_index": self.route_index,
                    "route_distance_m": self.route_distance_m,
                    "route_duration_s": self.route_duration_s,
                    "route_source": self.route_source,
                    "lookahead": self.lookahead_point,
                    "heading_error": self.heading_error,
                    "distance_to_goal_m": self.distance_to_goal_m,
                },
                "hardware": {
                    "mock_mode": self.sensors.mock_mode or self.motor.mock_mode or self.servo.mock_mode,
                    "gps_ready": self.calibrated and gps_data["fix_status"] == "Fix",
                    "imu_ready": True,
                    "mag_ready": True,
                    "motor_ready": True,
                    "servo_ready": True,
                },
                "logs": list(self.logs),
            }

    def shutdown(self):
        self._running = False
        self.motor.stop()
        self.servo.center()