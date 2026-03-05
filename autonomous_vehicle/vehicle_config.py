"""
vehicle_config.py
Central configuration for all physical vehicle parameters.
Change values here to tune the entire system.
"""
import math

# ─── Car Physical Dimensions ─────────────────────────────────────────────────
CAR_LENGTH_M  = 0.27     # 27 cm
CAR_WIDTH_M   = 0.16     # 16 cm
WHEELBASE_M   = 0.18     # 18 cm   (front to rear axle)
TRACK_WIDTH_M = 0.16     # 16 cm   (left to right wheel centre)

WHEEL_DIAMETER_M = 0.05             # 5 cm
WHEEL_RADIUS_M   = WHEEL_DIAMETER_M / 2.0
WHEEL_CIRCUMFERENCE_M = math.pi * WHEEL_DIAMETER_M  # ≈ 0.1571 m

# ─── Steering Limits ─────────────────────────────────────────────────────────
MAX_STEERING_ANGLE_DEG = 30.0       # Physical max left/right lock
MAX_STEERING_ANGLE_RAD = math.radians(MAX_STEERING_ANGLE_DEG)

# ─── Servo Pulse Widths (pigpio, microseconds) ────────────────────────────────
SERVO_PIN       = 17
SERVO_MAX_LEFT  = 680
SERVO_CENTER    = 1060
SERVO_MAX_RIGHT = 1460

# ─── Motor Driver ────────────────────────────────────────────────────────────
MOTOR_R_EN = 23
MOTOR_L_EN = 24
MOTOR_RPWM = 13    # Forward
MOTOR_LPWM = 12    # Backward
MOTOR_PWM_FREQ = 1000    # Hz

# ─── Hardware I²C addresses ──────────────────────────────────────────────────
MPU6500_ADDRESS   = 0x68
QMC5883L_ADDRESS  = 0x0D

# ─── GPS Serial Port ─────────────────────────────────────────────────────────
GPS_SERIAL_PORT  = "/dev/serial0"
GPS_BAUDRATE     = 9600

# ─── Control Loop ────────────────────────────────────────────────────────────
CONTROL_LOOP_HZ     = 50          # Main brain loop frequency
SENSOR_LOOP_HZ      = 100         # Raw sensor read frequency
DASHBOARD_PUSH_HZ   = 10          # WebSocket push to browser

# ─── Navigation ──────────────────────────────────────────────────────────────
PURE_PURSUIT_LOOKAHEAD_M = 0.5    # 50 cm lookahead
WAYPOINT_REACHED_M       = 0.30   # Waypoint considered reached within 30 cm

# ─── PID Steering ────────────────────────────────────────────────────────────
PID_KP = 2.5
PID_KI = 0.05
PID_KD = 0.8

# ─── Speed Control ───────────────────────────────────────────────────────────
BASE_SPEED_PCT   = 50.0    # Motor PWM % at straight
MIN_SPEED_PCT    = 20.0    # Never go below this while navigating
MAX_SPEED_PCT    = 80.0

# ─── Movement Detection ──────────────────────────────────────────────────────
STATIONARY_ACCEL_THRESHOLD = 0.15  # m/s² deviation from 1g
STATIONARY_GPS_SPEED_KMH   = 0.5   # km/h below which we consider stationary

# ─── Web Dashboard ───────────────────────────────────────────────────────────
DASHBOARD_HOST = "0.0.0.0"
DASHBOARD_PORT = 5001
