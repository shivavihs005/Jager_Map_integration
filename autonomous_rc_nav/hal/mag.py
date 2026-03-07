import math
import threading
import time

try:
    from smbus2 import SMBus
except ImportError:
    try:
        from smbus import SMBus
    except ImportError:
        SMBus = None


QMC5883_ADDR = 0x0D
REG_DATA_X_L = 0x00
REG_CONTROL_1 = 0x09
REG_SET_RESET = 0x0B


class QMC5883:
    def __init__(self, bus_num=1):
        self._lock = threading.Lock()
        self.mock_mode = SMBus is None
        self.bus = None
        self.mag_x = 0.0
        self.mag_y = 0.0
        self.mag_z = 0.0
        self.heading = 0.0

        if self.mock_mode:
            return

        try:
            self.bus = SMBus(bus_num)
            self.bus.write_byte_data(QMC5883_ADDR, REG_SET_RESET, 0x01)
            time.sleep(0.01)
            self.bus.write_byte_data(QMC5883_ADDR, REG_CONTROL_1, 0x1D)
            time.sleep(0.01)
        except Exception:
            self.mock_mode = True
            self.bus = None

    def _read_word(self, register):
        low = self.bus.read_byte_data(QMC5883_ADDR, register)
        high = self.bus.read_byte_data(QMC5883_ADDR, register + 1)
        value = (high << 8) | low
        if value > 32767:
            value -= 65536
        return value

    def set_mock_heading(self, heading_deg):
        with self._lock:
            self.heading = heading_deg % 360.0
            self.mag_x = int(math.cos(math.radians(self.heading)) * 420)
            self.mag_y = int(math.sin(math.radians(self.heading)) * 420)
            self.mag_z = 20.0

    def update(self):
        with self._lock:
            if self.mock_mode:
                self.mag_x = int(math.cos(math.radians(self.heading)) * 420)
                self.mag_y = int(math.sin(math.radians(self.heading)) * 420)
                self.mag_z = 20.0 + math.sin(time.time() * 0.4) * 2.0
                return

            self.mag_x = self._read_word(REG_DATA_X_L)
            self.mag_y = self._read_word(REG_DATA_X_L + 2)
            self.mag_z = self._read_word(REG_DATA_X_L + 4)
            heading = math.degrees(math.atan2(self.mag_y, self.mag_x))
            if heading < 0:
                heading += 360.0
            self.heading = heading

    def get_data(self):
        with self._lock:
            return {
                "mag_x": self.mag_x,
                "mag_y": self.mag_y,
                "mag_z": self.mag_z,
                "heading": self.heading,
                "mock_mode": self.mock_mode,
            }