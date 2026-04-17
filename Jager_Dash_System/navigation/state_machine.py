import math
import time
import requests
import threading
from hardware.sensors import SensorsData
from hardware.motor_controller import MotorController

# --- Helper Math Functions ---
def haversine(lat1, lon1, lat2, lon2):
    R = 6371000 # radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi/2.0)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(delta_lambda/2.0)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

def calculate_bearing(lat1, lon1, lat2, lon2):
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1)*math.sin(lat2) - math.sin(lat1)*math.cos(lat2)*math.cos(dlon)
    return (math.degrees(math.atan2(x, y)) + 360) % 360

def normalize_angle(angle):
    while angle > 180: angle -= 360
    while angle < -180: angle += 360
    return angle

def angle_between(bearing1, bearing2):
    return normalize_angle(bearing2 - bearing1)

class StateMachine:
    def __init__(self):
        self.mode = "STOP"
        self.sensors = SensorsData()
        self.motor = MotorController()
        
        self.waypoints = []
        self.current_wp_index = 0
        
        # Navigation tuning
        self.Kp = 8.0 # Steering proportional gain
        self.MAX_STEER = 400 # Max offset from center (1460-1040=420 max)
        
        self.nav_thread = None
        self.running = False

    def set_mode(self, mode):
        self.mode = mode
        print(f"[STATE MACHINE] Mode set to {self.mode}")

    def start(self):
        self.running = True
        self.motor.set_state("STOP")
        if self.mode == "OUTDOOR":
            self.nav_thread = threading.Thread(target=self.outdoor_main_loop, daemon=True)
            self.nav_thread.start()
        elif self.mode == "INDOOR":
            self.nav_thread = threading.Thread(target=self.indoor_main_loop, daemon=True)
            self.nav_thread.start()

    def stop(self):
        self.running = False
        self.mode = "STOP"
        self.motor.stop()
        if self.nav_thread:
            self.nav_thread.join(timeout=1.0)
            self.nav_thread = None

    def fetch_osrm_route(self, lat1, lon1, lat2, lon2):
        print(f"[NAV] Fetching OSRM Route from {lat1},{lon1} to {lat2},{lon2}")
        url = f"https://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=full&geometries=geojson"
        try:
            res = requests.get(url, timeout=5).json()
            if res.get("code") == "Ok":
                coords = res["routes"][0]["geometry"]["coordinates"]
                self.generate_waypoint_states(coords)
                return self.waypoints
        except Exception as e:
            print(f"[NAV] OSRM Fetch Failed: {e}")
        return []

    def generate_waypoint_states(self, coords):
        """Converts raw coordinates into Radius-Based Zones with Action labels"""
        self.waypoints = []
        for i in range(len(coords)):
            action = "STRAIGHT"
            if i > 0 and i < len(coords)-1:
                b1 = calculate_bearing(coords[i-1][1], coords[i-1][0], coords[i][1], coords[i][0])
                b2 = calculate_bearing(coords[i][1], coords[i][0], coords[i+1][1], coords[i+1][0])
                angle = angle_between(b1, b2)
                if angle > 15:
                    action = "RIGHT"
                elif angle < -15:
                    action = "LEFT"
            
            # Master Prompt WP Structure: Radius = 3.0 meters
            self.waypoints.append({
                "lat": coords[i][1],
                "lon": coords[i][0],
                "action": action,
                "radius": 3.0 
            })
        self.current_wp_index = 0
        print(f"[NAV] Generated {len(self.waypoints)} Radius-Based Waypoints.")

    def outdoor_main_loop(self):
        """The core continuous autonomous loop"""
        print("[NAV] Entering Continuous OUTDOOR Loop...")
        while self.running and self.mode == "OUTDOOR":
            gps = self.sensors.get_filtered_gps()
            heading = self.sensors.get_heading()
            # obstacle_dist = self.sensors.read_sdm15() # REMOVED: SDM15 is an energy meter
            # TODO: Integrate dedicated distance sensor for obstacle avoidance
            obstacle_dist = 999.0 # Mock value

            # Priority 1: Obstacle Avoidance
            if obstacle_dist < 40.0:
                print(f"[NAV] OBSTACLE DETECTED at {obstacle_dist}cm! Engaging Avoidance.")
                self.motor.avoid_obstacle()
                continue
                
            # Priority 2: Navigation Target
            if not self.waypoints or self.current_wp_index >= len(self.waypoints):
                print("[NAV] Destination Reached or No Waypoints. Halting.")
                self.stop()
                break

            current_wp = self.waypoints[self.current_wp_index]
            dist = haversine(gps["lat"], gps["lon"], current_wp["lat"], current_wp["lon"])

            # 🔹 RANGE-BASED TRIGGER
            if dist < current_wp["radius"]:
                print(f"[NAV] Entered WP Zone {self.current_wp_index} (Dist: {dist:.1f}m). Triggering Action: {current_wp['action']}")
                if self.current_wp_index < len(self.waypoints) - 1:
                    next_wp = self.waypoints[self.current_wp_index + 1]
                    target_bearing = calculate_bearing(gps["lat"], gps["lon"], next_wp["lat"], next_wp["lon"])
                else:
                    target_bearing = calculate_bearing(gps["lat"], gps["lon"], current_wp["lat"], current_wp["lon"])
                self.current_wp_index += 1
            else:
                target_bearing = calculate_bearing(gps["lat"], gps["lon"], current_wp["lat"], current_wp["lon"])

            # Error computation
            error = normalize_angle(target_bearing - heading)
            
            # Continuous Steering logic: pd control
            steering = self.Kp * error
            steering = max(min(steering, self.MAX_STEER), -self.MAX_STEER) # Clamp
            
            pulse = int(self.motor.SERVO_CENTER + steering)
            self.motor.move_forward(pulse)
            
            # Loop delay for stable CPU tracking (20Hz)
            time.sleep(0.05)

    def indoor_main_loop(self):
        """Simple mockup for indoor camera direction logic"""
        from hardware.camera import CameraStream
        cam = CameraStream()
        while self.running and self.mode == "INDOOR":
            # obstacle_dist = self.sensors.read_sdm15() # REMOVED: SDM15 is an energy meter
            # TODO: Integrate dedicated distance sensor for obstacle avoidance
            obstacle_dist = 999.0 # Mock value

            if obstacle_dist < 40.0:
                 self.motor.avoid_obstacle()
            else:
                 # Simplified bright-seeking logic mock wrapper
                 steering_pulse = cam.get_brightness_direction()
                 self.motor.move_forward(steering_pulse)
            time.sleep(0.1)

    def manual_joystick(self, x, y):
        if self.mode == "MANUAL":
            self.motor.execute_joystick(x, y)
