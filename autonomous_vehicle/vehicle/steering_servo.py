"""
steering_servo.py
Steering servo driver using pigpio pulse-width control.
Pin: GPIO 17
Limits: MAX_LEFT=680 µs, CENTER=1060 µs, MAX_RIGHT=1460 µs
Max physical steering: ±30°
"""
import math
import threading

try:
    import pigpio
    PIGPIO_AVAILABLE = True
except ImportError:
    PIGPIO_AVAILABLE = False

from vehicle_config import (SERVO_PIN, SERVO_MAX_LEFT, SERVO_CENTER,
                            SERVO_MAX_RIGHT, MAX_STEERING_ANGLE_DEG)


class SteeringServo:
    def __init__(self, pi=None):
        self._mock = not PIGPIO_AVAILABLE
        self._lock = threading.Lock()
        self.current_pulse  = SERVO_CENTER
        self.current_angle_deg = 0.0

        if not self._mock:
            self.pi = pi or pigpio.pi()
            if not self.pi.connected:
                print("[Servo] pigpio daemon not running — mock mode")
                self._mock = True
            else:
                print(f"[Servo] Initialised on GPIO {SERVO_PIN}")
                self.center()
        else:
            self.pi = None
            print("[Servo] pigpio not found — mock mode")

    # ── Pulse control ─────────────────────────────────────────────────────────
    def set_pulse(self, pulse):
        pulse = int(max(SERVO_MAX_LEFT, min(SERVO_MAX_RIGHT, pulse)))
        with self._lock:
            self.current_pulse = pulse
            # Back-compute angle for telemetry
            frac = (pulse - SERVO_CENTER) / (SERVO_MAX_RIGHT - SERVO_CENTER)
            self.current_angle_deg = frac * MAX_STEERING_ANGLE_DEG
            if not self._mock:
                self.pi.set_servo_pulsewidth(SERVO_PIN, pulse)

    # ── Angle control (±30°) ──────────────────────────────────────────────────
    def set_angle(self, angle_deg):
        """
        angle_deg: -30 (full left) to +30 (full right). 0 = straight.
        Linearly maps to pulse range.
        """
        angle_deg = max(-MAX_STEERING_ANGLE_DEG,
                        min( MAX_STEERING_ANGLE_DEG, float(angle_deg)))

        if angle_deg >= 0:
            span  = SERVO_MAX_RIGHT - SERVO_CENTER
            frac  = angle_deg / MAX_STEERING_ANGLE_DEG
            pulse = int(SERVO_CENTER + frac * span)
        else:
            span  = SERVO_CENTER - SERVO_MAX_LEFT
            frac  = -angle_deg / MAX_STEERING_ANGLE_DEG
            pulse = int(SERVO_CENTER - frac * span)

        self.set_pulse(pulse)

    # ── Convenience shortcuts ─────────────────────────────────────────────────
    def center(self):
        self.set_pulse(SERVO_CENTER)

    def max_left(self):
        self.set_pulse(SERVO_MAX_LEFT)

    def max_right(self):
        self.set_pulse(SERVO_MAX_RIGHT)

    # ── Getters ───────────────────────────────────────────────────────────────
    def get_angle_deg(self):
        return self.current_angle_deg

    def get_pulse(self):
        return self.current_pulse

    # ── Cleanup ───────────────────────────────────────────────────────────────
    def cleanup(self):
        self.center()
        if not self._mock and self.pi:
            self.pi.set_servo_pulsewidth(SERVO_PIN, 0)
        print("[Servo] Cleaned up")
