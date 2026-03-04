"""
steering_servo.py — Controls the steering servo
"""
import time

try:
    from adafruit_pca9685 import PCA9685
    from board import SCL, SDA
    import busio
    PCA_AVAILABLE = True
except ImportError:
    PCA_AVAILABLE = False
    GPIO_AVAILABLE = False

class SteeringServo:
    SERVO_PIN = 18
    
    def __init__(self):
        self._mock = not GPIO_AVAILABLE
        self.current_angle = 45.0

        if not self._mock:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            GPIO.setup(self.SERVO_PIN, GPIO.OUT)
            
            # 50Hz PWM frequency for standard servos
            self.pwm = GPIO.PWM(self.SERVO_PIN, 50)
            self.pwm.start(0)
            
            # Start centered
            self.center()
            print(f"[Servo] Initialized successfully on GPIO {self.SERVO_PIN}.")

    def set_angle(self, target_angle):
        # Limit to the physical bounds the user specified (0 to 90)
        target_angle = max(0.0, min(90.0, float(target_angle)))
        self.current_angle = target_angle
        self._write_angle(self.current_angle)

    def _write_angle(self, angle):
        if self._mock: return

        # Exact formula from test_servo.py that proved to work
        # 0 deg = 2.5%, 45 deg = 5.0%, 90 deg = 7.5%
        duty = 2.5 + (angle / 180.0) * 10.0
        self.pwm.ChangeDutyCycle(duty)

    def center(self):
        """Center position = 45°"""
        self.set_angle(45.0)

    def steer_left(self):
        """Left = 0°"""
        self.set_angle(0.0)

    def steer_right(self):
        """Right = 90°"""
        self.set_angle(90.0)
        
    def cleanup(self):
        if not self._mock:
            self.pwm.stop()
