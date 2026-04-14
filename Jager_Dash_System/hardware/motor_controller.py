import time

class MotorController:
    """Mock motor controller for Windows testing."""
    def __init__(self):
        self.state = "STOP"
        self.speed = 0
        self.steering_angle = 1060 # Center by default
        
        # Simulated Pulse Values
        self.SERVO_LEFT = 680
        self.SERVO_CENTER = 1060
        self.SERVO_RIGHT = 1460
        
        print("[MOCK MOTOR] Motor Controller Initialized")

    def set_state(self, state, speed=None):
        if state not in ["FORWARD", "REVERSE", "TURN_LEFT", "TURN_RIGHT", "STOP"]:
            print(f"[MOCK MOTOR] Invalid state: {state}")
            return
            
        self.state = state
        if speed is not None:
            self.speed = max(0, min(100, speed))
            
        print(f"[MOCK MOTOR] State changed to: {self.state} with speed: {self.speed}%")

    def set_steering(self, angle_pulse):
        self.steering_angle = max(self.SERVO_LEFT, min(self.SERVO_RIGHT, angle_pulse))
        print(f"[MOCK SERVO] Steering angle set to pulse: {self.steering_angle} µs")

    def stop(self):
        self.set_state("STOP", 0)
        self.set_steering(self.SERVO_CENTER)
        
    def execute_joystick(self, x, y):
        """Map generic joystick x, y (-100 to 100) to motors and servo."""
        # Convert X (-100 to 100) to Steering pulse
        # x=-100 -> LEFT (680), x=0 -> CENTER (1060), x=100 -> RIGHT (1460)
        pulse = self.SERVO_CENTER + (x / 100.0) * (self.SERVO_RIGHT - self.SERVO_CENTER)
        self.set_steering(int(pulse))
        
        # Convert Y (-100 to 100) to speed and direction
        if y > 10:
            self.set_state("FORWARD", y)
        elif y < -10:
            self.set_state("REVERSE", abs(y))
        else:
            self.set_state("STOP", 0)
