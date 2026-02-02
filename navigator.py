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
            
            # Calculate Total Remaining Distance
            total_remaining = self.calculate_total_remaining_distance(current_loc, self.current_waypoint_index)

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
                
                if diff < 20: # 20 degree tolerance for "straight"
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
            
            # Straight Assist Logic: FORCE LOCK unless major error
            if straight_road_assist:
                 # SUPER AGGRESSIVE Deadband for straight roads
                 # If we are supposed to go straight, IGNORE GPS wandering unless we are WAY off.
                if abs(heading_error) < 45: # 45 degree tolerance! Keep it straight!
                    # print(f"Straight Lock. Err: {heading_error:.1f}")
                    steering_angle = 0.0 # Strict Center
                    # Check if we need to force reset smoothed value to 0 to prevent drift
                    if abs(self.current_steering) > 0.1:
                        self.current_steering = 0.0 
                else:
                    # We are drifting way too much, gentle correction
                    steering_signal = heading_error * 0.01 # Very Low gain to avoid snap
                    steering_angle = max(-0.5, min(0.5, steering_signal)) # Cap steering
                
                target_steering = steering_angle
            else:
                 # Normal Turns logic
                 # Deadband
                if abs(heading_error) < self.steering_deadband:
                    heading_error = 0

                # P-Controller
                steering_signal = heading_error * 0.04 
                target_steering = max(-1.0, min(1.0, steering_signal))

            # Smoothing Logic ("Turn little by little")
            # Move current_steering towards target_steering by steering_step
            if target_steering > self.current_steering:
                self.current_steering = min(target_steering, self.current_steering + self.steering_step)
            elif target_steering < self.current_steering:
                self.current_steering = max(target_steering, self.current_steering - self.steering_step)
            
            # Use the smoothed value
            final_steering = self.current_steering
            
            print(f"WP:{self.current_waypoint_index} | Dist:{dist:.1f}m | Tot:{total_remaining:.1f}m | Hdg:{current_heading:.1f} | Tgt:{bearing:.1f} | Str:{final_steering:.2f} | {'LOCK' if straight_road_assist and abs(heading_error) < 45 else 'NAV'}")

            car.set_steering(final_steering) 
            car.set_speed(target_speed)
            
            state_machine.update_motion_state(target_speed, final_steering)
            
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
