import threading

try:
    import serial
except ImportError:
    serial = None

try:
    import pynmea2
except ImportError:
    pynmea2 = None

from config import HOME, SENSORS


class Neo6MGPS:
    def __init__(self, port="/dev/serial0", baudrate=9600):
        self._lock = threading.Lock()
        self.port = port
        self.baudrate = baudrate
        self.ser = None
        self.mock_mode = serial is None or pynmea2 is None
        self.latitude = HOME.lat
        self.longitude = HOME.lon
        self.fix_status = "No Fix"
        self.satellite_count = 0
        self.hdop = 99.0
        self.speed_mps = 0.0

        if self.mock_mode:
            return

        try:
            self.ser = serial.Serial(port, baudrate, timeout=1)
        except Exception:
            self.mock_mode = True
            self.ser = None

    def set_mock_position(self, lat, lon, speed_mps=0.0, satellites=None, hdop=None, fix_status=None):
        with self._lock:
            self.latitude = lat
            self.longitude = lon
            self.speed_mps = speed_mps
            if satellites is not None:
                self.satellite_count = satellites
            if hdop is not None:
                self.hdop = hdop
            if fix_status is not None:
                self.fix_status = fix_status

    def update(self):
        if self.mock_mode or not self.ser:
            return

        try:
            line = self.ser.readline().decode("utf-8", errors="ignore").strip()
            if not line:
                return

            if line.startswith(("$GPRMC", "$GNRMC")):
                msg = pynmea2.parse(line)
                with self._lock:
                    if msg.status == "A":
                        self.latitude = msg.latitude
                        self.longitude = msg.longitude
                        self.fix_status = "Fix"
                        self.speed_mps = float(msg.spd_over_grnd or 0.0) * 0.514444
                    else:
                        self.fix_status = "No Fix"
            elif line.startswith(("$GPGGA", "$GNGGA")):
                msg = pynmea2.parse(line)
                with self._lock:
                    self.satellite_count = int(msg.num_sats or 0)
                    self.hdop = float(msg.horizontal_dil or self.hdop)
        except Exception:
            return

    def get_data(self):
        with self._lock:
            return {
                "latitude": self.latitude,
                "longitude": self.longitude,
                "fix_status": self.fix_status,
                "satellite_count": self.satellite_count,
                "hdop": self.hdop,
                "speed_mps": self.speed_mps,
                "sample_hz": 1.0,
                "mock_mode": self.mock_mode,
            }

    def arm_default_fix(self):
        self.set_mock_position(
            HOME.lat,
            HOME.lon,
            speed_mps=0.0,
            satellites=SENSORS.default_satellites,
            hdop=SENSORS.default_hdop,
            fix_status="Fix",
        )