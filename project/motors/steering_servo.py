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

class SteeringServo:
    SERVO_CHANNEL = 4
    
    # Standard 50Hz PWM specs
    MIN_PULSE = 104     # ~0.5ms (0 deg)
    MAX_PULSE = 510     # ~2.5ms (180 deg)
    
    def __init__(self):
        self._mock = not PCA_AVAILABLE
        self.current_angle = 90.0

        if not self._mock:
            i2c = busio.I2C(SCL, SDA)
            self.pca = PCA9685(i2c)
            self.pca.frequency = 50
            print("[Servo] Initialized successfully.")

    def set_angle(self, target_angle):
        target_angle = max(0.0, min(180.0, target_angle))
        
        # Smooth movement — move in 2-degree increments
        step = 2.0 if target_angle > self.current_angle else -2.0
        
        while abs(target_angle - self.current_angle) > 2.0:
            self.current_angle += step
            self._write_angle(self.current_angle)
            time.sleep(0.01) # Short delay for smooth movement
            
        self.current_angle = target_angle
        self._write_angle(self.current_angle)

    def _write_angle(self, angle):
        if self._mock: return

        # Map 0-180 to MIN_PULSE-MAX_PULSE
        pulse = self.MIN_PULSE + (angle / 180.0) * (self.MAX_PULSE - self.MIN_PULSE)
        duty_cycle = int((pulse / 4096.0) * 65535)
        self.pca.channels[self.SERVO_CHANNEL].duty_cycle = duty_cycle

    def center(self):
        """Center position = 90°"""
        self.set_angle(90)

    def steer_left(self):
        """Left = 60°"""
        self.set_angle(60)

    def steer_right(self):
        """Right = 120°"""
        self.set_angle(120)
