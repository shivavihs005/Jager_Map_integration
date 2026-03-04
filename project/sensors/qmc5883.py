"""
qmc5883.py — Read magnetometer values
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

QMC5883_ADDR = 0x0D
REG_DATA_OUT_X_LSB = 0x00
REG_CONTROL_1 = 0x09
REG_SET_RESET = 0x0B

class QMC5883:
    def __init__(self, bus_num=1):
        self._lock = threading.Lock()
        self.mock_mode = True
        
        self.mag_x = 0.0
        self.mag_y = 0.0
        self.mag_z = 0.0
        self.heading = 0.0

        if SMBus is None:
            print("[QMC5883] No SMBus found. Running in mock mode.")
            return

        try:
            self.bus = SMBus(bus_num)
            
            # Setup
            self.bus.write_byte_data(QMC5883_ADDR, REG_SET_RESET, 0x01)
            time.sleep(0.01)
            
            # Continuous mode, 200Hz, 8G, OSR=512
            self.bus.write_byte_data(QMC5883_ADDR, REG_CONTROL_1, 0x1D)
            time.sleep(0.01)

            self.mock_mode = False
            print("[QMC5883] Initialized successfully.")
        except Exception as e:
            print(f"[QMC5883] Init failed: {e}. Running mock mode.")
            self.bus = None

    def _read_word_2c(self, reg):
        low = self.bus.read_byte_data(QMC5883_ADDR, reg)
        high = self.bus.read_byte_data(QMC5883_ADDR, reg + 1)
        val = (high << 8) | low
        if val > 32767:
            val -= 65536
        return val

    def update(self):
        """Read values and calculate heading."""
        if self.mock_mode:
            return

        try:
            with self._lock:
                self.mag_x = self._read_word_2c(REG_DATA_OUT_X_LSB)
                self.mag_y = self._read_word_2c(REG_DATA_OUT_X_LSB + 2)
                self.mag_z = self._read_word_2c(REG_DATA_OUT_X_LSB + 4)

                # Calculate heading: atan2(Y, X)
                heading_rad = math.atan2(self.mag_y, self.mag_x)
                heading_deg = math.degrees(heading_rad)
                
                # Convert to 0–360
                if heading_deg < 0:
                    heading_deg += 360.0

                self.heading = heading_deg
        except Exception:
            pass 

    def get_data(self):
        with self._lock:
            return {
                "mag_x": self.mag_x,
                "mag_y": self.mag_y,
                "mag_z": self.mag_z,
                "heading": self.heading
            }
