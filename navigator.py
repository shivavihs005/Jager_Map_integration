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

            # Check if we have waypoints left
            if self.current_waypoint_index >= len(self.waypoints):
                print("Destination Reached (End of Route)!")
                self.stop_navigation()
                break

            target_wp = self.waypoints[self.current_waypoint_index]
            
            dist = self.haversine_distance(
                current_loc['lat'], current_loc['lng'],
                target_wp['lat'], target_wp['lng']
            )

            # Waypoint Switching Logic
            if dist < self.arrival_threshold_meters:
                print(f"Reached Waypoint {self.current_waypoint_index}")
                self.current_waypoint_index += 1
                if self.current_waypoint_index >= len(self.waypoints):
                    print("Destination Reached!")
                    self.stop_navigation()
                    break
                # Update target immediately
                target_wp = self.waypoints[self.current_waypoint_index]

            # Calculate Bearing to current target
            bearing = self.calculate_bearing(
                current_loc['lat'], current_loc['lng'],
                target_wp['lat'], target_wp['lng']
            )

            # --- Straight Road Detection ---
            # Look ahead: if the bearing to the NEXT waypoint is very similar to current target bearing,
            # we are on a straight road.
            straight_road_assist = False
            if self.current_waypoint_index + 1 < len(self.waypoints):
                next_wp = self.waypoints[self.current_waypoint_index + 1]
                next_bearing = self.calculate_bearing(
                    target_wp['lat'], target_wp['lng'],
                    next_wp['lat'], next_wp['lng']
                )
                
                # Check variance
                diff = abs(bearing - next_bearing)
                if diff > 180: diff = 360 - diff
                
                if diff < 10: # 10 degree tolerance for "straight"
                    straight_road_assist = True
            
            
            # Drive Logic
            target_speed = min(self.base_speed, state_machine.max_speed)
            
            current_heading = current_loc.get('heading', 0.0)
            
            # Calculate Heading Error
            heading_error = bearing - current_heading
            
            # Normalize to [-180, 180]
            if heading_error > 180:
                heading_error -= 360
            elif heading_error < -180:
                heading_error += 360
            
            # Straight Assist Logic: If on straight road and error is small, force 0 steering
            if straight_road_assist and abs(heading_error) < 10:
                print(f"Straight Assist Active. Bearing: {bearing:.1f}")
                steering_angle = 0
            else:
                 # Deadband
                if abs(heading_error) < self.steering_deadband:
                    heading_error = 0

                # P-Controller
                steering_signal = heading_error * 0.04 
                steering_angle = max(-1.0, min(1.0, steering_signal))
            
            print(f"WP:{self.current_waypoint_index} | Dist:{dist:.1f}m | Hdg:{current_heading:.1f} | Tgt:{bearing:.1f} | Str:{steering_angle:.2f}")

            car.set_steering(steering_angle) 
            car.set_speed(target_speed)
            
            state_machine.update_motion_state(target_speed, steering_angle)
            
            time.sleep(0.1) # Faster update rate

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
