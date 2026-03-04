"""
motor_controller.py — Controls the DC drive motor using RPi.GPIO and BTS7960 High-Power Motor Driver
"""
import time
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    print("[Motors] RPi.GPIO not found. Running in mock mode.")
    GPIO_AVAILABLE = False

class MotorController:
    # BTS7960 / Motor Driver Pins
    R_EN = 23   # Right Enable (usually tied high, or GPIO controlled)
    L_EN = 24   # Left Enable
    RPWM = 13   # Forward speed control
    LPWM = 12   # Backward speed control

    def __init__(self):
        self._mock = not GPIO_AVAILABLE
        
        if not self._mock:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            
            # Setup pins as outputs
            GPIO.setup([self.R_EN, self.L_EN, self.RPWM, self.LPWM], GPIO.OUT)
            
            # Enable the BTS7960 bridges (setting both enables High turns the driver ON)
            GPIO.output(self.R_EN, GPIO.HIGH)
            GPIO.output(self.L_EN, GPIO.HIGH)
            
            # Initialize hardware PWM on the direction pins at 1000Hz
            self.pwm_fwd = GPIO.PWM(self.RPWM, 1000)
            self.pwm_bwd = GPIO.PWM(self.LPWM, 1000)
            
            self.pwm_fwd.start(0)
            self.pwm_bwd.start(0)
            print("[Motors] BTS7960 Initialized successfully on GPIO 13, 12, 23, 24.")

    def move_forward(self, speed):
        """Drive forward by pulsing RPWM and pulling LPWM to 0"""
        if self._mock: return
        speed = max(0.0, min(100.0, float(speed)))
        self.pwm_bwd.ChangeDutyCycle(0)
        self.pwm_fwd.ChangeDutyCycle(speed)

    def move_backward(self, speed):
        """Drive backward by pulsing LPWM and pulling RPWM to 0"""
        if self._mock: return
        speed = max(0.0, min(100.0, float(speed)))
        self.pwm_fwd.ChangeDutyCycle(0)
        self.pwm_bwd.ChangeDutyCycle(speed)

    def turn_left(self, speed=50.0):
        """In an Ackermann steering setup, the back motor just drives forward."""
        self.move_forward(speed)

    def turn_right(self, speed=50.0):
        """In an Ackermann steering setup, the back motor just drives forward."""
        self.move_forward(speed)

    def reverse_turn(self, speed=50.0):
        """Drive backward while turning."""
        self.move_backward(speed)

    def stop(self):
        """Stop motor by zeroing both PWM signals"""
        if self._mock: return
        self.pwm_fwd.ChangeDutyCycle(0)
        self.pwm_bwd.ChangeDutyCycle(0)

    def cleanup(self):
        """Polite hardware shutdown"""
        if not self._mock:
            self.stop()
            # Disable the driver bridges
            GPIO.output(self.R_EN, GPIO.LOW)
            GPIO.output(self.L_EN, GPIO.LOW)
            self.pwm_fwd.stop()
            self.pwm_bwd.stop()
