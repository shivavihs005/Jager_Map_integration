"""
magnetometer_qmc5883l.py
QMC5883L magnetometer driver — heading output in degrees.
"""
import time
import math

try:
    import smbus2
    SMBUS_AVAILABLE = True
except ImportError:
    SMBUS_AVAILABLE = False

from vehicle_config import QMC5883L_ADDRESS

# ─── Registers ───────────────────────────────────────────────────────────────
REG_X_LSB     = 0x00
REG_STATUS    = 0x06
REG_CONTROL1  = 0x09
REG_CONTROL2  = 0x0A
REG_PERIOD    = 0x0B

MODE_CONTINUOUS = 0x01
ODR_200Hz       = 0b11 << 2
RNG_8G          = 0b01 << 4
OSR_512         = 0b00 << 6
CTRL1_DEFAULT   = MODE_CONTINUOUS | ODR_200Hz | RNG_8G | OSR_512


class Magnetometer_QMC5883L:
    def __init__(self, bus_num=1):
        self._mock     = not SMBUS_AVAILABLE
        self._address  = QMC5883L_ADDRESS

        # Hard-iron calibration offsets
        self.offset_x = 0.0
        self.offset_y = 0.0

        # Soft-iron scale factors
        self.scale_x = 1.0
        self.scale_y = 1.0

        # Latest
        self.mag      = [0.0, 0.0, 0.0]
        self.heading  = 0.0   # degrees, 0 = North, 90 = East

        if not self._mock:
            self.bus = smbus2.SMBus(bus_num)
            self._init_chip()
        else:
            self.bus = None
            print("[MAG] smbus2 not found — mock mode")

    def _init_chip(self):
        self.bus.write_byte_data(self._address, REG_CONTROL2, 0x80)   # soft reset
        time.sleep(0.1)
        self.bus.write_byte_data(self._address, REG_PERIOD,   0x01)
        self.bus.write_byte_data(self._address, REG_CONTROL1, CTRL1_DEFAULT)
        print("[MAG] QMC5883L initialised")

    def _read_word(self, reg):
        low  = self.bus.read_byte_data(self._address, reg)
        high = self.bus.read_byte_data(self._address, reg + 1)
        val  = (high << 8) | low
        return val - 65536 if val >= 0x8000 else val

    def calibrate_hard_iron(self, seconds=15):
        """Rotate car 360° in ~15 s."""
        print(f"[MAG] Hard-iron calibration — rotate vehicle 360° in {seconds}s…")
        x_min = x_max = None
        y_min = y_max = None

        end = time.time() + seconds
        while time.time() < end:
            self.update()
            x, y = self.mag[0], self.mag[1]
            x_min = min(x_min, x) if x_min is not None else x
            x_max = max(x_max, x) if x_max is not None else x
            y_min = min(y_min, y) if y_min is not None else y
            y_max = max(y_max, y) if y_max is not None else y
            time.sleep(0.05)

        self.offset_x = (x_max + x_min) / 2
        self.offset_y = (y_max + y_min) / 2
        avg_delta = ((x_max - x_min) + (y_max - y_min)) / 4
        self.scale_x = avg_delta / ((x_max - x_min) / 2) if (x_max - x_min) > 0 else 1.0
        self.scale_y = avg_delta / ((y_max - y_min) / 2) if (y_max - y_min) > 0 else 1.0
        print(f"[MAG] Offsets: x={self.offset_x:.1f}  y={self.offset_y:.1f}")

    def update(self):
        if self._mock:
            self.mag = [100.0, 0.0, 0.0]
            self.heading = 0.0
            return

        raw_x = self._read_word(REG_X_LSB)
        raw_y = self._read_word(REG_X_LSB + 2)
        raw_z = self._read_word(REG_X_LSB + 4)

        cx = (raw_x - self.offset_x) * self.scale_x
        cy = (raw_y - self.offset_y) * self.scale_y

        self.mag = [cx, cy, float(raw_z)]

        heading = math.degrees(math.atan2(cy, cx))
        if heading < 0:
            heading += 360.0
        self.heading = heading

    def get_heading(self):
        return self.heading

    def get_data(self):
        return {
            "mag_x": self.mag[0],
            "mag_y": self.mag[1],
            "mag_z": self.mag[2],
            "heading": self.heading
        }
