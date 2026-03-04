"""
steering_servo.py
Stable servo controller for Raspberry Pi
"""
import time
import threading

try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    print("[Servo] RPi.GPIO not found. Running in mock mode.")


class SteeringServo:

    SERVO_PIN = 18

    def __init__(self):
        self._mock = not GPIO_AVAILABLE
        self.current_angle = 90
        self._lock = threading.Lock()

        if not self._mock:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            GPIO.setup(self.SERVO_PIN, GPIO.OUT)
            self.pwm = GPIO.PWM(self.SERVO_PIN, 50)
            self.pwm.start(0)
            print("[Servo] Initialized on GPIO18")

        self.center()

    def _write_angle(self, angle):
        if self._mock: return
        
        duty = 2 + (angle / 18)
        GPIO.output(self.SERVO_PIN, True)
        self.pwm.ChangeDutyCycle(duty)
        time.sleep(0.4)
        GPIO.output(self.SERVO_PIN, False)
        self.pwm.ChangeDutyCycle(0)

    def set_angle(self, angle):
        angle = max(0, min(180, float(angle)))

        with self._lock:
            self.current_angle = angle
            print(f"[Servo] Moving to {angle}°")
            self._write_angle(angle)

    def center(self):
        self.set_angle(90)

    def steer_left(self):
        self.set_angle(60)

    def steer_right(self):
        self.set_angle(120)

    def cleanup(self):
        print("[Servo] Cleanup")
        if not self._mock:
            self.pwm.stop()
            GPIO.cleanup(self.SERVO_PIN)
