"""
behavior_controller.py — Advanced Robotics Behavior Controller
Professional behavior controller for the Jager autonomous vehicle.

Control Context:
    - IMU provides yaw (-180 to +180 degrees)
    - SensorFusion provides fused_yaw and speed
    - car.set_speed() controls motor (-100 to 100)
    - car.set_steering() controls steering (-1 to +1, 0.0 is center)

Features:
    - Servo center offset calibration (corrects mechanical bias)
    - Dual-loop PID: Yaw PID (steering) + Speed PID (motor)
    - Separate rotation speed control (independent of drive slider)
    - 3-tier rotation speed scaling for smooth turns
    - Speed ramping (no jerk / sudden acceleration)
    - IR obstacle safety override (always has priority)
    - Anti-windup, derivative filtering, deadband
    - Thread-safe via data_lock
"""
import time
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
    TOLERANCE = 2.0                # Degrees error to consider turn complete
    SPEED_TOLERANCE = 0.3          # m/s deadband for speed PID
    INVERT_STEERING = True         # True if mechanical steering is inverted

    # Servo center offset — corrects mechanical bias
    # Positive = nudge right, Negative = nudge left. Tune on real hardware.
    SERVO_CENTER_OFFSET = 0.05

    # Rotation speed (independent of drive slider)
    TURN_SPEED_MAX = 18            # Max rotation motor power %
    TURN_SPEED_MID = 12            # Medium (10–30° error)
    TURN_SPEED_MIN = 6             # Fine (< 10° error)

    # Speed ramping — max change per 50ms cycle
    RAMP_MAX_DELTA = 5.0

    # Obstacle safety threshold (cm)
    OBSTACLE_STOP_CM = 20.0

    # Turn completion hold time (seconds) — hold neutral before switching to IDLE
    TURN_HOLD_TIME = 0.2

    def __init__(self, car, fusion, data_lock, ir_sensor=None):
        """
        Initialize the behavior controller.

        Args:
            car:        CarController instance
            fusion:     SensorFusion instance
            data_lock:  threading.Lock for shared sensor data
            ir_sensor:  IRSensor instance (optional, enables obstacle safety)
        """
        self.car = car
        self.fusion = fusion
        self.data_lock = data_lock
        self.ir_sensor = ir_sensor

        # Internal state
        self.state = self.IDLE
        self.user_speed = 50            # Drive slider speed (FORWARD/BACKWARD)
        self.target_yaw = 0.0           # Target yaw for turns / heading hold
        self.target_speed = 0.0         # Target speed for speed PID
        self.current_yaw = 0.0
        self.last_error = 0.0

        # Speed ramping state
        self.current_motor_output = 0.0

        # Turn hold state (brief pause at target before IDLE)
        self._turn_hold_start = None

        # Safety state
        self.obstacle_triggered = False

        # ── PID Controllers ──────────────────────────────────────────────
        # Yaw PID (steering): tuned for precise heading control
        self.yaw_pid = PIDController(
            Kp=0.025, Ki=0.0008, Kd=0.015,
            min_out=-1.0, max_out=1.0
        )

        # Speed PID (motor): tuned for smooth velocity control
        self.speed_pid = PIDController(
            Kp=2.0, Ki=0.5, Kd=0.1,
            min_out=-100.0, max_out=100.0
        )

    # ── Utilities ────────────────────────────────────────────────────────

    @staticmethod
    def normalize_angle(angle):
        """Normalize an angle to the range [-180, +180]."""
        while angle > 180.0:
            angle -= 360.0
        while angle < -180.0:
            angle += 360.0
        return angle

    @staticmethod
    def clamp(value, min_val, max_val):
        return max(min_val, min(max_val, value))

    def _apply_steering(self, steering):
        """
        Apply steering with center offset and clamping.
        Handles inversion and servo bias correction.
        """
        if self.INVERT_STEERING:
            steering = -steering

        # Apply center offset to correct mechanical bias
        steering += self.SERVO_CENTER_OFFSET

        # Clamp to valid range
        steering = self.clamp(steering, -1.0, 1.0)
        self.car.set_steering(steering)

    def _apply_speed_ramped(self, target):
        """
        Apply motor speed with ramp limiting to prevent jerk.
        Limits change to RAMP_MAX_DELTA per cycle.
        """
        delta = target - self.current_motor_output
        delta = self.clamp(delta, -self.RAMP_MAX_DELTA, self.RAMP_MAX_DELTA)
        self.current_motor_output += delta
        self.current_motor_output = self.clamp(self.current_motor_output, -100.0, 100.0)
        self.car.set_speed(self.current_motor_output)

    def _get_rotation_speed(self, error_deg):
        """
        3-tier rotation speed based on angular error.
        Slows down as we approach the target for precision.
        """
        abs_err = abs(error_deg)
        if abs_err > 30.0:
            return self.TURN_SPEED_MAX      # 18%
        elif abs_err > 10.0:
            return self.TURN_SPEED_MID      # 12%
        else:
            return self.TURN_SPEED_MIN      # 6%

    # ── Safety ───────────────────────────────────────────────────────────

    def _check_obstacle(self):
        """
        Safety override: check IR sensor for obstacles.
        Returns True if obstacle detected and vehicle was stopped.
        ALWAYS takes priority over all other states.
        """
        if self.ir_sensor is None:
            self.obstacle_triggered = False
            return False

        ir_data = self.ir_sensor.get_data()
        if ir_data["is_obstacle"]:
            # IMMEDIATE STOP — overrides everything
            self.car.set_speed(0.0)
            self._apply_steering(0.0)
            self.car.stop()
            self.current_motor_output = 0.0
            self.state = self.IDLE
            self.obstacle_triggered = True
            self.yaw_pid.reset()
            self.speed_pid.reset()
            self._turn_hold_start = None
            print(f"[SAFETY] 🛑 OBSTACLE at {ir_data['distance_cm']:.1f}cm — EMERGENCY STOP")
            return True

        self.obstacle_triggered = False
        return False

    # ── State Management ─────────────────────────────────────────────────

    def set_state(self, state_name):
        """
        Set the behavior controller state.
        Valid: IDLE, FORWARD, BACKWARD, TURN_LEFT_90, TURN_RIGHT_90, HEADING_HOLD
        """
        valid_states = {
            self.IDLE, self.FORWARD, self.BACKWARD,
            self.TURN_LEFT_90, self.TURN_RIGHT_90, self.HEADING_HOLD
        }

        if state_name not in valid_states:
            return

        self.state = state_name
        self.last_error = 0.0
        self._turn_hold_start = None

        # Reset PIDs on state change
        self.yaw_pid.reset()
        self.speed_pid.reset()

        with self.data_lock:
            self.current_yaw = self.fusion.get_data()["fused_yaw"]

        if self.state == self.IDLE:
            self.car.set_speed(0.0)
            self._apply_steering(0.0)
            self.car.stop()
            self.current_motor_output = 0.0

        elif self.state == self.HEADING_HOLD:
            self.target_yaw = self.current_yaw

        elif self.state == self.TURN_LEFT_90:
            self.target_yaw = self.normalize_angle(self.current_yaw - 90.0)

        elif self.state == self.TURN_RIGHT_90:
            self.target_yaw = self.normalize_angle(self.current_yaw + 90.0)

        elif self.state == self.FORWARD:
            self.target_speed = self.user_speed

        elif self.state == self.BACKWARD:
            self.target_speed = -self.user_speed

    # ── Main Update Loop ─────────────────────────────────────────────────

    def update(self):
        """
        Update loop, called at ~20Hz.

        Execution order (professional robotics pattern):
        1. Read sensors
        2. Safety override check
        3. State logic + PID
        4. Speed ramping
        5. Actuator commands
        """
        # ── Step 1: Read fused sensors ──
        with self.data_lock:
            fused = self.fusion.get_data()
            self.current_yaw = fused["fused_yaw"]

        # ── Step 2: SAFETY OVERRIDE (always first!) ──
        if self._check_obstacle():
            return  # Vehicle stopped, nothing else executes

        # ── Step 3: State logic ──
        if self.state == self.IDLE:
            self._apply_speed_ramped(0.0)
            self._apply_steering(0.0)

        elif self.state == self.FORWARD:
            self._execute_drive(self.target_speed, fused["fused_speed"])

        elif self.state == self.BACKWARD:
            self._execute_drive(self.target_speed, fused["fused_speed"])

        elif self.state == self.HEADING_HOLD:
            self._execute_heading_hold()

        elif self.state in (self.TURN_LEFT_90, self.TURN_RIGHT_90):
            self._execute_turn()

    # ── State Executors ──────────────────────────────────────────────────

    def _execute_drive(self, target_speed, current_speed):
        """Forward/Backward with speed PID and ramp limiter."""
        error = target_speed - current_speed
        motor = self.speed_pid.compute(error, dt=0.05)

        # Deadband — don't fight noise near target
        if abs(error) <= self.SPEED_TOLERANCE:
            motor = target_speed  # Hold steady

        self._apply_speed_ramped(motor)
        self._apply_steering(0.0)

    def _execute_heading_hold(self):
        """Maintain target_yaw with yaw PID while driving forward."""
        error = self.normalize_angle(self.target_yaw - self.current_yaw)
        self.last_error = error

        steering = self.yaw_pid.compute(error, dt=0.05)
        self._apply_steering(steering)
        self._apply_speed_ramped(self.user_speed)

    def _execute_turn(self):
        """
        PID rotation maneuver with 3-tier speed, ramping, and hold delay.
        """
        error = self.normalize_angle(self.target_yaw - self.current_yaw)
        self.last_error = error

        # ── Check if target reached ──
        if abs(error) <= self.TOLERANCE:
            # Phase 1: Hold neutral for TURN_HOLD_TIME before going IDLE
            if self._turn_hold_start is None:
                self._turn_hold_start = time.time()
                self._apply_speed_ramped(0.0)
                self._apply_steering(0.0)
                print("[TURN] ✅ Target reached — holding neutral...")
                return

            # Phase 2: Check if hold time has elapsed
            elapsed = time.time() - self._turn_hold_start
            if elapsed >= self.TURN_HOLD_TIME:
                self.car.set_speed(0.0)
                self._apply_steering(0.0)
                self.car.stop()
                self.current_motor_output = 0.0
                self.state = self.IDLE
                self.last_error = 0.0
                self._turn_hold_start = None
                self.yaw_pid.reset()
                self.speed_pid.reset()
                print("[TURN] ✅ Turn complete. State → IDLE")
                return

            # Still holding — keep neutral
            self._apply_speed_ramped(0.0)
            self._apply_steering(0.0)
            return

        # Reset hold timer if we drift back out of tolerance
        self._turn_hold_start = None

        # ── PID steering ──
        steering = self.yaw_pid.compute(error, dt=0.05)
        self._apply_steering(steering)

        # ── 3-tier rotation speed ──
        speed = self._get_rotation_speed(error)
        self._apply_speed_ramped(speed)

        # Debug
        print(
            f"[TURN] yaw={self.current_yaw:.1f}° target={self.target_yaw:.1f}° "
            f"error={error:.1f}° steer={steering:.2f} speed={speed:.0f}"
        )

    # ── Data Export ──────────────────────────────────────────────────────

    def get_data(self):
        return {
            "controller_state": self.state,
            "target_yaw": round(self.target_yaw, 2),
            "current_yaw": round(self.current_yaw, 2),
            "error": round(self.last_error, 2),
            "motor_output": round(self.current_motor_output, 1),
            "obstacle_triggered": self.obstacle_triggered
        }
