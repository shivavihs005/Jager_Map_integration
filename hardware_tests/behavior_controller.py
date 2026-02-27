"""
behavior_controller.py — Robotics Behavior Controller
Provides high-level driving behaviors (forward, backward, relative turns)
for the Jager autonomous vehicle using fused IMU yaw.

Control Architecture:
    - States: IDLE, FORWARD, BACKWARD, TURN_LEFT, TURN_RIGHT, TURN_RELATIVE
    - Relative turns use a proportional (P) controller on yaw error
    - All angles are normalized to [-180, +180] to handle wraparound
    - The update() method runs at 20Hz from the main application

Author: Jager Robotics Stack
"""


class BehaviorController:
    """
    High-level behavior controller for the autonomous vehicle.

    Uses fused yaw from SensorFusion (IMU-dominant when slow) to execute
    precise relative-angle turns with proportional steering control.
    Automatically stops when the target angle is reached within tolerance.
    """

    # ── State Constants ──────────────────────────────────────────────────
    IDLE = "IDLE"
    FORWARD = "FORWARD"
    BACKWARD = "BACKWARD"
    TURN_LEFT = "TURN_LEFT"
    TURN_RIGHT = "TURN_RIGHT"
    TURN_RELATIVE = "TURN_RELATIVE"

    # ── Tuning Constants ─────────────────────────────────────────────────
    # Proportional gain for yaw error → steering output.
    # Range: 0.01 (slow, smooth) to 0.02 (fast, aggressive).
    Kp = 0.015

    # Angle tolerance in degrees. Controller stops when |error| <= this.
    TOLERANCE = 3.0

    # Motor power (0–100) used during turns and slow maneuvers.
    LOW_FORWARD_SPEED = 25

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
        self.user_speed = 50        # Default speed (0–100), set by UI slider
        self.target_yaw = 0.0       # Target yaw for TURN_RELATIVE
        self.current_yaw = 0.0      # Latest fused yaw reading
        self.last_error = 0.0       # Latest yaw error (for telemetry)

    # ── Math Utilities ───────────────────────────────────────────────────

    @staticmethod
    def normalize_angle(angle):
        """
        Normalize an angle to the range [-180, +180].

        This is critical for handling the -180/+180 wraparound boundary.
        Without normalization, a target of 260° would never be reached
        because the IMU reports in [-180, +180].

        Args:
            angle: Raw angle in degrees (can be any value)

        Returns:
            Normalized angle in [-180, +180]
        """
        while angle > 180.0:
            angle -= 360.0
        while angle < -180.0:
            angle += 360.0
        return angle

    @staticmethod
    def calculate_relative_target(current_yaw, delta_angle):
        """
        Compute a new target yaw by adding a delta to the current heading.

        Example:
            current_yaw = 170°, delta = +90°
            raw target  = 260°
            normalized  = -100°  (correct wraparound)

        Args:
            current_yaw:  Current fused yaw in degrees
            delta_angle:  Relative turn amount (+ = right, - = left)

        Returns:
            Normalized target yaw in [-180, +180]
        """
        target = current_yaw + delta_angle
        return BehaviorController.normalize_angle(target)

    @staticmethod
    def clamp(value, min_val, max_val):
        """Clamp a value to [min_val, max_val]."""
        return max(min_val, min(max_val, value))

    # ── State Control ────────────────────────────────────────────────────

    def set_state(self, state_name):
        """
        Set the controller state.

        Valid states: IDLE, FORWARD, BACKWARD, TURN_LEFT, TURN_RIGHT.
        For TURN_RELATIVE, use set_relative_turn() instead.

        Args:
            state_name: One of the state constants (string)
        """
        valid = {
            self.IDLE, self.FORWARD, self.BACKWARD,
            self.TURN_LEFT, self.TURN_RIGHT
        }
        if state_name in valid:
            self.state = state_name
            self.last_error = 0.0

            # When entering IDLE, immediately stop the car
            if state_name == self.IDLE:
                self.car.stop()

    def set_relative_turn(self, delta_angle):
        """
        Begin a relative yaw turn.

        Computes the target yaw from the current fused heading + delta,
        then switches state to TURN_RELATIVE. The update() loop will
        drive the car toward the target using proportional control.

        Args:
            delta_angle: Degrees to turn (+ = right/clockwise,
                                          - = left/counter-clockwise)
        """
        with self.data_lock:
            self.current_yaw = self.fusion.get_data()["fused_yaw"]

        self.target_yaw = self.calculate_relative_target(
            self.current_yaw, delta_angle
        )
        self.last_error = 0.0
        self.state = self.TURN_RELATIVE

    # ── Main Update Loop ─────────────────────────────────────────────────

    def update(self):
        """
        Execute one control cycle. Must be called at ~20Hz.

        Reads the latest fused yaw (thread-safe), then applies the
        behavior for the current state:

            IDLE       → car stopped, no output
            FORWARD    → straight ahead at user_speed
            BACKWARD   → reverse at user_speed
            TURN_LEFT  → low speed, full left steering
            TURN_RIGHT → low speed, full right steering
            TURN_RELATIVE → proportional yaw controller toward target
        """
        # ── Read fused yaw under lock ────────────────────────────────────
        with self.data_lock:
            self.current_yaw = self.fusion.get_data()["fused_yaw"]

        # ── State Machine ────────────────────────────────────────────────

        if self.state == self.IDLE:
            # Nothing to do — car should already be stopped
            pass

        elif self.state == self.FORWARD:
            self.car.set_speed(self.user_speed)
            self.car.set_steering(0.0)

        elif self.state == self.BACKWARD:
            self.car.set_speed(-self.user_speed)
            self.car.set_steering(0.0)

        elif self.state == self.TURN_LEFT:
            self.car.set_speed(self.LOW_FORWARD_SPEED)
            self.car.set_steering(-1.0)  # Full left

        elif self.state == self.TURN_RIGHT:
            self.car.set_speed(self.LOW_FORWARD_SPEED)
            self.car.set_steering(1.0)   # Full right

        elif self.state == self.TURN_RELATIVE:
            self._execute_relative_turn()

    def _execute_relative_turn(self):
        """
        Proportional controller for TURN_RELATIVE state.

        Computes normalized yaw error, then:
            - If |error| <= TOLERANCE: stop the car, return to IDLE.
            - Otherwise: apply proportional steering = clamp(error * Kp),
              drive forward at LOW_FORWARD_SPEED.

        The P-controller naturally reduces steering as the target is
        approached, preventing overshoot and oscillation.
        """
        # ── Compute normalized yaw error ─────────────────────────────────
        error = self.normalize_angle(self.target_yaw - self.current_yaw)
        self.last_error = error

        # ── Target reached — stop and go idle ────────────────────────────
        if abs(error) <= self.TOLERANCE:
            self.car.stop()
            self.state = self.IDLE
            self.last_error = 0.0
            return

        # ── Proportional steering ────────────────────────────────────────
        # Positive error → turn right (steering > 0)
        # Negative error → turn left  (steering < 0)
        steering = self.clamp(error * self.Kp, -1.0, 1.0)
        self.car.set_speed(self.LOW_FORWARD_SPEED)
        self.car.set_steering(steering)

    # ── Telemetry ────────────────────────────────────────────────────────

    def get_data(self):
        """
        Return current controller state for the Flask API / UI.

        Returns:
            dict with state, target_yaw, current_yaw, error, and Kp
        """
        return {
            "controller_state": self.state,
            "target_yaw": round(self.target_yaw, 2),
            "current_yaw": round(self.current_yaw, 2),
            "error": round(self.last_error, 2),
            "kp": self.Kp
        }
