"""
steering_servo.py
Stable servo controller for Raspberry Pi using pigpio
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

    # Pin & Pulse Configuration
    SERVO_PIN = 17
    MAX_LEFT = 680
    CENTER = 1060
    MAX_RIGHT = 1460
    
    STEP = 10
    DELAY = 0.02

    def __init__(self):
        self._mock = not PIGPIO_AVAILABLE
        self.current_pulse = self.CENTER
        self._lock = threading.Lock()

        if not self._mock:
            self.pi = pigpio.pi()
            if not self.pi.connected:
                print("[Servo] ERROR: Could not connect to pigpio daemon. Is it running (sudo pigpiod)?")
                self._mock = True
            else:
                print(f"[Servo] Initialized on GPIO {self.SERVO_PIN} via pigpio")
                self.center()
        else:
            self.pi = None

    def set_pulse(self, target_pulse):
        """Immediately sets the servo to a specific pulse width."""
        target_pulse = max(self.MAX_LEFT, min(self.MAX_RIGHT, int(target_pulse)))

        with self._lock:
            self.current_pulse = target_pulse
            print(f"[Servo] Moving to pulse {target_pulse}")
            if not self._mock:
                self.pi.set_servo_pulsewidth(self.SERVO_PIN, target_pulse)

    def set_angle(self, angle):
        """
        Legacy support: maps 0-180 degrees to 680-1460 pulse.
        0 = MAX_LEFT (680)
        90 = CENTER (1060)
        180 = MAX_RIGHT (1460)
        """
        # Map [0, 180] to [680, 1460]
        angle = max(0, min(180, float(angle)))
        pulse_range = self.MAX_RIGHT - self.MAX_LEFT
        target_pulse = int(self.MAX_LEFT + (angle / 180.0) * pulse_range)
        self.set_pulse(target_pulse)

    def smooth_move_to(self, target_pulse):
        """Gradually moves the servo to a target pulse width instead of snapping."""
        target_pulse = max(self.MAX_LEFT, min(self.MAX_RIGHT, int(target_pulse)))

        with self._lock:
            if target_pulse > self.current_pulse:
                step = self.STEP
            else:
                step = -self.STEP

            if not self._mock:
                for pulse in range(self.current_pulse, target_pulse, step):
                    self.pi.set_servo_pulsewidth(self.SERVO_PIN, pulse)
                    time.sleep(self.DELAY)
                
                self.pi.set_servo_pulsewidth(self.SERVO_PIN, target_pulse)
            self.current_pulse = target_pulse
            print(f"[Servo] Reached pulse {target_pulse}")

    def center(self):
        self.set_pulse(self.CENTER)

    def steer_left(self):
        self.set_pulse(self.MAX_LEFT)

    def steer_right(self):
        self.set_pulse(self.MAX_RIGHT)

    def cleanup(self):
        print("[Servo] Cleanup")
        if not self._mock and self.pi:
            self.pi.set_servo_pulsewidth(self.SERVO_PIN, 0)
            self.pi.stop()
