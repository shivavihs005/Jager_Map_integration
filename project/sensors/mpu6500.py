"""
mpu6500.py — Read accelerometer and gyroscope values, calculate simple pitch/roll
"""
import time
import math
import threading

try:
    from smbus2 import SMBus
except ImportError:
    try:
        from smbus import SMBus
    except ImportError:
        SMBus = None

MPU_ADDR = 0x68
PWR_MGMT_1 = 0x6B
GYRO_CONFIG = 0x1B
ACCEL_CONFIG = 0x1C
ACCEL_XOUT_H = 0x3B
GYRO_XOUT_H = 0x43

ACCEL_SCALE = 16384.0   # ±2g
GYRO_SCALE = 131.0      # ±250°/s

class MPU6500:
    def __init__(self, bus_num=1):
        self._lock = threading.Lock()
        
        self.acc_x = 0.0
        self.acc_y = 0.0
        self.acc_z = 0.0
        self.gyro_x = 0.0
        self.gyro_y = 0.0
        self.gyro_z = 0.0

        self.pitch = 0.0
        self.roll = 0.0

        if SMBus is None:
            print("[MPU6500] No SMBus found. Running in mock mode.")
            self.mock_mode = True
            return

        try:
            self.bus = SMBus(bus_num)
            self.bus.write_byte_data(MPU_ADDR, PWR_MGMT_1, 0x00)
            time.sleep(0.1)
            self.bus.write_byte_data(MPU_ADDR, GYRO_CONFIG, 0x00)
            self.bus.write_byte_data(MPU_ADDR, ACCEL_CONFIG, 0x00)
            self.mock_mode = False
            print("[MPU6500] Initialized successfully.")
        except Exception as e:
            print(f"[MPU6500] Init failed: {e}. Running in mock mode.")
            self.bus = None
            self.mock_mode = True

    def _read_word(self, reg):
        try:
            high = self.bus.read_byte_data(MPU_ADDR, reg)
            low = self.bus.read_byte_data(MPU_ADDR, reg + 1)
            val = (high << 8) | low
            if val > 32767:
                val -= 65536
            return val
        except Exception:
            return 0

    def update(self):
        if self.mock_mode:
            return

        with self._lock:
            self.acc_x = self._read_word(ACCEL_XOUT_H) / ACCEL_SCALE
            self.acc_y = self._read_word(ACCEL_XOUT_H + 2) / ACCEL_SCALE
            self.acc_z = self._read_word(ACCEL_XOUT_H + 4) / ACCEL_SCALE

            self.gyro_x = self._read_word(GYRO_XOUT_H) / GYRO_SCALE
            self.gyro_y = self._read_word(GYRO_XOUT_H + 2) / GYRO_SCALE
            self.gyro_z = self._read_word(GYRO_XOUT_H + 4) / GYRO_SCALE

            # Basic pitch and roll calculation from accelerometer
            try:
                self.pitch = math.degrees(math.atan2(self.acc_x, math.sqrt(self.acc_y * self.acc_y + self.acc_z * self.acc_z)))
                self.roll = math.degrees(math.atan2(self.acc_y, math.sqrt(self.acc_x * self.acc_x + self.acc_z * self.acc_z)))
            except ZeroDivisionError:
                pass

    def get_data(self):
        with self._lock:
            return {
                "acc_x": self.acc_x,
                "acc_y": self.acc_y,
                "acc_z": self.acc_z,
                "gyro_x": self.gyro_x,
                "gyro_y": self.gyro_y,
                "gyro_z": self.gyro_z,
                "pitch": self.pitch,
                "roll": self.roll
            }
