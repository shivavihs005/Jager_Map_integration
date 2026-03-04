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
        self.current_angle = 90.0

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
        target_angle = max(0.0, min(180.0, float(target_angle)))
        self.current_angle = target_angle
        self._write_angle(self.current_angle)

    def _write_angle(self, angle):
        if self._mock: return

        # Exact formula from user's working script
        duty = 2 + (angle / 18.0)
        GPIO.output(self.SERVO_PIN, True)
        self.pwm.ChangeDutyCycle(duty)
        time.sleep(0.4)
        GPIO.output(self.SERVO_PIN, False)
        self.pwm.ChangeDutyCycle(0)

    def center(self):
        """Center position = 90°"""
        self.set_angle(90.0)

    def steer_left(self):
        """Left = 60°"""
        self.set_angle(60.0)

    def steer_right(self):
        """Right = 120°"""
        self.set_angle(120.0)
        
    def cleanup(self):
        if not self._mock:
            self.pwm.stop()
