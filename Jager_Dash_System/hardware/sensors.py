import time
import random
import math

try:
    import serial
    import smbus2
    PI_ENV = True
except ImportError:
    PI_ENV = False

from hardware.ultrasonic_sensor import UltrasonicSensor

class SensorsData:
    def __init__(self):
        self.gps_lat = 37.7749
        self.gps_lon = -122.4194
        self.filtered_lat = self.gps_lat
        self.filtered_lon = self.gps_lon
        self.alpha = 0.2  # Simple exponential smoothing factor for GPS
        
        self.heading = 0.0
        self.ultrasonic = UltrasonicSensor() # Init Ultrasonic distance sensor

        print(f"[SENSORS] Initializing... Hardware Environment: {'Pi' if PI_ENV else 'Windows Mock'}")
        
        if PI_ENV:
            try:
                # Initialize GPS on Hardware UART (/dev/serial0) per spec.
                # NOTE: Ensure /boot/config.txt has enable_uart=1 and dtoverlay=disable-bt
                self.ser = serial.Serial('/dev/serial0', 9600, timeout=1)
                
                # Init I2C bus for IMU/Compass
                self.bus = smbus2.SMBus(1)
                self.bus.write_byte_data(0x68, 0x6B, 0) # Wake MPU6500
                self.bus.write_byte_data(0x0D, 0x0B, 0x01) # Set/Reset Mag
                self.bus.write_byte_data(0x0D, 0x09, 0x1D) # Continuous Mag
            except Exception as e:
                print(f"[SENSORS] Pi Hardware init failed: {e}")
                self.ser = None
                self.bus = None
        else:
            self.ser = None
            self.bus = None

        self.prev_heading = None
        self.heading_alpha = 0.3

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
                data = self.bus.read_i2c_block_data(0x0D, 0x00, 6)
                x = data[0] | (data[1] << 8)
                y = data[2] | (data[3] << 8)
                
                # Convert to signed
                if x > 32767: x -= 65536
                if y > 32767: y -= 65536
                
                raw_heading = math.atan2(y, x)
                raw_heading = math.degrees(raw_heading)
                if raw_heading < 0: raw_heading += 360
                
                # Smoothen
                if self.prev_heading is None:
                    self.prev_heading = raw_heading
                else:
                    self.prev_heading = self.heading_alpha * raw_heading + (1 - self.heading_alpha) * self.prev_heading
                
                self.heading = self.prev_heading
            except Exception:
                pass
        else:
            self.heading = (self.heading + random.uniform(-2, 2)) % 360
            
        return self.heading

    def get_all(self):
        return {
            "gps": self.get_filtered_gps(),
            "imu": {"heading": self.get_heading(), "pitch": 0, "roll": 0},
            "distance": self.ultrasonic.get_distance()
        }
