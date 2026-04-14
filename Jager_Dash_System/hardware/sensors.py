import random
import time

class SensorsData:
    """Mock sensors class for Windows testing."""
    def __init__(self):
        print("[MOCK SENSORS] Sensors Initialized")
        
        # Internal state to mock some realistic changes
        self.mock_lat = 37.7749
        self.mock_lon = -122.4194
        
    def calibrate(self):
        print("[MOCK SENSORS] Calibrating sensors... ", end="")
        time.sleep(1)
        print("Done.")
        return True

    def get_gps(self):
        """Mock GPS reading (returns roughly San Francisco coordinates with drift)"""
        self.mock_lat += random.uniform(-0.0001, 0.0001)
        self.mock_lon += random.uniform(-0.0001, 0.0001)
        return {
            "lat": self.mock_lat,
            "lon": self.mock_lon,
            "locked": True
        }

    def get_imu(self):
        """Mock IMU data"""
        return {
            "heading": random.uniform(0, 360),
            "pitch": random.uniform(-5, 5),
            "roll": random.uniform(-5, 5)
        }

    def get_distance(self):
        """Mock SDM15 distance sensor (cm)"""
        # Return a value between 20cm and 200cm
        return round(random.uniform(20.0, 200.0), 2)
        
    def get_all(self):
        return {
            "gps": self.get_gps(),
            "imu": self.get_imu(),
            "distance_cm": self.get_distance()
        }
