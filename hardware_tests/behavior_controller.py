"""
behavior_controller.py — Robotics Behavior Controller
Professional behavior controller for the Jager autonomous vehicle.

Control Context:
    - IMU provides yaw (-180 to +180 degrees)
    - SensorFusion provides fused_yaw and speed
    - car.set_speed() controls motor
    - car.set_steering() controls steering (-1 to +1, 0.0 is center)

Features:
    - TURN_LEFT_90 and TURN_RIGHT_90 rotate the vehicle approx 90 degrees relative to current yaw.
    - HEADING_HOLD captures current yaw and maintains it against drift.
    - Rotation slows down organically as target is approached.
    - Steering uses full PID control.
    - Motor stops and servo centers strictly upon reaching tolerance.
    - IDLE strictly enforces zero motor and centered steering.
"""
from pid import PIDController

class BehaviorController:
    # ── State Constants ──────────────────────────────────────────────────
    IDLE = "IDLE"
    FORWARD = "FORWARD"
    BACKWARD = "BACKWARD"
    TURN_LEFT_90 = "TURN_LEFT_90"
    TURN_RIGHT_90 = "TURN_RIGHT_90"
    HEADING_HOLD = "HEADING_HOLD"

    # ── Control Parameters ───────────────────────────────────────────────
    TOLERANCE = 3.0            # Degrees error to consider turn complete
    SPEED_TOLERANCE = 0.3        # m/s error to consider speed target reached
    ROTATION_SPEED = 20        # Base motor power percentage for rotation
    INVERT_STEERING = True     # Set True if mechanical steering is inverted

    def __init__(self, car, fusion, data_lock):
        """
        Initialize the behavior controller.
        """
        self.car = car
        self.fusion = fusion
        self.data_lock = data_lock

        # Internal state
        self.state = self.IDLE
        self.user_speed = 50        # User slider speed for FORWARD/BACKWARD
        self.target_yaw = 0.0       # Target yaw for turns / heading hold
        self.current_yaw = 0.0
        self.last_error = 0.0
        self.target_speed = 0.0      # Target speed for forward/backward

        # PIDs
        self.yaw_pid = PIDController(Kp=0.02, Ki=0.0005, Kd=0.01, min_out=-1.0, max_out=1.0)
        self.speed_pid = PIDController(Kp=2.0, Ki=0.5, Kd=0.1, min_out=-100.0, max_out=100.0)

    @staticmethod
    def normalize_angle(angle):
        """
        Normalize an angle to the range [-180, +180].
        Essential for proper wraparound math.
        """
        while angle > 180.0:
            angle -= 360.0
        while angle < -180.0:
            angle += 360.0
        return angle

    @staticmethod
    def clamp(value, min_val, max_val):
        return max(min_val, min(max_val, value))

    def set_state(self, state_name):
        """
        Set the behavior controller state.
        Valid states: IDLE, FORWARD, BACKWARD, TURN_LEFT_90, TURN_RIGHT_90, HEADING_HOLD
        """
        valid_states = {
            self.IDLE, self.FORWARD, self.BACKWARD,
            self.TURN_LEFT_90, self.TURN_RIGHT_90, self.HEADING_HOLD
        }
        
        if state_name not in valid_states:
            return

        self.state = state_name
        self.last_error = 0.0
        
        # Reset PIDs on state change
        self.yaw_pid.reset()
        self.speed_pid.reset()

        with self.data_lock:
            self.current_yaw = self.fusion.get_data()["fused_yaw"]

        if self.state == self.IDLE:
            # Enforce zero output
            self.car.set_speed(0.0)
            self.car.set_steering(0.0)
            self.car.stop()
            
        elif self.state == self.HEADING_HOLD:
            # Capture current yaw as the target to maintain
            self.target_yaw = self.current_yaw

        elif self.state == self.TURN_LEFT_90:
            # Target is 90 degrees left (negative delta)
            self.target_yaw = self.normalize_angle(self.current_yaw - 90.0)
            
        elif self.state == self.TURN_RIGHT_90:
            # Target is 90 degrees right (positive delta)
            self.target_yaw = self.normalize_angle(self.current_yaw + 90.0)

        elif self.state == self.FORWARD:
            # Set target speed for forward motion
            self.target_speed = self.user_speed

        elif self.state == self.BACKWARD:
            # Set target speed for backward motion (negative)
            self.target_speed = -self.user_speed

    def update(self):
        """
        Update loop logic, intended to be called at ~20Hz.
        """
        with self.data_lock:
            self.current_yaw = self.fusion.get_data()["fused_yaw"]

        if self.state == self.IDLE:
            # Enforce neutral strictly every cycle to prevent drift
            self.car.set_speed(0.0)
            self.car.set_steering(0.0)

        elif self.state == self.FORWARD:
            # Compute speed error and apply PID
            error = self.target_speed - self.fusion.get_data()["fused_speed"]
            motor = self.speed_pid.compute(error, dt=0.05)
            # Apply deadband
            if abs(error) <= self.SPEED_TOLERANCE:
                motor = 0.0
            self.car.set_speed(motor)
            self.car.set_steering(0.0)
            return
        elif self.state == self.BACKWARD:
            # Compute speed error and apply PID for backward motion
            error = self.target_speed - self.fusion.get_data()["fused_speed"]
            motor = self.speed_pid.compute(error, dt=0.05)
            if abs(error) <= self.SPEED_TOLERANCE:
                motor = 0.0
            self.car.set_speed(motor)
            self.car.set_steering(0.0)
            return
        elif self.state == self.HEADING_HOLD:
            self._execute_heading_hold()

        elif self.state in (self.TURN_LEFT_90, self.TURN_RIGHT_90):
            self._execute_turn()

    def _execute_heading_hold(self):
        """
        Continuously adjusts steering to maintain target_yaw.
        Drives forward at user_speed.
        """
        error = self.normalize_angle(self.target_yaw - self.current_yaw)
        self.last_error = error

        steering = self.yaw_pid.compute(error, dt=0.05)
        
        if self.INVERT_STEERING:
            steering = -steering

        self.car.set_steering(steering)
        self.car.set_speed(self.user_speed)

    def _execute_turn(self):
        """
        PID rotation maneuver.
        """
        error = self.normalize_angle(self.target_yaw - self.current_yaw)
        self.last_error = error

        if abs(error) <= self.TOLERANCE:
            # Target reached!
            self.car.set_speed(0.0)
            self.car.set_steering(0.0)
            self.car.stop()
            self.state = self.IDLE
            self.last_error = 0.0
            self.yaw_pid.reset()
            self.speed_pid.reset()
            print("[TURN] ✅ Target reached. Motor=0, Steering=CENTER, State=IDLE")
            return

        # PID steering logic
        steering = self.yaw_pid.compute(error, dt=0.05)
        
        # Invert steering if mechanically mounted opposite
        if self.INVERT_STEERING:
            steering = -steering

        # Controlled rotation speed (slow down as we get closer)
        if abs(error) < 20.0:
            speed = self.ROTATION_SPEED * (abs(error) / 20.0)
        else:
            speed = self.ROTATION_SPEED

        # Set final outputs
        self.car.set_steering(steering)
        self.car.set_speed(speed)

        # Debug print
        print(f"[TURN] yaw={self.current_yaw:.1f}° target={self.target_yaw:.1f}° error={error:.1f}° steer={steering:.2f} speed={speed:.1f}")

    def get_data(self):
        return {
            "controller_state": self.state,
            "target_yaw": round(self.target_yaw, 2),
            "current_yaw": round(self.current_yaw, 2),
            "error": round(self.last_error, 2)
        }
