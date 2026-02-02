
import time
import threading

try:
    import RPi.GPIO as GPIO
    MOCK_GPIO = False
except ImportError:
    MOCK_GPIO = True
    print("MOCK GPIO ACTIVE")

class CarDriver:
    def __init__(self):
        # Pin Config
        self.SERVO_PIN = 18
        self.PIN_FORWARD = 13
        self.PIN_BACKWARD = 12
        self.R_EN = 23
        self.L_EN = 24

        self.current_angle_val = 0.0 # -1.0 to 1.0
        self.servo_timer = None
        
        if not MOCK_GPIO:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            GPIO.setup([self.R_EN, self.L_EN, self.PIN_FORWARD, self.PIN_BACKWARD, self.SERVO_PIN], GPIO.OUT)
            GPIO.output(self.R_EN, GPIO.HIGH)
            GPIO.output(self.L_EN, GPIO.HIGH)
            
            self.pwm_fwd = GPIO.PWM(self.PIN_FORWARD, 1000)
            self.pwm_bwd = GPIO.PWM(self.PIN_BACKWARD, 1000)
            self.pwm_servo = GPIO.PWM(self.SERVO_PIN, 50)
            
            self.pwm_fwd.start(0)
            self.pwm_bwd.start(0)
            self.pwm_servo.start(0)

    def set_move(self, speed):
        # Speed: -100 to 100
        if MOCK_GPIO:
            print(f"[MOCK] Speed: {speed}")
            return

        if speed > 0:
            self.pwm_fwd.ChangeDutyCycle(speed)
            self.pwm_bwd.ChangeDutyCycle(0)
        elif speed < 0:
            self.pwm_fwd.ChangeDutyCycle(0)
            self.pwm_bwd.ChangeDutyCycle(abs(speed))
        else:
            self.pwm_fwd.ChangeDutyCycle(0)
            self.pwm_bwd.ChangeDutyCycle(0)

    def set_steering(self, val):
        # Val: -1.0 (Left) to 1.0 (Right)
        # Clamped to prevent chassis hit
        val = max(-1.0, min(1.0, val))
        self.current_angle_val = val
        
        if MOCK_GPIO:
            print(f"[MOCK] Steer: {val:.2f}")
            return

        # Map to 45 - 135 degrees
        # 0 = 90 deg (Center)
        target_angle = 90 + (val * 45)
        duty = 2.5 + (target_angle / 18.0)
        
        self.pwm_servo.ChangeDutyCycle(duty)
        
        # Relax after 300ms
        if self.servo_timer:
            self.servo_timer.cancel()
            
        def stop_s():
            self.pwm_servo.ChangeDutyCycle(0)
            
        self.servo_timer = threading.Timer(0.3, stop_s)
        self.servo_timer.start()

    def cleanup(self):
        if not MOCK_GPIO:
            self.pwm_fwd.stop()
            self.pwm_bwd.stop()
            self.pwm_servo.stop()
            GPIO.cleanup()

driver = CarDriver()
