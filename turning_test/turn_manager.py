import time
import threading
import sys
import os

# Put parent directory into path so we can import the new autonomous modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from sensor import sensor_system
from motor import motor
from state_machine import state_machine, CarMode, MotionState

# Ensure sensors are running
sensor_system.start()

class TurnManager:
    def __init__(self):
        self.target_heading = 0
        self.turning = False
        self.thread = None
        
        self.servo_trim = 0.0
        self.heading_offset = 0.0

    def set_trim(self, servo_trim, heading_offset):
        self.servo_trim = servo_trim
        self.heading_offset = heading_offset
        # Apply trim to motor logic (in actual implementation we'd expose a center offset config)
        print(f"Calibration Updated: Servo={servo_trim}, Heading={heading_offset}")

    def set_direction(self, direction):
        mapping = {'NORTH': 0, 'EAST': 90, 'SOUTH': 180, 'WEST': 270}
        if direction in mapping:
            self.target_heading = mapping[direction]
            print(f"Target set to {direction} ({self.target_heading})")
            self.start_turn()

    def start_turn(self):
        if self.turning: return
        self.turning = True
        self.thread = threading.Thread(target=self._control_loop)
        self.thread.daemon = True
        self.thread.start()

    @property
    def current_heading(self):
        # We will map the relative IMU yaw to our test dashboard "compass"
        # Using the heading_offset to calibrate "North"
        data = sensor_system.get_data()
        # Ensure it's 0-360 mapped
        h = (data['current_yaw'] + self.heading_offset) % 360
        if h < 0: h += 360
        return h

    def _control_loop(self):
        print("Starting Hardware MPU Turn Sequence...")
        
        while self.turning:
            effective_target = self.target_heading
            curr = self.current_heading
            
            error = effective_target - curr
            if error > 180: error -= 360
            elif error < -180: error += 360
            
            print(f"Heading: {curr:.1f} | Target: {effective_target} | Error: {error:.1f}")

            if abs(error) < 5:
                print("Aligned!")
                motor.stop()
                self.turning = False
                break

            # Turn using actual motor API instead of setting a target for dead reckoning
            steer_target = 30.0 if error > 0 else -30.0 # max right vs max left physical degrees
            
            # The test uses drive_forward but we can also use precise relative turn 
            # motor.turn_by_degree(error) is blocking, so if we use it, our UI won't update mid-turn
            # unless we read it from another thread.
            # Instead, since this thread is the control loop, we'll manually apply drive and stop
            
            # Simple proportional or just max steer
            motor.set_steering(steer_target)
            
            # For a pure "turn on spot" simulation equivalent on Ackermann, we can just drive_forward
            # If the car can do differential steering, you'd do that in motor.set_speed
            motor.set_speed(30)
            
            # small delay before next reading
            time.sleep(0.05)
            
        print("Hardware Turn Complete.")
        motor.stop()

turn_manager = TurnManager()

