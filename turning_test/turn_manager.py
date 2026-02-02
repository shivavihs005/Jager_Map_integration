
import time
import threading
from car_driver import driver

class TurnManager:
    def __init__(self):
        self.current_heading = 0 # 0=N, 90=E, 180=S, 270=W
        self.target_heading = 0
        self.turning = False
        self.thread = None
        
        # Tuning
        # How many degrees per second the car turns at a given speed/steer
        # This is strictly a guess for the simulation/dead-reckoning
        self.turn_rate_deg_per_sec = 45.0 
        self.motor_speed = 30 # Slow speed for turning
        self.heading_offset = 0.0 # Degrees

    def set_trim(self, servo_trim, heading_offset):
        driver.servo_trim = servo_trim
        self.heading_offset = heading_offset
        print(f"Calibration Updated: Servo={servo_trim}, Heading={heading_offset}")

    def set_direction(self, direction):
        # Map input string to degrees
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

    def _control_loop(self):
        print("Starting Turn Sequence...")
        
        while self.turning:
            # Calculate Error
            # Shortest turn logic
            # Apply offset to current heading logic if needed, or target.
            # Here: We want Target to be offset. E.g. NORTH is 0, but if offset is 5, correct North is 5.
            # Error = (Target + Offset) - Current
            effective_target = self.target_heading + self.heading_offset
            
            error = effective_target - self.current_heading
            
            # Normalize to -180 to 180
            if error > 180: error -= 360
            elif error < -180: error += 360
            
            print(f"Heading: {self.current_heading:.1f} | Target: {self.target_heading} | Error: {error:.1f}")

            if abs(error) < 5:
                print("Aligned!")
                driver.set_move(0)
                driver.set_steering(0)
                self.turning = False
                break

            # Steer
            # Turn little by little (Smoothly ramp steer)
            # Use max steer for efficiency but we could ramp it if needed
            steer_target = 0.0
            if error > 0:
                steer_target = 1.0 # Right
            else:
                steer_target = -1.0 # Left
                
            # For simplicity in this test, just set steering safe max
            driver.set_steering(steer_target)
            
            # Move
            driver.set_move(self.motor_speed)
            
            # Simulate Heading Update (Dead Reckoning)
            # In real life, read compass here.
            # We assume we update every 0.1s
            step_time = 0.1
            
            # Direction of turn
            turn_dir = 1 if error > 0 else -1
            
            change = self.turn_rate_deg_per_sec * step_time * turn_dir
            
            # Don't overshoot
            if abs(change) > abs(error):
                change = error

            self.current_heading = (self.current_heading + change) % 360
            
            time.sleep(step_time)
            
        print("Turn Complete.")

turn_manager = TurnManager()
