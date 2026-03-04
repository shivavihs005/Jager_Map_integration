"""
neo6m_gps.py — Read GPS data from UART
"""
import serial
import pynmea2
import threading
import time

class Neo6MGPS:
    def __init__(self, port="/dev/serial0", baudrate=9600):
        self._lock = threading.Lock()
        
        self.latitude = 0.0
        self.longitude = 0.0
        self.fix_status = "No Fix"
        self.satellite_count = 0
        self.speed = 0.0

        try:
            self.ser = serial.Serial(port, baudrate, timeout=1)
            self.mock_mode = False
            print(f"[GPS] Opened {port} at {baudrate} baud.")
        except Exception as e:
            print(f"[GPS] UART open failed: {e}. Running mock mode.")
            self.ser = None
            self.mock_mode = True

    def update(self):
        if self.mock_mode or not self.ser:
            return

        try:
            line = self.ser.readline().decode('utf-8', errors='ignore').strip()
            if not line:
                return

            if line.startswith('$GPRMC') or line.startswith('$GNRMC'):
                msg = pynmea2.parse(line)
                with self._lock:
                    if msg.status == 'A':  # Data Valid
                        self.latitude = msg.latitude
                        self.longitude = msg.longitude
                        self.fix_status = "Fix"
                        # Speed in knots to m/s
                        self.speed = float(msg.spd_over_grnd) * 0.514444
                    else:
                        self.fix_status = "No Fix"

            elif line.startswith('$GPGGA') or line.startswith('$GNGGA'):
                msg = pynmea2.parse(line)
                with self._lock:
                    try:
                        self.satellite_count = int(msg.num_sats)
                    except ValueError:
                        self.satellite_count = 0

        except pynmea2.ParseError:
            pass
        except Exception:
            pass

    def get_data(self):
        with self._lock:
            return {
                "latitude": self.latitude,
                "longitude": self.longitude,
                "fix_status": self.fix_status,
                "satellite_count": self.satellite_count,
                "speed": self.speed
            }
