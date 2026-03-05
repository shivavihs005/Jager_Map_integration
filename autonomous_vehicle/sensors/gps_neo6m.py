"""
gps_neo6m.py
NEO6M GPS driver — NMEA parsing, Haversine speed, fix detection.
"""
import math
import time
import threading

try:
    import serial
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False

from vehicle_config import GPS_SERIAL_PORT, GPS_BAUDRATE

EARTH_RADIUS_M = 6_371_000.0   # Mean earth radius, metres


def haversine_m(lat1, lon1, lat2, lon2):
    """Great-circle distance between two GPS points in metres."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlon / 2)**2
    return 2 * EARTH_RADIUS_M * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class GPS_NEO6M:
    def __init__(self):
        self._mock = not SERIAL_AVAILABLE
        self._lock = threading.Lock()

        # Published state
        self.latitude   = 0.0
        self.longitude  = 0.0
        self.altitude   = 0.0
        self.speed_kmh  = 0.0
        self.satellites = 0
        self.fix        = False

        self._prev_lat  = None
        self._prev_lon  = None
        self._prev_time = None

        if not self._mock:
            try:
                self._ser = serial.Serial(GPS_SERIAL_PORT, GPS_BAUDRATE, timeout=1)
                print(f"[GPS] NEO6M opened on {GPS_SERIAL_PORT}")
            except Exception as e:
                print(f"[GPS] Serial error: {e} — mock mode")
                self._mock = True
                self._ser = None

            # Background reader thread
            if not self._mock:
                threading.Thread(target=self._reader_thread, daemon=True).start()
        else:
            self._ser = None
            print("[GPS] pyserial not found — mock mode")

    # ── Background NMEA reader ────────────────────────────────────────────────
    def _reader_thread(self):
        while True:
            try:
                line = self._ser.readline().decode("ascii", errors="ignore").strip()
                if line.startswith("$GPGGA"):
                    self._parse_gga(line)
                elif line.startswith("$GPRMC"):
                    self._parse_rmc(line)
            except Exception:
                pass

    # ── NMEA Parsers ─────────────────────────────────────────────────────────
    def _nmea_to_decimal(self, val_str, direction):
        if not val_str:
            return 0.0
        dot = val_str.index(".")
        deg = float(val_str[:dot - 2])
        mins = float(val_str[dot - 2:])
        decimal = deg + mins / 60.0
        if direction in ("S", "W"):
            decimal = -decimal
        return decimal

    def _parse_gga(self, sentence):
        parts = sentence.split(",")
        if len(parts) < 10:
            return
        try:
            lat = self._nmea_to_decimal(parts[2], parts[3])
            lon = self._nmea_to_decimal(parts[4], parts[5])
            fix_quality = int(parts[6]) if parts[6] else 0
            sats = int(parts[7]) if parts[7] else 0
            alt = float(parts[9]) if parts[9] else 0.0
        except (ValueError, IndexError):
            return

        if fix_quality > 0:
            now = time.time()
            with self._lock:
                if self._prev_lat is not None and self._prev_time is not None:
                    dist_m = haversine_m(self._prev_lat, self._prev_lon, lat, lon)
                    dt     = now - self._prev_time
                    if dt > 0:
                        self.speed_kmh = (dist_m / dt) * 3.6
                self.latitude   = lat
                self.longitude  = lon
                self.altitude   = alt
                self.satellites = sats
                self.fix        = True
                self._prev_lat  = lat
                self._prev_lon  = lon
                self._prev_time = now
        else:
            with self._lock:
                self.fix = False

    def _parse_rmc(self, sentence):
        parts = sentence.split(",")
        # Supplement fix status from RMC
        if len(parts) > 2 and parts[2] == "A":
            with self._lock:
                self.fix = True

    # ── Public API ───────────────────────────────────────────────────────────
    def get_position(self):
        with self._lock:
            return self.latitude, self.longitude

    def get_speed_kmh(self):
        with self._lock:
            return self.speed_kmh

    def has_fix(self):
        with self._lock:
            return self.fix

    def get_data(self):
        with self._lock:
            return {
                "latitude":   self.latitude,
                "longitude":  self.longitude,
                "altitude":   self.altitude,
                "speed_kmh":  round(self.speed_kmh, 2),
                "satellites": self.satellites,
                "fix":        self.fix
            }
