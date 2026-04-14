import threading
import time
import requests

from hardware.motor_controller import MotorController
from hardware.sensors import SensorsData

class StateMachine:
    def __init__(self):
        self.mode = "STOP" # OUTDOOR, INDOOR, MANUAL, STOP
        self.running = False
        self.thread = None
        
        self.motor = MotorController()
        self.sensors = SensorsData()
        
        self.waypoints = []
        self.current_waypoint_idx = 0
        
    def start(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._run_loop, daemon=True)
            self.thread.start()
            print("[STATE MACHINE] Loop started.")

    def stop(self):
        self.running = False
        self.mode = "STOP"
        self.motor.stop()
        if self.thread:
            self.thread.join()
            print("[STATE MACHINE] Loop stopped.")

    def set_mode(self, mode):
        self.mode = mode
        if mode == "STOP":
            self.motor.stop()
        print(f"[STATE MACHINE] Mode set to: {mode}")

    def fetch_osrm_route(self, lat1, lon1, lat2, lon2):
        """Fetch A* route from OSRM given start and end."""
        # Note: In real world, use your actual OSMR server IP or the public one.
        url = f"http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=full&geometries=geojson"
        try:
            r = requests.get(url, timeout=5)
            data = r.json()
            if data['code'] == 'Ok':
                coords = data['routes'][0]['geometry']['coordinates']
                # Convert coords to waypoints [[lat, lon], ...]
                self.waypoints = [[c[1], c[0]] for c in coords]
                self.current_waypoint_idx = 0
                return self.waypoints
            else:
                print("[STATE MACHINE] OSRM Route Failed")
                return None
        except Exception as e:
            print(f"[STATE MACHINE] Route fetch error: {e}")
            return None

    def manual_joystick(self, x, y):
        """Called by API when in manual mode."""
        if self.mode == "MANUAL":
            self.motor.execute_joystick(x, y)

    def _run_loop(self):
        """Main logical execution loop running continuously."""
        while self.running:
            sensor_data = self.sensors.get_all()
            dist = sensor_data["distance_cm"]
            
            if self.mode == "OUTDOOR":
                # Obstacle detection priority
                if dist < 40:
                    print(f"[OUTDOOR] OBSTACLE! {dist}cm -> STOP")
                    self.motor.stop()
                else:
                    # Mock outdoor logic
                    # If we have waypoints, drive logic
                    if self.waypoints and self.current_waypoint_idx < len(self.waypoints):
                        self.motor.set_state("FORWARD", 60)
                        # Simulate reaching a waypoint every 2 seconds
                        time.sleep(2)
                        self.current_waypoint_idx += 1
                        print(f"[OUTDOOR] Reached WP {self.current_waypoint_idx}/{len(self.waypoints)}")
                    else:
                        print("[OUTDOOR] No waypoints or arrived at destination.")
                        self.mode = "STOP"
                        self.motor.stop()
                        
            elif self.mode == "INDOOR":
                # Indoor camera/sensor logic
                if dist < 30:
                    print(f"[INDOOR] Object near -> Avoidance")
                    self.motor.set_state("REVERSE", 50)
                    time.sleep(1)
                    self.motor.set_state("TURN_LEFT", 60)
                    time.sleep(0.5)
                else:
                    self.motor.set_state("FORWARD", 50)
            
            # If MANUAL, joystick handles state directly, no loop logic needed here.

            time.sleep(0.1) # Loop rate ~10Hz
