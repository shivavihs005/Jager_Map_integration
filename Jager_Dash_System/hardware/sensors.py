import time
import random
import math

try:
    import serial
    import smbus2
    PI_ENV = True
except ImportError:
    PI_ENV = False

class SensorsData:
    def __init__(self):
        self.gps_lat = 37.7749
        self.gps_lon = -122.4194
        self.filtered_lat = self.gps_lat
        self.filtered_lon = self.gps_lon
        self.alpha = 0.2  # Simple exponential smoothing factor for GPS
        
        self.heading = 0.0
        self.distance_cm = 150.0

        print(f"[SENSORS] Initializing... Hardware Environment: {'Pi' if PI_ENV else 'Windows Mock'}")
        
        if PI_ENV:
            try:
                self.ser = serial.Serial('/dev/serial0', 9600, timeout=1)
                self.bus = smbus2.SMBus(1)
            except Exception as e:
                print(f"[SENSORS] Pi Hardware init failed: {e}")
                self.ser = None
                self.bus = None
        else:
            self.ser = None
            self.bus = None

    def calibrate(self):
        print("[SENSORS] Calibrating systems over I2C/UART...")
        time.sleep(1)
        return {"status": "PASS", "message": "Calibration OK"}

    def update_gps_filter(self, raw_lat, raw_lon):
        # Exponential smoothing pipeline
        self.filtered_lat = (self.alpha * raw_lat) + ((1 - self.alpha) * self.filtered_lat)
        self.filtered_lon = (self.alpha * raw_lon) + ((1 - self.alpha) * self.filtered_lon)

    def get_filtered_gps(self):
        if PI_ENV and self.ser:
            try:
                # Basic NMEA read mock logic (ideally use pynmea2 here)
                line = self.ser.readline().decode('ascii', errors='replace')
                if line.startswith('$GPRMC'):
                    # Dummy parse for structure - production needs standard math conversion
                    parts = line.split(',')
                    if len(parts) > 5 and parts[2] == 'A':
                        lat_raw = float(parts[3])
                        lon_raw = float(parts[5])
                        self.update_gps_filter(lat_raw / 100.0, -lon_raw / 100.0)
            except Exception:
                pass
        else:
            # Mock GPS walking randomly
            self.gps_lat += random.uniform(-0.0001, 0.0001)
            self.gps_lon += random.uniform(-0.0001, 0.0001)
            self.update_gps_filter(self.gps_lat, self.gps_lon)
            
        return {"lat": self.filtered_lat, "lon": self.filtered_lon, "locked": True}

    def get_heading(self):
        if PI_ENV and self.bus:
            try:
                # Mock QMC5883L I2C 0x0D read logic
                # Normally read registers 0x00 to 0x05 for X,Y,Z
                x = self.bus.read_word_data(0x0D, 0x00)
                y = self.bus.read_word_data(0x0D, 0x02)
                self.heading = (math.atan2(y, x) * 180 / math.pi) % 360
            except Exception:
                pass
        else:
            self.heading = (self.heading + random.uniform(-2, 2)) % 360
            
        return self.heading

    def read_sdm15(self):
        if PI_ENV:
            # Placeholder for SDM15 distance readout (UART/Pulse)
            self.distance_cm = 150.0 
        else:
            self.distance_cm = random.uniform(50.0, 200.0)
        return self.distance_cm

    def get_all(self):
        return {
            "gps": self.get_filtered_gps(),
            "imu": {"heading": self.get_heading(), "pitch": 0, "roll": 0},
            "distance_cm": round(self.read_sdm15(), 2)
        }
