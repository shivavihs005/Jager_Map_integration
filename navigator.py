import math
import time
import threading
from gps_reader import gps_reader
from car_controller import car
from state_machine import state_machine, CarMode, MotionState


class Navigator:
    def __init__(self):
        self.waypoints = [] # List of {lat, lng}
        self.current_waypoint_index = 0
        self.is_navigating = False
        self.thread = None
        self.arrival_threshold_meters = 5.0
        
        # PID / Control Parameters
        self.base_speed = 40 # Duty Cycle %
        self.kp = 1.0 # Proportional Gain for steering
        
        # Deadband to prevent jitter
        self.steering_deadband = 5.0 # Degrees
        
        # Smoothing
        self.current_steering = 0.0
        self.steering_step = 0.2 # Max change per update (0.1s) ~ 2.0 per second (normalized)

    def set_route(self, waypoints):
        """
        waypoints: list of dicts {'lat': float, 'lng': float}
        """
        self.waypoints = waypoints
        self.current_waypoint_index = 0
        print(f"Route set with {len(waypoints)} waypoints.")

    def start_navigation(self):
        if self.is_navigating:
            return
        
        if not self.waypoints or len(self.waypoints) == 0:
            print("No route set.")
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

    nav_start_location = None # To store where we started for the first segment

    def calculate_total_remaining_distance(self, current_loc, target_index):
        """
        Calculates the total distance from current location to the target waypoint,
        plus the distance of all subsequent segments.
        """
        if target_index >= len(self.waypoints):
            return 0.0

        total_dist = 0.0
        
        # 1. Distance from current location to current target
        target_wp = self.waypoints[target_index]
        total_dist += self.haversine_distance(
            current_loc['lat'], current_loc['lng'],
            target_wp['lat'], target_wp['lng']
        )
        
        # 2. Distance for remaining segments
        for i in range(target_index, len(self.waypoints) - 1):
            p1 = self.waypoints[i]
            p2 = self.waypoints[i+1]
            total_dist += self.haversine_distance(
                p1['lat'], p1['lng'],
                p2['lat'], p2['lng']
            )
            
        return total_dist

    def get_cross_track_error(self, start_lat, start_lng, end_lat, end_lng, curr_lat, curr_lng):
        """
        Calculates Cross-Track Error (distance from the line start->end).
        Returns distance in meters. Positive = Right of line, Negative = Left.
        """
        R = 6371000 # Earth Radius
        
        # Distance from Start to Current
        dist_13 = self.haversine_distance(start_lat, start_lng, curr_lat, curr_lng)
        
        # Bearing from Start to End (Path Bearing)
        bearing_12 = self.calculate_bearing(start_lat, start_lng, end_lat, end_lng)
        
        # Bearing from Start to Current
        bearing_13 = self.calculate_bearing(start_lat, start_lng, curr_lat, curr_lng)
        
        # Angle Difference
        diff = math.radians(bearing_13 - bearing_12)
        
        # XTE Formula (approximate for small distances, or precise spherical)
        # XTE = asin(sin(dist_13/R) * sin(diff)) * R
        # Since distances are small compared to Earth radius, simpler formula:
        # XTE = dist_13 * math.sin(diff)
        
        return dist_13 * math.sin(diff)

    def _nav_loop(self):
        # Initialize last_visited with current location when starting
        # We need a stable start point for the first segment
        start_loc = gps_reader.get_location()
        while start_loc['lat'] == 0:
             print("Waiting for GPS to initialize start point...")
             time.sleep(1)
             if not self.is_navigating: return
             start_loc = gps_reader.get_location()

        last_visited_wp = start_loc
        print(f"Navigation Loop Started. Start Loc: {start_loc}")

        while self.is_navigating:
            # Check Mode
            if state_machine.current_mode != CarMode.AUTONOMOUS:
                print("Mode changed. Stopping navigation.")
                self.stop_navigation()
                break

            current_loc = gps_reader.get_location()
            
            if current_loc['lat'] == 0:
                print("Lost GPS fix...")
                car.stop()
                time.sleep(0.5)
                continue

            if self.current_waypoint_index >= len(self.waypoints):
                print("Destination Reached!")
                self.stop_navigation()
                break

            target_wp = self.waypoints[self.current_waypoint_index]
            
            # Distance to Target
            dist_to_target = self.haversine_distance(
                current_loc['lat'], current_loc['lng'],
                target_wp['lat'], target_wp['lng']
            )

            # Total Distance
            total_remaining = self.calculate_total_remaining_distance(current_loc, self.current_waypoint_index)

            # --- Waypoint Switching ---
            if dist_to_target < self.arrival_threshold_meters:
                print(f"Reached Waypoint {self.current_waypoint_index}")
                # Update last visited to the waypoint we just reached (ideal point)
                # This snaps the start of the next line to the exact waypoint coordinate
                last_visited_wp = target_wp 
                
                self.current_waypoint_index += 1
                if self.current_waypoint_index >= len(self.waypoints):
                   print("Route Complete.")
                   self.stop_navigation()
                   break
                
                # Update target
                target_wp = self.waypoints[self.current_waypoint_index]

            # --- STEERING DISABLED IN AUTONOMOUS MODE ---
            # User requested: Always keep servo at 90 degrees (straight)
            # No GPS-based steering corrections
            
            steering_mode = "LOCK"
            final_steering = 0.0
            self.current_steering = 0.0

            # Drive
            target_speed = min(self.base_speed, state_machine.max_speed)
            car.set_steering(final_steering)
            car.set_speed(target_speed)
            state_machine.update_motion_state(target_speed, final_steering)

            print(f"WP:{self.current_waypoint_index} | DistToWP:{dist_to_target:.1f}m | Tot:{total_remaining:.1f}m | Mode:STRAIGHT_ONLY | Str:0.00")

            time.sleep(0.1)

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
