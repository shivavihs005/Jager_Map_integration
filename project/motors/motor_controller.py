"""
motor_controller.py — Controls the two DC motors
Uses the same PCA9685/GPIO fallback logic as the previous implementation.
"""
import time
try:
    from adafruit_pca9685 import PCA9685
    from board import SCL, SDA
    import busio
    PCA_AVAILABLE = True
except ImportError:
    print("[Motors] PCA9685 library not found. Running in mock mode.")
    PCA_AVAILABLE = False

try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    print("[Motors] RPi.GPIO not found. Running in mock mode.")
    GPIO_AVAILABLE = False

class MotorController:
    # PCA9685 Channels
    ENA = 0
    ENB = 1
    # GPIO Pins
    IN1, IN2 = 23, 24
    IN3, IN4 = 27, 22

    def __init__(self):
        self._mock = not (PCA_AVAILABLE and GPIO_AVAILABLE)
        
        if not self._mock:
            # Initialize PCA9685
            i2c = busio.I2C(SCL, SDA)
            self.pca = PCA9685(i2c)
            self.pca.frequency = 50

            # Initialize GPIO
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            GPIO.setup([self.IN1, self.IN2, self.IN3, self.IN4], GPIO.OUT)
            self.stop()
            print("[Motors] Initialized successfully.")

    def _set_pwm(self, channel, percent):
        if self._mock: return
        percent = max(0.0, min(100.0, percent))
        duty_cycle = int((percent / 100.0) * 65535)
        self.pca.channels[channel].duty_cycle = duty_cycle

    def _set_pins(self, p1, p2, p3, p4):
        if self._mock: return
        GPIO.output(self.IN1, p1)
        GPIO.output(self.IN2, p2)
        GPIO.output(self.IN3, p3)
        GPIO.output(self.IN4, p4)

    def move_forward(self, speed):
        """Both motors forward"""
        self._set_pins(GPIO.HIGH, GPIO.LOW, GPIO.HIGH, GPIO.LOW)
        self._set_pwm(self.ENA, speed)
        self._set_pwm(self.ENB, speed)

    def move_backward(self, speed):
        """Both motors reverse"""
        self._set_pins(GPIO.LOW, GPIO.HIGH, GPIO.LOW, GPIO.HIGH)
        self._set_pwm(self.ENA, speed)
        self._set_pwm(self.ENB, speed)

    def turn_left(self, speed=100.0):
        """Left motor slow, right motor fast"""
        self._set_pins(GPIO.HIGH, GPIO.LOW, GPIO.HIGH, GPIO.LOW)
        self._set_pwm(self.ENA, speed * 0.4) # left slow
        self._set_pwm(self.ENB, speed * 0.7) # right fast

    def turn_right(self, speed=100.0):
        """Right motor slow, left motor fast"""
        self._set_pins(GPIO.HIGH, GPIO.LOW, GPIO.HIGH, GPIO.LOW)
        self._set_pwm(self.ENA, speed * 0.7) # left fast
        self._set_pwm(self.ENB, speed * 0.4) # right slow

    def reverse_turn(self, speed):
        """Both motors backward with steering (same base logic as backward)"""
        self.move_backward(speed)

    def stop(self):
        """Stop all motors"""
        self._set_pins(GPIO.LOW, GPIO.LOW, GPIO.LOW, GPIO.LOW)
        self._set_pwm(self.ENA, 0)
        self._set_pwm(self.ENB, 0)

    def cleanup(self):
        if not self._mock:
            self.stop()
            GPIO.cleanup()
