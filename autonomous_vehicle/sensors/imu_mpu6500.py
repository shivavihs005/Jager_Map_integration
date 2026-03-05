"""
imu_mpu6500.py
MPU6500 driver: raw accelerometer, gyroscope, temperature.
"""
import time
import math

try:
    import smbus2
    SMBUS_AVAILABLE = True
except ImportError:
    SMBUS_AVAILABLE = False

from vehicle_config import MPU6500_ADDRESS

# ─── Register Map ────────────────────────────────────────────────────────────
REG_PWR_MGMT_1  = 0x6B
REG_ACCEL_XOUT  = 0x3B
REG_GYRO_XOUT   = 0x43
REG_TEMP_OUT    = 0x41
REG_CONFIG      = 0x1A
REG_GYRO_CFG    = 0x1B
REG_ACCEL_CFG   = 0x1C
REG_INT_ENABLE  = 0x38

ACCEL_SCALE = 16384.0   # ±2g  → LSB/g
GYRO_SCALE  = 131.0     # ±250 dps → LSB/(°/s)


class IMU_MPU6500:
    def __init__(self, bus_num=1):
        self._mock    = not SMBUS_AVAILABLE
        self._address = MPU6500_ADDRESS

        # Bias offsets (filled by calibrate())
        self.gyro_bias  = [0.0, 0.0, 0.0]
        self.accel_bias = [0.0, 0.0, 0.0]

        # Latest readings (SI units)
        self.accel = [0.0, 0.0, 0.0]   # m/s²
        self.gyro  = [0.0, 0.0, 0.0]   # rad/s
        self.temp  = 0.0                 # °C

        if not self._mock:
            self.bus = smbus2.SMBus(bus_num)
            self._init_chip()
        else:
            self.bus = None
            print("[IMU] smbus2 not found — mock mode")

    # ── Hardware init ────────────────────────────────────────────────────────
    def _init_chip(self):
        self.bus.write_byte_data(self._address, REG_PWR_MGMT_1, 0x00)  # Wake up
        time.sleep(0.1)
        self.bus.write_byte_data(self._address, REG_CONFIG,    0x03)    # DLPF 44 Hz
        self.bus.write_byte_data(self._address, REG_GYRO_CFG,  0x00)    # ±250 dps
        self.bus.write_byte_data(self._address, REG_ACCEL_CFG, 0x00)    # ±2g
        print("[IMU] MPU6500 initialised")

    # ── Low-level read ───────────────────────────────────────────────────────
    def _read_word(self, reg):
        high = self.bus.read_byte_data(self._address, reg)
        low  = self.bus.read_byte_data(self._address, reg + 1)
        val  = (high << 8) | low
        return val - 65536 if val >= 0x8000 else val

    def _read_word_mock(self):
        return 0

    # ── Calibration ──────────────────────────────────────────────────────────
    def calibrate(self, samples=200):
        """Collect bias at rest. Keep vehicle still for ~2 s."""
        print("[IMU] Calibrating — keep still…")
        ax_sum = ay_sum = az_sum = 0.0
        gx_sum = gy_sum = gz_sum = 0.0

        for _ in range(samples):
            self._read_raw()
            ax_sum += self.accel[0]
            ay_sum += self.accel[1]
            az_sum += self.accel[2]
            gx_sum += self.gyro[0]
            gy_sum += self.gyro[1]
            gz_sum += self.gyro[2]
            time.sleep(0.01)

        self.accel_bias = [ax_sum / samples,
                           ay_sum / samples,
                           (az_sum / samples) - 9.81]   # Remove gravity from Z
        self.gyro_bias  = [gx_sum / samples,
                           gy_sum / samples,
                           gz_sum / samples]
        print(f"[IMU] Gyro bias:  {[f'{b:.4f}' for b in self.gyro_bias]}")
        print(f"[IMU] Accel bias: {[f'{b:.4f}' for b in self.accel_bias]}")

    # ── Raw read ─────────────────────────────────────────────────────────────
    def _read_raw(self):
        if self._mock:
            self.accel = [0.0, 0.0, 9.81]
            self.gyro  = [0.0, 0.0, 0.0]
            self.temp  = 25.0
            return

        ax = self._read_word(REG_ACCEL_XOUT)     / ACCEL_SCALE * 9.81
        ay = self._read_word(REG_ACCEL_XOUT + 2) / ACCEL_SCALE * 9.81
        az = self._read_word(REG_ACCEL_XOUT + 4) / ACCEL_SCALE * 9.81

        gx = math.radians(self._read_word(REG_GYRO_XOUT)     / GYRO_SCALE)
        gy = math.radians(self._read_word(REG_GYRO_XOUT + 2) / GYRO_SCALE)
        gz = math.radians(self._read_word(REG_GYRO_XOUT + 4) / GYRO_SCALE)

        raw_temp = self._read_word(REG_TEMP_OUT)
        self.temp = raw_temp / 321.0 + 21.0

        self.accel = [ax, ay, az]
        self.gyro  = [gx, gy, gz]

    # ── Public API ───────────────────────────────────────────────────────────
    def update(self):
        """Read sensor and remove bias. Call at SENSOR_LOOP_HZ."""
        self._read_raw()
        self.accel = [self.accel[i] - self.accel_bias[i] for i in range(3)]
        self.gyro  = [self.gyro[i]  - self.gyro_bias[i]  for i in range(3)]

    def get_accel(self):
        return tuple(self.accel)

    def get_gyro(self):
        return tuple(self.gyro)

    def get_magnitude(self):
        a = self.accel
        return math.sqrt(a[0]**2 + a[1]**2 + a[2]**2)

    def get_data(self):
        return {
            "acc_x": self.accel[0], "acc_y": self.accel[1], "acc_z": self.accel[2],
            "gyro_x": math.degrees(self.gyro[0]),
            "gyro_y": math.degrees(self.gyro[1]),
            "gyro_z": math.degrees(self.gyro[2]),
            "temp": self.temp
        }
