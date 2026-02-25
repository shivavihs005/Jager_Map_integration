import math
import time
import threading
from sensor import sensor_system
from motor import motor
from state_machine import state_machine, CarMode, MotionState

def normalize_angle(angle):
    while angle > 180: angle -= 360
    while angle < -180: angle += 360
    return angle

def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    a = math.sin(delta_phi/2)**2 + \
        math.cos(phi1) * math.cos(phi2) * \
        math.sin(delta_lambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

def calculate_bearing(lat1, lon1, lat2, lon2):
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_lambda = math.radians(lon2 - lon1)
    
    y = math.sin(delta_lambda) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - \
        math.sin(phi1) * math.cos(phi2) * math.cos(delta_lambda)
    
    theta = math.atan2(y, x)
    bearing = (math.degrees(theta) + 360) % 360
    return bearing

class Navigator:
    def __init__(self):
        self.waypoints = []
        self.current_waypoint_index = 0
        self.is_navigating = False
        self.thread = None
        self.arrival_threshold_meters = 3.0
        
        self.kp = 1.0
        
        # Telemetry
        self.desired_heading = 0.0
        self.heading_error = 0.0
        self.distance_to_next_waypoint = 0.0

    def set_route(self, waypoints):
        self.waypoints = waypoints
        self.current_waypoint_index = 0
        print(f"Route set with {len(waypoints)} waypoints.")

    def start_navigation(self):
        if self.is_navigating: return
        if not self.waypoints: return
        self.is_navigating = True
        self.thread = threading.Thread(target=self._nav_loop, daemon=True)
        self.thread.start()

    def stop_navigation(self):
        self.is_navigating = False
        motor.stop()

    def get_cross_track_error(self, start_lat, start_lng, end_lat, end_lng, curr_lat, curr_lng):
        dist_13 = haversine_distance(start_lat, start_lng, curr_lat, curr_lng)
        bearing_12 = calculate_bearing(start_lat, start_lng, end_lat, end_lng)
        bearing_13 = calculate_bearing(start_lat, start_lng, curr_lat, curr_lng)
        diff = math.radians(normalize_angle(bearing_13 - bearing_12))
        return dist_13 * math.sin(diff)

    def _nav_loop(self):
        print("Autonomous Navigation Started")
        
        # Reset yaw reference at start of maneuver
        sensor_system.reset_yaw()
        
        last_wp_loc = sensor_system.get_data()
        
        while self.is_navigating:
            state = state_machine.get_state()
            if state['mode'] not in [CarMode.SEMI_AUTO.value, CarMode.AUTO.value]:
                self.stop_navigation()
                break
                
            sensor_data = sensor_system.get_data()
            if sensor_data['lat'] == 0:
                print("No GPS, stopping motors.")
                motor.stop()
                time.sleep(0.5)
                continue

            if self.current_waypoint_index >= len(self.waypoints):
                print("Destination Reached")
                motor.stop()
                self.is_navigating = False
                break
                
            target_wp = self.waypoints[self.current_waypoint_index]
            
            # Distance
            dist = haversine_distance(
                sensor_data['lat'], sensor_data['lng'], 
                target_wp['lat'], target_wp['lng']
            )
            self.distance_to_next_waypoint = dist

            if dist < self.arrival_threshold_meters:
                print(f"Reached Waypoint {self.current_waypoint_index}")
                last_wp_loc = sensor_data
                self.current_waypoint_index += 1
                sensor_system.reset_yaw() # Reset yaw at each waypoint per spec
                motor.stop()
                time.sleep(1) # Pause at waypoint
                continue
                
            # Desired Heading
            self.desired_heading = calculate_bearing(
                sensor_data['lat'], sensor_data['lng'],
                target_wp['lat'], target_wp['lng']
            )
            
            # Combine GPS global heading with relative yaw offset
            current_abs_heading = normalize_angle(sensor_data['gps_heading'] + sensor_data['current_yaw'])
            self.heading_error = normalize_angle(self.desired_heading - current_abs_heading)
            
            # Corridor Based Filtering
            xte = self.get_cross_track_error(
                last_wp_loc['lat'], last_wp_loc['lng'],
                target_wp['lat'], target_wp['lng'],
                sensor_data['lat'], sensor_data['lng']
            )
            
            # Corridor width is 2 meters -> +/- 1m
            if abs(xte) < 1.0:
                steering_angle = 0.0 # Force straight
            else:
                # PID (P-only)
                max_turn = min(30.0, state['max_turn'] / 100.0 * 30.0) # Scale to physical degrees
                raw_steer = self.kp * self.heading_error
                steering_angle = max(-max_turn, min(max_turn, raw_steer))
            
            # Speed Control Logic proportional to heading error
            base_speed = state['max_speed']
            reduction_factor = abs(self.heading_error) / 180.0
            final_speed = base_speed * (1.0 - reduction_factor)
            
            motor.drive_forward(final_speed, steering_angle)
            time.sleep(0.05)

navigator = Navigator()

