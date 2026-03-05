"""
steering_servo.py — Stable servo controller using pigpio

Ported from project/motors/steering_servo.py (confirmed working).
Pin:    GPIO 17
Limits: MAX_LEFT=680 µs | CENTER=1060 µs | MAX_RIGHT=1460 µs
STEP + DELAY: smooth incremental movement (no snap jitter)
"""
import time
import threading

try:
    import pigpio
    PIGPIO_AVAILABLE = True
except ImportError:
    PIGPIO_AVAILABLE = False
    print("[Servo] pigpio not found. Running in mock mode.")


class SteeringServo:

    # ── Constants (match confirmed hardware calibration) ──────────────────────
    SERVO_PIN = 17
    MAX_LEFT  = 680
    CENTER    = 1060
    MAX_RIGHT = 1460

    STEP  = 10      # µs per step for smooth move
    DELAY = 0.02    # seconds between steps

    # Physical steering: ±30°
    MAX_ANGLE_DEG = 30.0

    def __init__(self, pi=None):
        self._mock = not PIGPIO_AVAILABLE
        self.current_pulse = self.CENTER
        self._lock = threading.Lock()

        if not self._mock:
            self.pi = pi if pi is not None else pigpio.pi()
            if not self.pi.connected:
                print("[Servo] ERROR: pigpio daemon not running (sudo pigpiod). Mock mode.")
                self._mock = True
            else:
                print(f"[Servo] Initialised on GPIO {self.SERVO_PIN} via pigpio")
                self.center()
        else:
            self.pi = None

    # ── Instant pulse ─────────────────────────────────────────────────────────
    def set_pulse(self, target_pulse):
        """Immediately moves servo to the given pulse width (µs)."""
        target_pulse = max(self.MAX_LEFT, min(self.MAX_RIGHT, int(target_pulse)))
        with self._lock:
            self.current_pulse = target_pulse
            if not self._mock:
                self.pi.set_servo_pulsewidth(self.SERVO_PIN, target_pulse)
        print(f"[Servo] Pulse → {target_pulse} µs")

    # ── Smooth pulse ──────────────────────────────────────────────────────────
    def smooth_move_to(self, target_pulse):
        """Gradually steps to target_pulse to avoid snap/jitter."""
        target_pulse = max(self.MAX_LEFT, min(self.MAX_RIGHT, int(target_pulse)))
        with self._lock:
            step = self.STEP if target_pulse > self.current_pulse else -self.STEP
            if not self._mock:
                for pulse in range(self.current_pulse, target_pulse, step):
                    self.pi.set_servo_pulsewidth(self.SERVO_PIN, pulse)
                    time.sleep(self.DELAY)
                self.pi.set_servo_pulsewidth(self.SERVO_PIN, target_pulse)
            self.current_pulse = target_pulse
        print(f"[Servo] Reached → {target_pulse} µs")

    # ── Angle interface (−30° to +30°) ────────────────────────────────────────
    def set_angle(self, angle_deg):
        """
        angle_deg: −30 (full left) → 0 (centre) → +30 (full right).
        Maps linearly to 680–1060–1460 µs.
        """
        angle_deg = max(-self.MAX_ANGLE_DEG, min(self.MAX_ANGLE_DEG, float(angle_deg)))
        if angle_deg >= 0:
            span  = self.MAX_RIGHT - self.CENTER
            pulse = int(self.CENTER + (angle_deg / self.MAX_ANGLE_DEG) * span)
        else:
            span  = self.CENTER - self.MAX_LEFT
            pulse = int(self.CENTER + (angle_deg / self.MAX_ANGLE_DEG) * span)
        self.set_pulse(pulse)

    # ── Joystick interface (−1.0 to +1.0) ────────────────────────────────────
    def set_normalised(self, val):
        """
        val: −1.0 (full left) → 0.0 (centre) → +1.0 (full right).
        Used by the web joystick /api/control endpoint.
        """
        val = max(-1.0, min(1.0, float(val)))
        if val >= 0:
            pulse = int(self.CENTER + val * (self.MAX_RIGHT - self.CENTER))
        else:
            pulse = int(self.CENTER + val * (self.CENTER - self.MAX_LEFT))
        self.set_pulse(pulse)

    # ── Convenience ───────────────────────────────────────────────────────────
    def center(self):        self.set_pulse(self.CENTER)
    def steer_left(self):    self.set_pulse(self.MAX_LEFT)
    def steer_right(self):   self.set_pulse(self.MAX_RIGHT)

    def get_pulse(self):     return self.current_pulse
    def get_angle_deg(self):
        frac = (self.current_pulse - self.CENTER) / (self.MAX_RIGHT - self.CENTER)
        return frac * self.MAX_ANGLE_DEG

    # ── Cleanup ───────────────────────────────────────────────────────────────
    def cleanup(self):
        self.center()
        if not self._mock and self.pi:
            self.pi.set_servo_pulsewidth(self.SERVO_PIN, 0)
            self.pi.stop()
        print("[Servo] Cleaned up")
