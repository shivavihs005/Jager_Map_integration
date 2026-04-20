import time
import random

try:
    import pigpio
    PI_ENV = True
except ImportError:
    PI_ENV = False

class MotorController:
    def __init__(self):
        self.state = "STOP"
        self.speed = 0
        self.steering_angle = 1040
        
        self.SERVO_LEFT = 680
        self.SERVO_CENTER = 1040
        self.SERVO_RIGHT = 1460

        # BTS7960 Pins
        self.R_EN = 23
        self.L_EN = 24
        self.RPWM = 13
        self.LPWM = 12
        # Servo
        self.SERVO_PIN = 17

        print(f"[MOTOR] Initializing... Hardware Environment: {'Pi' if PI_ENV else 'Windows Mock'}")
        
        self.pi = None
        if PI_ENV:
            self.pi = pigpio.pi()
            if not self.pi.connected:
                print("[MOTOR] pigpio daemon not running! Reverting to mock.")
                self.pi = None
            else:
                self.pi.set_mode(self.R_EN, pigpio.OUTPUT)
                self.pi.set_mode(self.L_EN, pigpio.OUTPUT)
                self.pi.write(self.R_EN, 1)
                self.pi.write(self.L_EN, 1)
                
                # Set PWM frequency
                self.pi.set_PWM_frequency(self.RPWM, 1000)
                self.pi.set_PWM_frequency(self.LPWM, 1000)
                
                self.set_steering(self.SERVO_CENTER)

    def set_state(self, state, speed=None):
        self.state = state
        if speed is not None:
            self.speed = max(0, min(100, speed))
            pwm_val = int((self.speed / 100.0) * 255)
            
            if self.pi:
                if state == "FORWARD":
                    self.pi.set_PWM_dutycycle(self.RPWM, pwm_val)
                    self.pi.set_PWM_dutycycle(self.LPWM, 0)
                elif state == "REVERSE":
                    self.pi.set_PWM_dutycycle(self.RPWM, 0)
                    self.pi.set_PWM_dutycycle(self.LPWM, pwm_val)
                elif state == "STOP":
                    self.pi.set_PWM_dutycycle(self.RPWM, 0)
                    self.pi.set_PWM_dutycycle(self.LPWM, 0)
            

    def move_forward(self, steering_pulse, speed=50):
        """Autonomous loop core handler — accepts both steering and speed."""
        self.set_steering(steering_pulse)
        self.set_state("FORWARD", speed) 
        
    def avoid_obstacle(self):
        """Emergency stop and reverse routine for outdoor mode."""
        self.stop()
        time.sleep(0.5)
        self.set_steering(self.SERVO_CENTER)
        self.set_state("REVERSE", 40)
        time.sleep(1)
        self.stop()

    def avoid_obstacle_indoor(self):
        """
        Indoor evasion sequence:
        1. Stop motors
        2. Reverse at 40% for 0.8 seconds
        3. Turn servo full left or right (alternating)  
        4. Move forward for 2 seconds
        5. Center servo and resume
        """
        print("[MOTOR] Indoor obstacle evasion triggered!")
        
        # Step 1: Stop
        self.stop()
        time.sleep(0.3)
        
        # Step 2: Back up slightly
        self.set_steering(self.SERVO_CENTER)
        self.set_state("REVERSE", 40)
        time.sleep(0.8)
        self.stop()
        time.sleep(0.2)
        
        # Step 3: Pick random turn direction
        turn_dir = random.choice([self.SERVO_LEFT, self.SERVO_RIGHT])
        direction_name = "LEFT" if turn_dir == self.SERVO_LEFT else "RIGHT"
        print(f"[MOTOR] Evasion turn: {direction_name}")
        self.set_steering(turn_dir)
        time.sleep(0.3)  # Wait for servo to reach position
        
        # Step 4: Move forward for 2 seconds with turned steering
        self.set_state("FORWARD", 35)
        time.sleep(2.0)
        
        # Step 5: Center servo
        self.set_steering(self.SERVO_CENTER)
        time.sleep(0.1)
        
        print("[MOTOR] Evasion complete, resuming.")

    def ramp_speed(self, target_speed, duration=3.0, step_interval=0.1):
        """
        Gradually ramp motor speed from current to target over `duration` seconds.
        Used for smooth indoor start-up.
        """
        current = self.speed
        steps = int(duration / step_interval)
        if steps <= 0:
            steps = 1
        increment = (target_speed - current) / steps
        
        for i in range(steps):
            current += increment
            clamped = max(0, min(100, int(current)))
            self.set_state("FORWARD", clamped)
            time.sleep(step_interval)
        
        # Final set to exact target
        self.set_state("FORWARD", max(0, min(100, target_speed)))
        print(f"[MOTOR] Ramp complete → {target_speed}% speed")

    def set_steering(self, angle_pulse):
        self.steering_angle = max(self.SERVO_LEFT, min(self.SERVO_RIGHT, int(angle_pulse)))
        if self.pi:
            self.pi.set_servo_pulsewidth(self.SERVO_PIN, self.steering_angle)

    def stop(self):
        self.set_state("STOP", 0)
        self.set_steering(self.SERVO_CENTER)

    def execute_joystick(self, x, y):
        pulse = self.SERVO_CENTER + (x / 100.0) * (self.SERVO_RIGHT - self.SERVO_CENTER)
        self.set_steering(pulse)
        if y > 10:
            self.set_state("FORWARD", y)
        elif y < -10:
            self.set_state("REVERSE", abs(y))
        else:
            self.set_state("STOP", 0)
