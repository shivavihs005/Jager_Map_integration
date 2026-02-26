import time
import threading
import math
import pynmea2
import serial

try:
    from smbus2 import SMBus
    SMBUS_AVAILABLE = True
except ImportError:
    try:
        from smbus import SMBus
        SMBUS_AVAILABLE = True
    except ImportError:
        SMBUS_AVAILABLE = False
        print("smbus / smbus2 not found. IMU will run in mock mode.")

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
        self.velocity_x = 0.0   # Integrated speed from IMU
        self.last_imu_time = 0
        self.gyro_z_bias = 0.0
        self.filtered_accel_x = 0.0
        
        # Tuning Constants
        self.ALPHA_ACCEL = 0.1
        self.GYRO_DEADBAND = 1.0
        self.ACCEL_DEADBAND = 0.02
        self.GRAVITY_MS2 = 9.81
        self.GPS_WEIGHT = 0.02  # Complementary filter for heading
        self.GYRO_SCALE = 131.0
        self.ACCEL_SCALE = 16384.0
        
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
                # Range +/- 250 deg/s
                self.bus.write_byte_data(self.mpu_address, 0x1B, 0x00) 
                # Range +/- 2g
                self.bus.write_byte_data(self.mpu_address, 0x1C, 0x00)
                print("MPU-6500 Initialized")
                self._calibrate_gyro()
            except Exception as e:
                print(f"Error initializing MPU-6500: {e}")
                self.bus = None

    def _calibrate_gyro(self, samples=500):
        if not self.bus: return
        print("Calibrating gyro bias... Please keep the car completely still.")
        total_z = 0.0
        for _ in range(samples):
            gz = self._read_raw_data(0x43 + 4) / self.GYRO_SCALE
            total_z += gz
            time.sleep(0.005)
        self.gyro_z_bias = total_z / samples
        print(f"Calibration complete. Gyro Z-Bias: {self.gyro_z_bias:.4f} °/s")

    def _read_raw_data(self, addr):
        if not self.bus: return 0.0
        try:
            high = self.bus.read_byte_data(self.mpu_address, addr)
            low = self.bus.read_byte_data(self.mpu_address, addr+1)
            val = (high << 8) | low
            if val > 32767:
                val -= 65536
            return val
        except Exception:
            return 0.0

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

    def _imu_loop(self):
        print("IMU Loop Started")
        
        if not self.bus:
            print("No I2C Bus, terminating real IMU loop.")
            return
            
        self.last_imu_time = time.time()
        while self.imu_running:
            now = time.time()
            dt = now - self.last_imu_time
            self.last_imu_time = now
            
            # Read Raw Gyro & Accel
            raw_accel_x = self._read_raw_data(0x3B)
            raw_accel_z = self._read_raw_data(0x3B + 4)
            raw_gyro_z = self._read_raw_data(0x43 + 4)
            
            accel_x = raw_accel_x / self.ACCEL_SCALE
            accel_z = raw_accel_z / self.ACCEL_SCALE
            gyro_z = raw_gyro_z / self.GYRO_SCALE
            
            with self.lock:
                # 1. Orientation Update (Yaw)
                corrected_gyro_z = gyro_z - self.gyro_z_bias
                if abs(corrected_gyro_z) > self.GYRO_DEADBAND:
                    self.current_yaw += corrected_gyro_z * dt
                    
                # Normalize exactly between -180 and 180 degrees
                self.current_yaw = (self.current_yaw + 180) % 360 - 180
                
                # 2. Forward Velocity Tracking (X-Axis)
                # Pitch approximation to remove gravity artifact
                pitch = math.atan2(accel_x, accel_z) if accel_z != 0 else 0
                linear_accel_x = accel_x - math.sin(pitch)
                
                # Apply alpha dampening
                self.filtered_accel_x = (self.ALPHA_ACCEL * linear_accel_x) + ((1.0 - self.ALPHA_ACCEL) * self.filtered_accel_x)
                
                if abs(self.filtered_accel_x) > self.ACCEL_DEADBAND:
                    acceleration_ms2 = self.filtered_accel_x * self.GRAVITY_MS2
                    self.velocity_x += acceleration_ms2 * dt
                else:
                    self.velocity_x *= 0.95 # Rapid decay when stationary
                    
            time.sleep(0.01) # ~100Hz

    def _gps_loop(self):
        print("GPS Loop Started")
        try:
            ser = serial.Serial(self.gps_port, self.gps_baudrate, timeout=1)
        except Exception as e:
            print(f"Error connecting to GPS: {e}")
            return

        while self.gps_running:
            try:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                if not line:
                    continue
                    
                if line.startswith('$GPGGA') or line.startswith('$GNGGA'):
                    try:
                        msg = pynmea2.parse(line)
                        if getattr(msg, 'gps_qual', 0) > 0:
                            if hasattr(msg, 'latitude') and hasattr(msg, 'longitude'):
                                lat = msg.latitude
                                lng = msg.longitude
                                with self.lock:
                                    self.lat = lat
                                    self.lng = lng
                                    self.has_fix = True
                        else:
                            with self.lock:
                                self.has_fix = False
                    except pynmea2.ParseError:
                        pass
                elif line.startswith('$GPRMC') or line.startswith('$GNRMC'):
                    try:
                        msg = pynmea2.parse(line)
                        if getattr(msg, 'status', 'V') == 'A':
                            if hasattr(msg, 'latitude') and hasattr(msg, 'longitude'):
                                 lat = msg.latitude
                                 lng = msg.longitude
                                 with self.lock:
                                     self.lat = lat
                                     self.lng = lng
                                     self.has_fix = True
                            
                            speed_knots = 0.0
                            if hasattr(msg, 'spd_over_grnd') and getattr(msg, 'spd_over_grnd') is not None:
                                 speed_knots = float(msg.spd_over_grnd)
                                 with self.lock:
                                     self.speed_kmh = speed_knots * 1.852
                            
                            if hasattr(msg, 'true_course') and getattr(msg, 'true_course') is not None:
                                heading = float(msg.true_course)
                                if speed_knots > 0.5: # 0.5 knot threshold to avoid stopped spin
                                    with self.lock:
                                        self.gps_heading = heading
                                        # Complementary GPS Fusion for Yaw Stabilization
                                        self.current_yaw = (1 - self.GPS_WEIGHT) * self.current_yaw + self.GPS_WEIGHT * heading
                        else:
                            with self.lock:
                                self.has_fix = False
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
                'speed': max(self.speed_kmh, self.velocity_x * 3.6), # Return fastest derived reading (kmh)
                'has_fix': self.has_fix
            }

sensor_system = SensorSystem()
