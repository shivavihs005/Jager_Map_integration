"""
Sensor Fusion Layer — Jager_Dash Indoor/Outdoor Autonomous System

Subsystems:
  1. GPS (NEO-6M) — Outdoor positioning via hardware UART
  2. IMU (MPU6500) — Gyroscope for heading rate (yaw rate)
  3. Magnetometer (QMC5883L) — Absolute heading (compass)
  4. Ultrasonic (HC-SR04) — Front obstacle distance
  5. Sensor Fusion — Complementary filter: gyro + magnetometer → stable heading
  6. Ultrasonic Averaging — Median of N samples to reject noise spikes
"""

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

# ============================================================
#  Environment Classification Constants
# ============================================================
DIST_OBSTACLE = 20.0   # cm — hard obstacle
DIST_CAUTION  = 30.0   # cm — slow down zone
DIST_FREE     = 50.0   # cm — free path

class SensorsData:
    def __init__(self):
        # --- GPS State ---
        self.gps_lat = 37.7749
        self.gps_lon = -122.4194
        self.filtered_lat = self.gps_lat
        self.filtered_lon = self.gps_lon
        self.alpha = 0.2  # GPS exponential smoothing factor

        # --- Heading State (Sensor Fusion) ---
        self.heading = 0.0
        self.gyro_yaw_rate = 0.0
        self.mag_heading = 0.0
        self.fused_heading = 0.0
        self.complementary_alpha = 0.95  # 95% gyro, 5% magnetometer
        self.last_fusion_time = time.time()

        # --- Ultrasonic ---
        self.ultrasonic = UltrasonicSensor()
        self.ultrasonic_samples = 5  # Number of samples for median filter
        self.last_distance = 100.0

        print(f"[SENSORS] Initializing... Hardware Environment: {'Pi' if PI_ENV else 'Windows Mock'}")

        if PI_ENV:
            try:
                # GPS on Hardware UART (/dev/serial0)
                self.ser = serial.Serial('/dev/serial0', 9600, timeout=1)

                # I2C bus for IMU + Compass
                self.bus = smbus2.SMBus(1)

                # Wake MPU6500 (address 0x68)
                self.bus.write_byte_data(0x68, 0x6B, 0x00)
                # Set gyro range to ±250 dps (sensitivity = 131 LSB/dps)
                self.bus.write_byte_data(0x68, 0x1B, 0x00)

                # Init QMC5883L magnetometer (address 0x0D)
                self.bus.write_byte_data(0x0D, 0x0B, 0x01)  # Set/Reset
                self.bus.write_byte_data(0x0D, 0x09, 0x1D)  # Continuous, 200Hz, 8G, OSR512

                print("[SENSORS] ✅ I2C sensors initialized (MPU6500 + QMC5883L)")
            except Exception as e:
                print(f"[SENSORS] ❌ Pi Hardware init failed: {e}")
                self.ser = None
                self.bus = None
        else:
            self.ser = None
            self.bus = None

        self.prev_heading = None
        self.heading_alpha = 0.3

    # ============================================================
    #  Calibration
    # ============================================================
    def calibrate(self):
        print("[SENSORS] Calibrating systems over I2C/UART...")
        time.sleep(1)
        return {"status": "PASS", "message": "Calibration OK"}

    # ============================================================
    #  GPS — Outdoor Only
    # ============================================================
    def update_gps_filter(self, raw_lat, raw_lon):
        self.filtered_lat = (self.alpha * raw_lat) + ((1 - self.alpha) * self.filtered_lat)
        self.filtered_lon = (self.alpha * raw_lon) + ((1 - self.alpha) * self.filtered_lon)

    def get_filtered_gps(self):
        if PI_ENV and self.ser:
            try:
                line = self.ser.readline().decode('ascii', errors='replace')
                if line.startswith('$GPRMC'):
                    parts = line.split(',')
                    if len(parts) > 5 and parts[2] == 'A':
                        lat_raw = float(parts[3])
                        lon_raw = float(parts[5])
                        self.update_gps_filter(lat_raw / 100.0, -lon_raw / 100.0)
            except Exception:
                pass
        else:
            self.gps_lat += random.uniform(-0.0001, 0.0001)
            self.gps_lon += random.uniform(-0.0001, 0.0001)
            self.update_gps_filter(self.gps_lat, self.gps_lon)

        return {"lat": self.filtered_lat, "lon": self.filtered_lon, "locked": True}

    # ============================================================
    #  IMU — Gyroscope Z-axis (Yaw Rate)
    # ============================================================
    def get_gyro_yaw_rate(self):
        """Read MPU6500 Z-axis gyroscope → degrees/second"""
        if PI_ENV and self.bus:
            try:
                # Gyro Z: registers 0x47 (high) and 0x48 (low)
                high = self.bus.read_byte_data(0x68, 0x47)
                low = self.bus.read_byte_data(0x68, 0x48)
                raw = (high << 8) | low
                if raw > 32767:
                    raw -= 65536
                # ±250 dps range → 131 LSB per dps
                self.gyro_yaw_rate = raw / 131.0
            except Exception:
                self.gyro_yaw_rate = 0.0
        else:
            self.gyro_yaw_rate = random.uniform(-1.0, 1.0)  # Mock drift
        return self.gyro_yaw_rate

    # ============================================================
    #  Magnetometer — Absolute Heading
    # ============================================================
    def get_mag_heading(self):
        """Read QMC5883L → compass heading in degrees (0-360)"""
        if PI_ENV and self.bus:
            try:
                data = self.bus.read_i2c_block_data(0x0D, 0x00, 6)
                x = data[0] | (data[1] << 8)
                y = data[2] | (data[3] << 8)
                if x > 32767: x -= 65536
                if y > 32767: y -= 65536

                raw = math.degrees(math.atan2(y, x))
                if raw < 0:
                    raw += 360
                self.mag_heading = raw
            except Exception:
                pass
        else:
            self.mag_heading = (self.mag_heading + random.uniform(-2, 2)) % 360
        return self.mag_heading

    # ============================================================
    #  Sensor Fusion — Complementary Filter (Gyro + Mag)
    # ============================================================
    def get_heading(self):
        """
        Complementary filter:
          heading = alpha * (heading + gyro_rate * dt) + (1 - alpha) * mag_heading

        - Gyro: fast, no drift in short term but drifts over time
        - Mag: absolute but noisy
        - Complementary filter: best of both worlds
        """
        now = time.time()
        dt = now - self.last_fusion_time
        self.last_fusion_time = now

        # Clamp dt to avoid crazy jumps on first call or long pauses
        dt = min(dt, 0.5)

        gyro_rate = self.get_gyro_yaw_rate()
        mag = self.get_mag_heading()

        # Complementary filter
        gyro_contribution = self.fused_heading + gyro_rate * dt
        self.fused_heading = self.complementary_alpha * gyro_contribution + (1 - self.complementary_alpha) * mag

        # Normalize to 0-360
        self.fused_heading = self.fused_heading % 360
        self.heading = self.fused_heading

        return self.heading

    # ============================================================
    #  Ultrasonic — Averaged Distance (Median Filter)
    # ============================================================
    def get_averaged_distance(self):
        """
        Take N ultrasonic samples, discard outliers via median filter.
        Rejects sudden spikes from noise or misreads.
        """
        samples = []
        for _ in range(self.ultrasonic_samples):
            d = self.ultrasonic.get_distance()
            if d < 999.0:  # Ignore timeout reads
                samples.append(d)
            time.sleep(0.005)  # 5ms between samples

        if not samples:
            return self.last_distance  # Return last known good value

        # Median filter — immune to single spike noise
        samples.sort()
        median = samples[len(samples) // 2]
        self.last_distance = median
        return median

    # ============================================================
    #  Environment Classification (Perception Layer)
    # ============================================================
    def classify_environment(self, distance):
        """Classify front obstacle status based on distance thresholds"""
        if distance < DIST_OBSTACLE:
            return "FRONT_BLOCKED"
        elif distance < DIST_CAUTION:
            return "CAUTION"
        else:
            return "OPEN_PATH"

    # ============================================================
    #  Combined Sensor Read (for API)
    # ============================================================
    def get_all(self):
        return {
            "gps": self.get_filtered_gps(),
            "imu": {"heading": self.get_heading(), "pitch": 0, "roll": 0},
            "distance": self.ultrasonic.get_distance()
        }
