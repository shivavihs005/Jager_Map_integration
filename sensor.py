import time
import threading
import math
import pynmea2
import serial
from map_matcher import map_matcher

try:
    from smbus2 import SMBus
    SMBUS_AVAILABLE = True
except ImportError:
    SMBUS_AVAILABLE = False
    print("smbus2 not found. IMU will run in mock mode.")

class SensorSystem:
    def __init__(self, port='/dev/serial0', baudrate=9600):
        self.lock = threading.Lock()
        
        # GPS State
        self.lat = 0.0
        self.lng = 0.0
        self.gps_heading = 0.0
        self.speed_kmh = 0.0
        self.has_fix = False
        
        # IMU State
        self.current_yaw = 0.0  # Integrated yaw
        self.last_imu_time = 0
        
        self.gps_running = False
        self.imu_running = False
        self.gps_thread = None
        self.imu_thread = None
        
        self.gps_port = port
        self.gps_baudrate = baudrate
        
        # MPU-6500 configuration
        self.i2c_bus = 1
        self.mpu_address = 0x68
        self.bus = None
        if SMBUS_AVAILABLE:
            try:
                self.bus = SMBus(self.i2c_bus)
                self.bus.write_byte_data(self.mpu_address, 0x6B, 0) # Wake up
                self.bus.write_byte_data(self.mpu_address, 0x1B, 0x00) # Gyro full scale range +/- 250 deg/s
                print("MPU-6500 Initialized")
            except Exception as e:
                print(f"Error initializing MPU-6500: {e}")
                self.bus = None

    def start(self):
        if not self.gps_running:
            self.gps_running = True
            self.gps_thread = threading.Thread(target=self._gps_loop, daemon=True)
            self.gps_thread.start()
            
        if not self.imu_running:
            self.imu_running = True
            self.imu_thread = threading.Thread(target=self._imu_loop, daemon=True)
            self.imu_thread.start()

    def stop(self):
        self.gps_running = False
        self.imu_running = False
        if self.gps_thread: self.gps_thread.join()
        if self.imu_thread: self.imu_thread.join()

    def _read_gyro_z(self):
        if not self.bus:
            return 0.0
        try:
            high = self.bus.read_byte_data(self.mpu_address, 0x47)
            low = self.bus.read_byte_data(self.mpu_address, 0x48)
            val = (high << 8) | low
            if val > 32767:
                val -= 65536
            # Scale factor for +/- 250 deg/s is 131.0
            return val / 131.0
        except Exception:
            return 0.0

    def _imu_loop(self):
        print("IMU Loop Started")
        self.last_imu_time = time.time()
        while self.imu_running:
            now = time.time()
            dt = now - self.last_imu_time
            self.last_imu_time = now
            
            gz = self._read_gyro_z()
            
            # Simple thresholding to reduce stationary drift
            if abs(gz) < 1.0: # Deg/s threshold
                gz = 0.0
                
            with self.lock:
                self.current_yaw += gz * dt
                if self.current_yaw > 180:
                    self.current_yaw -= 360
                elif self.current_yaw < -180:
                    self.current_yaw += 360
                    
            time.sleep(0.02) # ~50Hz

    def _gps_loop(self):
        print("GPS Loop Started")
        try:
            ser = serial.Serial(self.gps_port, self.gps_baudrate, timeout=1)
        except Exception as e:
            print(f"Error connecting to GPS: {e}")
            return

        while self.gps_running:
            try:
                line = ser.readline().decode('utf-8', errors='ignore')
                if line.startswith('$GPGGA') or line.startswith('$GNGGA'):
                    try:
                        msg = pynmea2.parse(line)
                        if msg.latitude and msg.longitude:
                            lat = msg.latitude
                            lng = msg.longitude
                            snapped = map_matcher.match_to_road(lat, lng)
                            if snapped: lat, lng = snapped
                            with self.lock:
                                self.lat = lat
                                self.lng = lng
                                self.has_fix = True
                    except pynmea2.ParseError:
                        pass
                elif line.startswith('$GPRMC') or line.startswith('$GNRMC'):
                    try:
                        msg = pynmea2.parse(line)
                        if msg.latitude and msg.longitude:
                             lat = msg.latitude
                             lng = msg.longitude
                             snapped = map_matcher.match_to_road(lat, lng)
                             if snapped: lat, lng = snapped
                             with self.lock:
                                 self.lat = lat
                                 self.lng = lng
                                 self.has_fix = True
                        
                        speed_knots = 0.0
                        if hasattr(msg, 'spd_over_grnd') and msg.spd_over_grnd is not None:
                             speed_knots = float(msg.spd_over_grnd)
                             with self.lock:
                                 self.speed_kmh = speed_knots * 1.852
                        
                        if hasattr(msg, 'true_course') and msg.true_course is not None:
                            heading = float(msg.true_course)
                            if speed_knots > 0.5: # 0.5 knot threshold to avoid stopped spin
                                with self.lock:
                                    self.gps_heading = heading
                    except pynmea2.ParseError:
                        pass
            except Exception as e:
                time.sleep(1)

    def reset_yaw(self):
        with self.lock:
            self.current_yaw = 0.0

    def get_data(self):
        with self.lock:
            return {
                'lat': self.lat,
                'lng': self.lng,
                'current_yaw': self.current_yaw,
                'gps_heading': self.gps_heading,
                'speed': self.speed_kmh,
                'has_fix': self.has_fix
            }

sensor_system = SensorSystem()
