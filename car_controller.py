try:
    import RPi.GPIO as GPIO
    MOCK_GPIO = False
except ImportError:
    print("RPi.GPIO not found. Using Mock GPIO.")
    MOCK_GPIO = True
    # create a dummy GPIO class to prevent NameError later if not careful, 
    # though we mainly use the flag to skip logic.
    class MockGPIO:
        BCM = 'BCM'
        OUT = 'OUT'
        HIGH = 'HIGH'
        LOW = 'LOW'
        def setmode(self, mode): pass
        def setwarnings(self, flag): pass
        def setup(self, pin, mode): pass
        def output(self, pin, state): pass
        def cleanup(self): pass
        class PWM:
            def __init__(self, pin, freq): pass
            def start(self, duty): pass
            def ChangeDutyCycle(self, duty): pass
            def stop(self): pass
    GPIO = MockGPIO()
import time
import threading

class CarController:
    def __init__(self):
        # Pin Configuration
        self.SERVO_PIN = 18
        self.R_EN = 23
        self.L_EN = 24
        self.PIN_BACKWARD = 12
        self.PIN_FORWARD = 13
        
        # State
        self.current_speed = 0
        self.current_angle = 90
        self.last_servo_update = 0
        self.servo_timer = None
        
        # Configuration
        self.STEERING_INVERTED = False # Set to True if car turns Left when it should turn Right
        self.OFFSET_ANGLE = 0.0 # Trim in degrees
        
        if MOCK_GPIO:
            print("Using Mock GPIO Driver (Import Failed).")
            self.mock_mode = True
            # Setup dummy objects so logic doesn't crash on undefined vars
            self._setup_gpio()
        else:
            try:
                self._setup_gpio()
            except RuntimeError:
                print("GPIO Error: Likely not running on a Pi. Hardware control disabled.")
                self.mock_mode = True
            else:
                self.mock_mode = False

    def _setup_gpio(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # Setup Pins
        GPIO.setup([self.R_EN, self.L_EN, self.PIN_FORWARD, self.PIN_BACKWARD], GPIO.OUT)
        GPIO.output(self.R_EN, GPIO.HIGH)
        GPIO.output(self.L_EN, GPIO.HIGH)
        GPIO.setup(self.SERVO_PIN, GPIO.OUT)

        # Initialize PWM
        self.pwm_forward = GPIO.PWM(self.PIN_FORWARD, 1000)
        self.pwm_forward.start(0)
        
        self.pwm_backward = GPIO.PWM(self.PIN_BACKWARD, 1000)
        self.pwm_backward.start(0)
        
        self.servo_pwm = GPIO.PWM(self.SERVO_PIN, 50)
        self.servo_pwm.start(0) # 0 means off initially

    def set_speed(self, speed):
        """
        Control motor speed.
        speed: -100 (Full Reverse) to 100 (Full Forward)
        """
        if self.mock_mode:
            print(f"[MOCK] Motor Speed: {speed}%")
            return

        # Clamp speed
        speed = max(-100, min(100, speed))
        
        if speed > 0:
            self.pwm_forward.ChangeDutyCycle(speed)
            self.pwm_backward.ChangeDutyCycle(0)
        elif speed < 0:
            self.pwm_forward.ChangeDutyCycle(0)
            self.pwm_backward.ChangeDutyCycle(abs(speed))
        else:
            self.pwm_forward.ChangeDutyCycle(0)
            self.pwm_backward.ChangeDutyCycle(0)

    def set_steering(self, angle_percent):
        """
        Control steering servo.
        angle_percent: -1.0 (Left) to 1.0 (Right)
        """
        if self.mock_mode:
            print(f"[MOCK] Steering: {angle_percent}")
            return

        # Clamp (-1 to 1)
        val = max(-1.0, min(1.0, angle_percent))
        
        if self.STEERING_INVERTED:
            val = -val
        
        # Map to angle (0-180) approximately based on user code logic
        # User Logic: 
        #   -0.5 to 0.5 = 90 (Center)
        #   > 0.5 = val * 180
        #   else = (val + 1) * 180
        
        # We'll use a smoother mapping for autonomous control
        # Map -1..1 to 45..135 degrees (avoid stuck at 0/180 and chassis hit)
        # -1 -> 45 deg, 0 -> 90 deg, 1 -> 135 deg
        target_angle = 90 + (val * 45) + self.OFFSET_ANGLE
        
        # Convert to Duty Cycle
        # Standard Servo: 2.5% (0deg) to 12.5% (180deg) usually
        # User code used: 2.5 + (angle / 18.0)
        duty = 2.5 + (target_angle / 18.0)
        
        self.servo_pwm.ChangeDutyCycle(duty)
        
        # Prevent Jitter: Turn off servo signal after short delay
        # This allows the servo to reach position then relax.
        if hasattr(self, 'servo_timer') and self.servo_timer:
            self.servo_timer.cancel()
        
        def stop_servo_signal():
            if not self.mock_mode:
                self.servo_pwm.ChangeDutyCycle(0)
        
        # Increased time slightly to ensure it reaches position "little by little"
        self.servo_timer = threading.Timer(0.5, stop_servo_signal)
        self.servo_timer.start()

    def stop(self):
        self.set_speed(0)
        self.set_steering(0) # Center
        
    def cleanup(self):
        if not self.mock_mode:
            self.pwm_forward.stop()
            self.pwm_backward.stop()
            self.servo_pwm.stop()
            GPIO.cleanup()

# Create global instance
car = CarController()
