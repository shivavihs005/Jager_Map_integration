"""
motor_controller.py — Controls the DC drive motor using RPi.GPIO and BTS7960

Ported from project/motors/motor_controller.py (confirmed working).
Pins (from vehicle_config.py):
    RPWM  → GPIO 13  (Forward)
    LPWM  → GPIO 12  (Backward)
    R_EN  → GPIO 23
    L_EN  → GPIO 24
"""
import time

try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    print("[Motors] RPi.GPIO not found. Running in mock mode.")
    GPIO_AVAILABLE = False

from vehicle_config import MOTOR_R_EN, MOTOR_L_EN, MOTOR_RPWM, MOTOR_LPWM


class MotorController:

    def __init__(self):
        self._mock = not GPIO_AVAILABLE

        if not self._mock:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)

            # Setup pins as outputs
            GPIO.setup([MOTOR_R_EN, MOTOR_L_EN, MOTOR_RPWM, MOTOR_LPWM], GPIO.OUT)

            # Enable BTS7960 bridges (HIGH = driver ON)
            GPIO.output(MOTOR_R_EN, GPIO.HIGH)
            GPIO.output(MOTOR_L_EN, GPIO.HIGH)

            # Hardware PWM at 1000 Hz on direction pins
            self.pwm_fwd = GPIO.PWM(MOTOR_RPWM, 1000)
            self.pwm_bwd = GPIO.PWM(MOTOR_LPWM, 1000)

            self.pwm_fwd.start(0)
            self.pwm_bwd.start(0)
            print(f"[Motors] BTS7960 initialised on pins RPWM={MOTOR_RPWM}, LPWM={MOTOR_LPWM}")
        else:
            print("[Motors] Mock mode active")

    # ── Drive commands ────────────────────────────────────────────────────────

    def move_forward(self, speed):
        """speed: 0–100 %"""
        if self._mock:
            print(f"[Motors MOCK] FWD {speed:.0f}%")
            return
        speed = max(0.0, min(100.0, float(speed)))
        self.pwm_bwd.ChangeDutyCycle(0)
        self.pwm_fwd.ChangeDutyCycle(speed)

    def move_backward(self, speed):
        """speed: 0–100 %"""
        if self._mock:
            print(f"[Motors MOCK] BWD {speed:.0f}%")
            return
        speed = max(0.0, min(100.0, float(speed)))
        self.pwm_fwd.ChangeDutyCycle(0)
        self.pwm_bwd.ChangeDutyCycle(speed)

    def set_speed(self, speed):
        """
        Unified speed interface: positive = forward, negative = backward.
        speed: -100 to 100
        """
        if speed > 0:
            self.move_forward(abs(speed))
        elif speed < 0:
            self.move_backward(abs(speed))
        else:
            self.stop()

    def stop(self):
        """Stop motor — zero both PWM signals."""
        if self._mock:
            print("[Motors MOCK] STOP")
            return
        self.pwm_fwd.ChangeDutyCycle(0)
        self.pwm_bwd.ChangeDutyCycle(0)

    # ── Cleanup ───────────────────────────────────────────────────────────────

    def cleanup(self):
        if not self._mock:
            self.stop()
            GPIO.output(MOTOR_R_EN, GPIO.LOW)
            GPIO.output(MOTOR_L_EN, GPIO.LOW)
            self.pwm_fwd.stop()
            self.pwm_bwd.stop()
            print("[Motors] Cleaned up")
