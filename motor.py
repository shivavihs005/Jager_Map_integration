import time
import threading
from state_machine import state_machine, MotionState

try:
    import RPi.GPIO as GPIO
    MOCK_GPIO = False
except ImportError:
    MOCK_GPIO = True
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
    print("MOCK GPIO used in motor.py")

from sensor import sensor_system

class MotorController:
    def __init__(self):
        self.SERVO_PIN = 18
        self.R_EN = 23
        self.L_EN = 24
        self.PIN_BACKWARD = 12
        self.PIN_FORWARD = 13
        
        self.STEER_CENTER = 90
        self.STEER_LEFT_MAX = -30
        self.STEER_RIGHT_MAX = 30
        
        self.mock_mode = MOCK_GPIO
        self._setup_gpio()
        self.stop()
        
    def _setup_gpio(self):
        if self.mock_mode: return
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup([self.R_EN, self.L_EN, self.PIN_FORWARD, self.PIN_BACKWARD, self.SERVO_PIN], GPIO.OUT)
        GPIO.output(self.R_EN, GPIO.HIGH)
        GPIO.output(self.L_EN, GPIO.HIGH)
        
        self.pwm_forward = GPIO.PWM(self.PIN_FORWARD, 1000)
        self.pwm_backward = GPIO.PWM(self.PIN_BACKWARD, 1000)
        self.servo_pwm = GPIO.PWM(self.SERVO_PIN, 50) # 50Hz for servo
        
        self.pwm_forward.start(0)
        self.pwm_backward.start(0)
        self.servo_pwm.start(0)

    def set_speed(self, speed):
        # speed: -100 to 100
        speed = max(-100, min(100, speed))
        
        if speed > 0:
            if not self.mock_mode:
                self.pwm_forward.ChangeDutyCycle(speed)
                self.pwm_backward.ChangeDutyCycle(0)
        elif speed < 0:
            if not self.mock_mode:
                self.pwm_forward.ChangeDutyCycle(0)
                self.pwm_backward.ChangeDutyCycle(abs(speed))
        else:
            if not self.mock_mode:
                self.pwm_forward.ChangeDutyCycle(0)
                self.pwm_backward.ChangeDutyCycle(0)

    def set_steering(self, angle): 
        # Angle from -30 to 30
        angle = max(self.STEER_LEFT_MAX, min(self.STEER_RIGHT_MAX, angle))
        target_angle = self.STEER_CENTER + angle
        
        # Convert to duty cycle (2.5% to 12.5% for 0 to 180 deg typically)
        duty = 2.5 + (target_angle / 18.0)
        if not self.mock_mode:
            self.servo_pwm.ChangeDutyCycle(duty)

    def stop(self):
        self.set_speed(0)
        self.set_steering(0)
        state_machine.set_motion_state(MotionState.STOPPED)

    def drive_forward(self, speed, steering_angle):
        self.set_speed(speed)
        self.set_steering(steering_angle)
        
        if steering_angle < -5:
            state_machine.set_motion_state(MotionState.TURN_LEFT)
        elif steering_angle > 5:
            state_machine.set_motion_state(MotionState.TURN_RIGHT)
        else:
            state_machine.set_motion_state(MotionState.FORWARD)

    def drive_backward(self, speed, steering_angle):
        self.set_speed(-abs(speed))
        self.set_steering(steering_angle)
        state_machine.set_motion_state(MotionState.BACKWARD)

    def turn_by_degree(self, target_angle_diff):
        """
        Precise turn logic using IMU input.
        """
        state_machine.set_motion_state(MotionState.PRECISION_TURN)
        sensor_system.reset_yaw()
        
        if target_angle_diff > 0:
            self.set_steering(self.STEER_RIGHT_MAX)
        else:
            self.set_steering(self.STEER_LEFT_MAX)
            
        self.set_speed(30) # fixed turning speed
        
        while True:
            current_yaw = sensor_system.get_data()['current_yaw']
            error = abs(abs(target_angle_diff) - abs(current_yaw))
            if error < 5.0: # 5 degree tolerance
                break
            # Emergency fallback or stop condition check
            state = state_machine.get_state()
            if state['mode'] != "SEMI_AUTO" and state['mode'] != "AUTO":
                break
            time.sleep(0.05)
            
        self.stop()

motor = MotorController()
