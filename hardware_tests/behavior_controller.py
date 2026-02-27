"""
behavior_controller.py — Robotics Behavior Controller
Pure rotation turn controller for the Jager autonomous vehicle.

Control Philosophy:
    - TURN_RELATIVE is a PURE ROTATION maneuver, not drive-and-steer.
    - Motor provides minimal rotational torque only (not forward speed).
    - Steering goes full lock in the turn direction.
    - On completion: motor = 0, steering = 0 (center), state = IDLE.

States:
    IDLE          — stopped, no output
    FORWARD       — straight ahead at user speed
    BACKWARD      — reverse at user speed
    TURN_RELATIVE — closed-loop pure rotation to target yaw

Author: Jager Robotics Stack
"""


class BehaviorController:
    """
    High-level behavior controller for the autonomous vehicle.

    Uses fused yaw from SensorFusion to execute precise relative-angle
    turns as pure rotation maneuvers. The vehicle rotates in place
    (or near-zero drift) using bang-bang steering with minimal motor power.
    """

    # ── State Constants ──────────────────────────────────────────────────
    IDLE = "IDLE"
    FORWARD = "FORWARD"
    BACKWARD = "BACKWARD"
    TURN_RELATIVE = "TURN_RELATIVE"

    # ── Tuning Constants ─────────────────────────────────────────────────

    # Angle tolerance in degrees. Turn completes when |error| <= this.
    TOLERANCE = 3.0

    # Motor power (0–100) used ONLY for rotation. This is NOT forward speed.
    # Just enough torque to rotate the vehicle. Keep low to prevent drift.
    ROTATION_SPEED = 20

    def __init__(self, car, fusion, data_lock):
        """
        Initialize the behavior controller.

        Args:
            car:       Car control object with set_speed(), set_steering(), stop()
            fusion:    SensorFusion instance providing fused_yaw
            data_lock: threading.Lock for thread-safe access to fusion data
        """
        self.car = car
        self.fusion = fusion
        self.data_lock = data_lock

        # ── Internal State ───────────────────────────────────────────────
        self.state = self.IDLE
        self.user_speed = 50        # Speed for FORWARD/BACKWARD (0–100)
        self.target_yaw = 0.0       # Target yaw for TURN_RELATIVE
        self.current_yaw = 0.0      # Latest fused yaw reading
        self.last_error = 0.0       # Latest yaw error (for telemetry)

    # ── Math Utilities ───────────────────────────────────────────────────

    @staticmethod
    def normalize_angle(angle):
        """
        Normalize an angle to the range [-180, +180].

        Critical for handling the -180/+180 wraparound boundary.
        Without this, a target of 260° would never be reached
        because the IMU reports in [-180, +180].

        Args:
            angle: Raw angle in degrees (any value)

        Returns:
            Normalized angle in [-180, +180]
        """
        while angle > 180.0:
            angle -= 360.0
        while angle < -180.0:
            angle += 360.0
        return angle

    # ── State Control ────────────────────────────────────────────────────

    def set_state(self, state_name):
        """
        Set the controller state.

        Valid states: IDLE, FORWARD, BACKWARD.
        For TURN_RELATIVE, use set_relative_turn() instead.

        Args:
            state_name: One of the state constants (string)
        """
        valid = {self.IDLE, self.FORWARD, self.BACKWARD}
        if state_name in valid:
            self.state = state_name
            self.last_error = 0.0

            # When entering IDLE: full stop + center steering
            if state_name == self.IDLE:
                self.car.set_speed(0.0)
                self.car.set_steering(0.0)
                self.car.stop()

    def set_relative_turn(self, delta_angle):
        """
        Begin a pure rotation turn by delta_angle degrees.

        Computes target yaw from current fused heading + delta.
        Switches to TURN_RELATIVE state. The update() loop handles
        the closed-loop rotation until the target is reached.

        Args:
            delta_angle: Degrees to turn (+ = right/clockwise,
                                          - = left/counter-clockwise)
        """
        # Read current heading (thread-safe)
        with self.data_lock:
            self.current_yaw = self.fusion.get_data()["fused_yaw"]

        # Compute normalized target
        self.target_yaw = self.normalize_angle(self.current_yaw + delta_angle)
        self.last_error = 0.0
        self.state = self.TURN_RELATIVE

    # ── Main Update Loop ─────────────────────────────────────────────────

    def update(self):
        """
        Execute one control cycle. Must be called at ~20Hz.

        Reads the latest fused yaw (thread-safe), then executes
        the behavior for the current state.
        """
        # ── Read fused yaw under lock ────────────────────────────────────
        with self.data_lock:
            self.current_yaw = self.fusion.get_data()["fused_yaw"]

        # ── State Machine ────────────────────────────────────────────────

        if self.state == self.IDLE:
            # No output — car should already be stopped
            pass

        elif self.state == self.FORWARD:
            # Straight ahead at user-set speed
            self.car.set_speed(self.user_speed)
            self.car.set_steering(0.0)

        elif self.state == self.BACKWARD:
            # Reverse at user-set speed
            self.car.set_speed(-self.user_speed)
            self.car.set_steering(0.0)

        elif self.state == self.TURN_RELATIVE:
            self._execute_pure_rotation()

    def _execute_pure_rotation(self):
        """
        Pure rotation maneuver for TURN_RELATIVE state.

        This is NOT drive-and-steer. The vehicle rotates in place:
            1. Steering goes full lock in the error direction.
            2. Motor provides minimal rotational torque only.
            3. When target reached: motor = 0, steering = center, state = IDLE.

        The bang-bang steering (full left or full right) ensures the
        fastest rotation. The low ROTATION_SPEED prevents forward drift.
        """
        # ── Compute normalized yaw error ─────────────────────────────────
        error = self.normalize_angle(self.target_yaw - self.current_yaw)
        self.last_error = error

        # ── Target reached → full stop ───────────────────────────────────
        if abs(error) <= self.TOLERANCE:
            # CRITICAL: Stop motor AND center steering
            self.car.set_speed(0.0)
            self.car.set_steering(0.0)
            self.car.stop()
            self.state = self.IDLE
            self.last_error = 0.0
            return

        # ── Pure rotation: bang-bang steering + minimal motor ─────────────
        # Positive error → need to rotate right → steering = +1.0
        # Negative error → need to rotate left  → steering = -1.0
        if error > 0:
            steering = 1.0    # Full right lock
        else:
            steering = -1.0   # Full left lock

        # Apply: full steering lock + minimal rotational motor power
        self.car.set_steering(steering)
        self.car.set_speed(self.ROTATION_SPEED)

    # ── Telemetry ────────────────────────────────────────────────────────

    def get_data(self):
        """
        Return current controller state for the Flask API / UI.

        Returns:
            dict with state, target_yaw, current_yaw, error
        """
        return {
            "controller_state": self.state,
            "target_yaw": round(self.target_yaw, 2),
            "current_yaw": round(self.current_yaw, 2),
            "error": round(self.last_error, 2)
        }
