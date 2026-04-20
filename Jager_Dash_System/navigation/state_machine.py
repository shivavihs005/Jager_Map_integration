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
        self.max_speed = 50  # Default from slider
        
        # PD Navigation tuning
        self.Kp = 8.0   # Steering proportional gain
        self.Kd = 2.0   # Steering derivative gain (reduces oscillation)
        self.MAX_STEER = 400  # Max offset from center (1460-1040=420 max)
        self.prev_error = 0.0  # For derivative term
        
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
            self.nav_thread.join(timeout=2.0)
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
        """The core continuous autonomous loop with PD steering and speed from slider."""
        print("[NAV] Entering Continuous OUTDOOR Loop...")
        self.prev_error = 0.0
        
        while self.running and self.mode == "OUTDOOR":
            gps = self.sensors.get_filtered_gps()
            heading = self.sensors.get_heading()
            obstacle_dist = self.sensors.ultrasonic.get_distance()

            # Priority 1: Obstacle Avoidance
            if obstacle_dist < 40.0:
                print(f"[NAV] OBSTACLE DETECTED at {obstacle_dist}cm! Engaging Avoidance.")
                self.motor.avoid_obstacle()
                self.prev_error = 0.0
                continue
                
            # Priority 2: Navigation Target
            if not self.waypoints or self.current_wp_index >= len(self.waypoints):
                print("[NAV] Destination Reached or No Waypoints. Halting.")
                self.stop()
                break

            current_wp = self.waypoints[self.current_wp_index]
            dist = haversine(gps["lat"], gps["lon"], current_wp["lat"], current_wp["lon"])

            # RANGE-BASED TRIGGER
            if dist < current_wp["radius"]:
                print(f"[NAV] Entered WP Zone {self.current_wp_index} (Dist: {dist:.1f}m). Action: {current_wp['action']}")
                if self.current_wp_index < len(self.waypoints) - 1:
                    next_wp = self.waypoints[self.current_wp_index + 1]
                    target_bearing = calculate_bearing(gps["lat"], gps["lon"], next_wp["lat"], next_wp["lon"])
                else:
                    target_bearing = calculate_bearing(gps["lat"], gps["lon"], current_wp["lat"], current_wp["lon"])
                self.current_wp_index += 1
            else:
                target_bearing = calculate_bearing(gps["lat"], gps["lon"], current_wp["lat"], current_wp["lon"])

            # PD Error computation
            error = normalize_angle(target_bearing - heading)
            derivative = error - self.prev_error
            self.prev_error = error
            
            # Continuous Steering: PD control
            steering = self.Kp * error + self.Kd * derivative
            steering = max(min(steering, self.MAX_STEER), -self.MAX_STEER)
            
            pulse = int(self.motor.SERVO_CENTER + steering)
            
            # Speed: use slider max_speed, reduce near waypoints
            drive_speed = self.max_speed
            if dist < 5.0:  # Within 5m of waypoint, slow down
                drive_speed = int(self.max_speed * 0.6)
            
            self.motor.move_forward(pulse, drive_speed)
            
            # Loop delay for stable CPU tracking (20Hz)
            time.sleep(0.05)
    # ================================================================
    #  INDOOR AUTONOMOUS — Robotic Vacuum-Style Navigation
    # ================================================================
    #  Architecture:
    #    1. Sensor Read   → get_averaged_distance() + get_heading()
    #    2. Perception    → classify_environment()
    #    3. Decision      → wall-follow / evade / explore
    #    4. Motion        → heading-corrected drive with PWM ramping
    # ================================================================

    def indoor_main_loop(self):
        """
        Full indoor autonomous navigation loop.
        
        Strategy:
          - Drive forward using heading correction (magnetometer keeps line straight)
          - Slow down in CAUTION zone (20-30cm)
          - On FRONT_BLOCKED (<20cm): stop → reverse → LEFT-hand-rule evasion
          - If LEFT blocked → try RIGHT → alternate until clear
          - After 6 failed evasion attempts → long reverse (unstuck recovery)
          - Dead reckoning: track approximate position via heading + time
        """
        print("=" * 60)
        print("[NAV] INDOOR AUTONOMOUS — Initializing...")
        print("=" * 60)

        # ---- Capture Reference Heading ----
        # Lock the initial heading as "forward" direction
        initial_heading = self.sensors.get_heading()
        target_heading = initial_heading
        print(f"[NAV] Reference heading locked: {initial_heading:.1f}°")

        # ---- Dead Reckoning State ----
        travel_time = 0.0  # Approximate seconds of forward motion

        # ---- Evasion State ----
        last_turn_dir = "LEFT"  # Wall-following: prefer LEFT first

        # ---- Phase 1: Gradual Speed Ramp-up ----
        print(f"[NAV] Ramping speed to {self.max_speed}%...")
        self.motor.ramp_speed(self.max_speed, duration=3.0)

        # ---- Phase 2: Main Navigation Loop (20Hz) ----
        loop_dt = 0.05  # 50ms = 20Hz
        
        while self.running and self.mode == "INDOOR":
            loop_start = time.time()

            # ========== 1. SENSOR READ ==========
            distance = self.sensors.get_averaged_distance()
            heading = self.sensors.get_heading()

            # ========== 2. PERCEPTION ==========
            env = self.sensors.classify_environment(distance)

            # ========== 3. DECISION + MOTION ==========

            if env == "FRONT_BLOCKED":
                # ---- OBSTACLE — Stop + Smart Evasion ----
                print(f"[NAV] ⛔ FRONT_BLOCKED at {distance:.1f}cm! Stopping...")
                self.motor.stop()
                time.sleep(0.3)

                # Step A: Reverse away from obstacle
                self.motor.set_state("REVERSE", self.max_speed)
                time.sleep(1.0)
                self.motor.stop()
                time.sleep(0.3)

                # Step B: Smart evasion — LEFT-hand rule with alternation
                evasion_success = self._evasion_search(last_turn_dir)

                if evasion_success:
                    # Update target heading to new direction after evasion
                    target_heading = self.sensors.get_heading()
                    print(f"[NAV] New target heading: {target_heading:.1f}°")

                # Step C: Re-ramp to cruise speed
                if self.running and self.mode == "INDOOR":
                    print(f"[NAV] Re-ramping to {self.max_speed}%...")
                    self.motor.ramp_speed(self.max_speed, duration=2.0)

            elif env == "CAUTION":
                # ---- SLOWDOWN ZONE (20-30cm) ----
                scale = (distance - 20.0) / 10.0  # 1.0 at 30cm → 0.0 at 20cm
                slow_speed = max(10, int(self.max_speed * scale))
                
                # Heading correction even while slowing
                self._heading_correct(heading, target_heading, slow_speed)

            else:
                # ---- OPEN PATH — Full speed with heading correction ----
                self._heading_correct(heading, target_heading, self.max_speed)
                travel_time += loop_dt  # Dead reckoning accumulation

            # ========== 4. LOOP TIMING ==========
            elapsed = time.time() - loop_start
            sleep_time = max(0, loop_dt - elapsed)
            time.sleep(sleep_time)

        # ---- Clean Exit ----
        self.motor.stop()
        print(f"[NAV] INDOOR loop ended. Approx travel time: {travel_time:.1f}s")
        print("=" * 60)

    # ================================================================
    #  Heading Correction — Keep Robot Driving Straight
    # ================================================================
    def _heading_correct(self, current_heading, target_heading, speed):
        """
        Use magnetometer heading to correct steering drift.
        If the car drifts left of target → steer slightly right, and vice versa.
        This keeps the robot driving in a straight line without gyro drift.
        """
        error = normalize_angle(target_heading - current_heading)

        # Proportional steering correction
        # Small Kp: gentle correction. Large → aggressive snapping.
        heading_Kp = 3.0
        correction = heading_Kp * error
        correction = max(min(correction, 200), -200)  # Clamp servo offset

        pulse = int(self.motor.SERVO_CENTER + correction)
        self.motor.set_steering(pulse)
        self.motor.set_state("FORWARD", speed)

    # ================================================================
    #  Smart Evasion Search — Wall-Following with Direction Alternation
    # ================================================================
    def _evasion_search(self, preferred_dir="LEFT"):
        """
        Multi-attempt evasion:
          1. Try preferred direction (LEFT by default — left-hand rule)
          2. If still blocked → flip to opposite direction
          3. Keep alternating until clear (max 6 attempts)
          4. If stuck after 6 attempts → long reverse (recovery mode)
          
        Returns True if clear path found, False if gave up.
        """
        # Set initial turn direction
        if preferred_dir == "LEFT":
            turn_servo = self.motor.SERVO_LEFT
            turn_name = "LEFT"
        else:
            turn_servo = self.motor.SERVO_RIGHT
            turn_name = "RIGHT"

        attempt = 0

        while self.running and self.mode == "INDOOR":
            attempt += 1
            print(f"[NAV] Evasion #{attempt}: turning {turn_name}...")

            # Turn servo to direction and drive forward for 2s
            self.motor.set_steering(turn_servo)
            time.sleep(0.3)
            self.motor.set_state("FORWARD", self.max_speed)
            time.sleep(2.0)
            self.motor.stop()
            time.sleep(0.2)

            # Center steering and check if path is now clear
            self.motor.set_steering(self.motor.SERVO_CENTER)
            time.sleep(0.2)
            check_dist = self.sensors.get_averaged_distance()

            if check_dist > 30.0:
                print(f"[NAV] ✅ Path CLEAR at {check_dist:.1f}cm after {turn_name}!")
                return True

            # Still blocked — back up and try opposite direction
            print(f"[NAV] ❌ Still blocked at {check_dist:.1f}cm. Flipping direction...")
            self.motor.stop()
            time.sleep(0.2)
            self.motor.set_state("REVERSE", self.max_speed)
            time.sleep(0.8)
            self.motor.stop()
            time.sleep(0.2)

            # Flip direction
            if turn_servo == self.motor.SERVO_LEFT:
                turn_servo = self.motor.SERVO_RIGHT
                turn_name = "RIGHT"
            else:
                turn_servo = self.motor.SERVO_LEFT
                turn_name = "LEFT"

            # Recovery: after 6 failed attempts, long reverse
            if attempt >= 6:
                print("[NAV] ⚠️ Stuck! Emergency long reverse...")
                self.motor.set_state("REVERSE", self.max_speed)
                time.sleep(3.0)
                self.motor.stop()
                time.sleep(0.5)
                attempt = 0  # Reset and try again

        return False

    # ================================================================
    #  Manual Mode — Direct Joystick Control (No sensor override)
    # ================================================================
    def manual_joystick(self, x, y):
        if self.mode == "MANUAL":
            self.motor.execute_joystick(x, y)
