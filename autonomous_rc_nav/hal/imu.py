import math
import threading
import time

from config import SENSORS

try:
    from smbus2 import SMBus
except ImportError:
    try:
        from smbus import SMBus
    except ImportError:
        SMBus = None


MPU_ADDR = 0x68
PWR_MGMT_1 = 0x6B
ACCEL_CONFIG = 0x1C
GYRO_CONFIG = 0x1B
ACCEL_XOUT_H = 0x3B
GYRO_XOUT_H = 0x43

ACCEL_SCALE = 4096.0
GYRO_SCALE = 131.0


class MPU6500:
    def __init__(self, bus_num=1):
        self._lock = threading.Lock()
        self.mock_mode = SMBus is None
        self.bus = None
        self.acc_x = 0.0
        self.acc_y = 0.0
        self.acc_z = 9.81
        self.gyro_x = 0.0
        self.gyro_y = 0.0
        self.gyro_z = 0.0
        self.temp_c = 26.0
        self.pitch = 0.0
        self.roll = 0.0
        self._mock_yaw_rate = 0.0

        if self.mock_mode:
            return

        try:
            self.bus = SMBus(bus_num)
            self.bus.write_byte_data(MPU_ADDR, PWR_MGMT_1, 0x00)
            time.sleep(0.1)
            self.bus.write_byte_data(MPU_ADDR, ACCEL_CONFIG, 0x10)
            self.bus.write_byte_data(MPU_ADDR, GYRO_CONFIG, 0x00)
        except Exception:
            self.mock_mode = True
            self.bus = None

    def _read_word(self, register):
        high = self.bus.read_byte_data(MPU_ADDR, register)
        low = self.bus.read_byte_data(MPU_ADDR, register + 1)
        value = (high << 8) | low
        if value > 32767:
            value -= 65536
        return value

    def set_mock_yaw_rate(self, yaw_rate_deg_s):
        with self._lock:
            self._mock_yaw_rate = yaw_rate_deg_s

    def update(self):
        with self._lock:
            if self.mock_mode:
                tick = time.time()
                self.acc_x = math.sin(tick * 0.8) * 0.05
                self.acc_y = math.cos(tick * 0.7) * 0.05
                self.acc_z = 9.81 + math.sin(tick * 0.3) * 0.08
                self.gyro_x = math.sin(tick * 0.5) * 0.05
                self.gyro_y = math.cos(tick * 0.4) * 0.05
                self.gyro_z = self._mock_yaw_rate
                self.temp_c = 26.0 + math.sin(tick * 0.2) * 0.3
            else:
                self.acc_x = (self._read_word(ACCEL_XOUT_H) / ACCEL_SCALE) * 9.81
                self.acc_y = (self._read_word(ACCEL_XOUT_H + 2) / ACCEL_SCALE) * 9.81
                self.acc_z = (self._read_word(ACCEL_XOUT_H + 4) / ACCEL_SCALE) * 9.81
                self.gyro_x = self._read_word(GYRO_XOUT_H) / GYRO_SCALE
                self.gyro_y = self._read_word(GYRO_XOUT_H + 2) / GYRO_SCALE
                self.gyro_z = self._read_word(GYRO_XOUT_H + 4) / GYRO_SCALE

            denom_pitch = math.sqrt((self.acc_y * self.acc_y) + (self.acc_z * self.acc_z))
            denom_roll = math.sqrt((self.acc_x * self.acc_x) + (self.acc_z * self.acc_z))
            if denom_pitch:
                self.pitch = math.degrees(math.atan2(self.acc_x, denom_pitch))
            if denom_roll:
                self.roll = math.degrees(math.atan2(self.acc_y, denom_roll))

    def get_data(self):
        with self._lock:
            return {
                "acc_x": self.acc_x,
                "acc_y": self.acc_y,
                "acc_z": self.acc_z,
                "gyro_x": self.gyro_x,
                "gyro_y": self.gyro_y,
                "gyro_z": self.gyro_z,
                "temp_c": self.temp_c,
                "pitch": self.pitch,
                "roll": self.roll,
                "sample_hz": SENSORS.imu_hz,
                "mock_mode": self.mock_mode,
            }