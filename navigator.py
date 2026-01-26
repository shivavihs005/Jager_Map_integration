import math
import time
import threading
from gps_reader import gps_reader
from car_controller import car

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
            current_loc = gps_reader.get_location()
            
            # If no GPS fix, stop and wait
            if current_loc['lat'] == 0 and current_loc['lng'] == 0:
                print("Waiting for GPS fix...")
                car.stop()
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

            # NOTE: We don't have a compass! 
            # We assume the car is moving and calculate heading from previous positions
            # OR we just blindly steer towards the bearing if we assume "Forward" is north (incorrect)
            # For a proper rover, you need a Magnetometer (Compass).
            # HERE, we will implement a simple "Drive and Correct" heuristic 
            # assuming we know our heading roughly or just drive straight if unknown.
            
            # Since we lack a Compass in the specs, we can only approximate heading 
            # by comparing last known position to current position.
            # For now, let's just print the needed bearing. 
            # Without a compass, autonomous steering is EXTREMELY difficult.
            # I will assume the car drives "Forward" and we correct based on GPS, 
            # but GPS heading is noisy at low speeds.
            
            print(f"Dist: {dist:.1f}m | Target Bearing: {bearing:.1f}")
            
            # CRITICAL: MISSING COMPASS
            # For this code to work, we need to know the car's current heading (Yaw).
            # Without it, we don't know if we need to turn Left or Right to match the Target Bearing.
            # I will set the steering to Center and Drive Forward as a placeholder 
            # because we cannot intelligently steer without knowing our orientation.
            
            car.set_steering(0) # Drive straight
            car.set_speed(self.base_speed)
            
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
