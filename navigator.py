import math
import time
import threading
from gps_reader import gps_reader
from car_controller import car
from state_machine import state_machine, CarMode, MotionState


class Navigator:
    def __init__(self):
        self.target_location = None # {lat, lng}
        self.is_navigating = False
        self.thread = None
        self.arrival_threshold_meters = 5.0
        
        # PID / Control Parameters
        self.base_speed = 40 # Duty Cycle %
        self.kp = 1.0 # Proportional Gain for steering

    def set_destination(self, lat, lng):
        self.target_location = {'lat': float(lat), 'lng': float(lng)}
        print(f"Destination set to: {self.target_location}")

    def start_navigation(self):
        if self.is_navigating:
            return
        
        if not self.target_location:
            print("No destination set.")
            return

        self.is_navigating = True
        self.thread = threading.Thread(target=self._nav_loop)
        self.thread.daemon = True
        self.thread.start()
        print("Navigation Started")

    def stop_navigation(self):
        self.is_navigating = False
        car.stop()
        print("Navigation Stopped")

    def _nav_loop(self):
        while self.is_navigating:
            # Check Mode
            if state_machine.current_mode != CarMode.AUTONOMOUS:
                print("Mode changed. Stopping navigation.")
                self.stop_navigation()
                break

            current_loc = gps_reader.get_location()
            
            # If no GPS fix, stop and wait
            if current_loc['lat'] == 0 and current_loc['lng'] == 0:
                print("Waiting for GPS fix...")
                car.stop()
                state_machine.update_motion_state(0, 0)
                time.sleep(1)
                continue

            dist = self.haversine_distance(
                current_loc['lat'], current_loc['lng'],
                self.target_location['lat'], self.target_location['lng']
            )

            if dist < self.arrival_threshold_meters:
                print("Arrived at destination!")
                self.stop_navigation()
                break

            # Calculate Bearing
            bearing = self.calculate_bearing(
                current_loc['lat'], current_loc['lng'],
                self.target_location['lat'], self.target_location['lng']
            )

            print(f"Dist: {dist:.1f}m | Target Bearing: {bearing:.1f}")
            
            # Drive Logic
            # Limit speed based on StateMachine settings
            target_speed = min(self.base_speed, state_machine.max_speed)
            
            # Calculate Heading Error
            # Compass/GPS Headings are 0-360 clockwise from North
            # Bearing is also 0-360
            
            # If GPS heading is 0, we might be stationary or have no fix for heading.
            # In that case, we can't reliably steer by heading.
            current_heading = current_loc.get('heading', 0.0)
            
            # Calculate difference
            heading_error = bearing - current_heading
            
            # Normalize to [-180, 180]
            # e.g. target 350, current 10. error = 340. 340 > 180 -> 340 - 360 = -20 (Turn Left)
            if heading_error > 180:
                heading_error -= 360
            elif heading_error < -180:
                heading_error += 360
                
            print(f"Dist: {dist:.1f}m | Hdg: {current_heading:.1f} | Tgt: {bearing:.1f} | Err: {heading_error:.1f}")

            # P-Controller for Steering
            # Error of 90 degrees should probably be max turn?
            # Let's say max turn (1.0) at 45 degrees error?
            # kp = 1.0 / 45.0 = 0.022
            # Let's try kp = 0.02
            
            steering_signal = heading_error * 0.03 # Tunable
            
            # Clamp to [-1.0, 1.0]
            steering_angle = max(-1.0, min(1.0, steering_signal))
            
            car.set_steering(steering_angle) 
            car.set_speed(target_speed)
            
            # Update State Machine for Dashboard
            state_machine.update_motion_state(target_speed, steering_angle)
            
            time.sleep(0.5)

    def haversine_distance(self, lat1, lon1, lat2, lon2):
        R = 6371000 # Radius of Earth in meters
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)
        
        a = math.sin(delta_phi/2)**2 + \
            math.cos(phi1) * math.cos(phi2) * \
            math.sin(delta_lambda/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c

    def calculate_bearing(self, lat1, lon1, lat2, lon2):
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_lambda = math.radians(lon2 - lon1)
        
        y = math.sin(delta_lambda) * math.cos(phi2)
        x = math.cos(phi1) * math.sin(phi2) - \
            math.sin(phi1) * math.cos(phi2) * math.cos(delta_lambda)
        
        theta = math.atan2(y, x)
        bearing = (math.degrees(theta) + 360) % 360
        return bearing

navigator = Navigator()
