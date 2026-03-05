"""
mission_manager.py
High-level state machine for autonomous navigation.

States:
    IDLE      → waiting for a destination
    NAVIGATE  → actively following path (Pure Pursuit + PID)
    STOP      → destination reached or emergency
"""
import time
import threading
import math

from vehicle_config import (CONTROL_LOOP_HZ, BASE_SPEED_PCT,
                            MIN_SPEED_PCT, MAX_SPEED_PCT,
                            PID_KP, PID_KI, PID_KD,
                            PURE_PURSUIT_LOOKAHEAD_M,
                            WHEELBASE_M, MAX_STEERING_ANGLE_DEG)


class PIDController:
    def __init__(self, kp, ki, kd, output_min, output_max):
        self.kp = kp; self.ki = ki; self.kd = kd
        self.out_min = output_min; self.out_max = output_max
        self._integral = 0.0
        self._prev_error = 0.0

    def reset(self):
        self._integral = 0.0
        self._prev_error = 0.0

    def compute(self, error, dt):
        self._integral += error * dt
        # Anti-windup clamp
        self._integral = max(self.out_min / self.ki if self.ki else self._integral,
                             min(self.out_max / self.ki if self.ki else self._integral,
                                 self._integral))
        derivative = (error - self._prev_error) / dt if dt > 0 else 0.0
        self._prev_error = error
        out = self.kp * error + self.ki * self._integral + self.kd * derivative
        return max(self.out_min, min(self.out_max, out))


def angle_diff_deg(target, current):
    """Shortest signed difference, range [-180, 180]."""
    d = target - current
    return (d + 180) % 360 - 180


class MissionManager:
    IDLE     = "IDLE"
    NAVIGATE = "NAVIGATE"
    STOP     = "STOP"

    def __init__(self, state_estimator, path_planner,
                 pure_pursuit, motor, servo):
        self._state_est   = state_estimator
        self._path        = path_planner
        self._pursuit     = pure_pursuit
        self._motor       = motor
        self._servo       = servo

        self._state   = self.IDLE
        self._lock    = threading.Lock()
        self._running = False
        self._thread  = None
        self._dt = 1.0 / CONTROL_LOOP_HZ
        self._trajectory = []       # List of (lat, lon) visited

        # PID for heading
        self._pid = PIDController(PID_KP, PID_KI, PID_KD,
                                  -MAX_STEERING_ANGLE_DEG,
                                   MAX_STEERING_ANGLE_DEG)

    # ── Lifecycle ──────────────────────────────────────────────────────────
    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True,
                                        name="MissionManager")
        self._thread.start()
        print("[Mission] Started")

    def stop(self):
        self._running = False
        self._motor.stop()
        self._servo.center()

    # ── Public commands ────────────────────────────────────────────────────
    def navigate_to(self, lat, lon):
        """Set a destination and begin autonomous navigation."""
        self._path.set_destination(lat, lon)
        self._pid.reset()
        self._trajectory.clear()
        with self._lock:
            self._state = self.NAVIGATE
        print(f"[Mission] Navigate → ({lat:.6f}, {lon:.6f})")

    def abort(self):
        with self._lock:
            self._state = self.STOP
        self._motor.stop()
        self._servo.center()
        print("[Mission] ABORTED")

    def set_max_speed(self, pct):
        """Update cruise speed cap from dashboard slider (0-100)."""
        import vehicle_config as vc
        vc.BASE_SPEED_PCT = max(10.0, min(100.0, float(pct)))
        print(f"[Mission] Max speed → {vc.BASE_SPEED_PCT:.0f}%")

    def get_state(self):
        with self._lock:
            return self._state

    def get_trajectory(self):
        return list(self._trajectory)

    # ── Control loop ───────────────────────────────────────────────────────
    def _loop(self):
        t_last = time.time()
        while self._running:
            t_now = time.time()
            dt    = t_now - t_last
            t_last = t_now

            with self._lock:
                current_state = self._state

            if current_state == self.NAVIGATE:
                self._navigate_step(dt)
            elif current_state == self.STOP:
                self._motor.stop()
                self._servo.center()

            elapsed = time.time() - t_now
            sleep_t = self._dt - elapsed
            if sleep_t > 0:
                time.sleep(sleep_t)

    def _navigate_step(self, dt):
        vehicle = self._state_est.get_state()
        lat     = vehicle["latitude"]
        lon     = vehicle["longitude"]
        heading = vehicle["heading_deg"]
        speed   = vehicle["velocity_ms"]

        # Record trajectory
        if lat != 0 or lon != 0:
            if not self._trajectory or \
               math.hypot(lat - self._trajectory[-1][0],
                          lon - self._trajectory[-1][1]) > 1e-6:
                self._trajectory.append((lat, lon))

        # Advance waypoint if reached
        self._path.check_and_advance(lat, lon)

        if self._path.is_complete():
            print("[Mission] Destination reached!")
            self._motor.stop()
            self._servo.center()
            with self._lock:
                self._state = self.STOP
            return

        # Get look-ahead waypoint
        wp = self._path.get_lookahead_waypoint(lat, lon, PURE_PURSUIT_LOOKAHEAD_M)
        if wp is None:
            return

        # Pure Pursuit → desired steering angle
        desired_steer = self._pursuit.compute_steering(lat, lon, heading,
                                                       wp[0], wp[1])

        # PID on heading error to smooth the output
        heading_error = angle_diff_deg(
            self._pursuit.compute_steering(lat, lon, heading, wp[0], wp[1]),
            0.0)   # error from 0 (straight)
        pid_steer = self._pid.compute(desired_steer, dt)

        # Send to servo
        self._servo.set_angle(pid_steer)

        # Adaptive speed: slower when turning more
        steer_ratio = abs(pid_steer) / MAX_STEERING_ANGLE_DEG
        target_speed = BASE_SPEED_PCT * (1.0 - steer_ratio * 0.6)
        target_speed = max(MIN_SPEED_PCT, min(MAX_SPEED_PCT, target_speed))

        self._motor.set_speed(target_speed)
