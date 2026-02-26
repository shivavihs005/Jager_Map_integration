"""
gps.py — NMEA GPS Parser for NEO-6M
Parses $GPRMC/$GNRMC sentences for lat, lon, speed, and heading.
"""

import time

try:
    import serial
    import pynmea2
    GPS_LIBS_AVAILABLE = True
except ImportError:
    GPS_LIBS_AVAILABLE = False
    print("[GPS] pyserial or pynmea2 not found. GPS will run in mock mode.")


class GPS:
    def __init__(self, port="/dev/serial0", baud=9600):
        self.lat = 0.0
        self.lon = 0.0
        self.speed = 0.0       # m/s
        self.heading = 0.0     # degrees true
        self.has_fix = False
        self.satellites = 0
        self.last_update = 0

        self.ser = None
        self.mock_mode = True

        if not GPS_LIBS_AVAILABLE:
            return

        try:
            self.ser = serial.Serial(port, baud, timeout=1)
            self.mock_mode = False
            print(f"[GPS] Serial port {port} opened at {baud} baud.")
        except Exception as e:
            print(f"[GPS] Could not open serial port: {e}. Running in mock mode.")

    def update(self):
        """Read one line from GPS and parse if valid."""
        if self.mock_mode or self.ser is None:
            return

        try:
            line = self.ser.readline().decode('ascii', errors='replace').strip()
            if not line:
                return

            # Parse RMC sentences (position, speed, heading)
            if line.startswith('$GPRMC') or line.startswith('$GNRMC'):
                try:
                    msg = pynmea2.parse(line)
                    if getattr(msg, 'status', 'V') == 'A':
                        if hasattr(msg, 'latitude') and hasattr(msg, 'longitude'):
                            self.lat = msg.latitude
                            self.lon = msg.longitude
                            self.has_fix = True
                            self.last_update = time.time()

                        # Speed (knots → m/s)
                        spd = getattr(msg, 'spd_over_grnd', None)
                        if spd is not None:
                            self.speed = float(spd) * 0.514444

                        # Heading (course over ground)
                        cog = getattr(msg, 'true_course', None)
                        if cog is not None and self.speed > 0.3:
                            self.heading = float(cog)
                    else:
                        self.has_fix = False
                except pynmea2.ParseError:
                    pass

            # Parse GGA for satellite count
            elif line.startswith('$GPGGA') or line.startswith('$GNGGA'):
                try:
                    msg = pynmea2.parse(line)
                    self.satellites = int(getattr(msg, 'num_sats', 0) or 0)
                    if getattr(msg, 'gps_qual', 0) > 0:
                        if hasattr(msg, 'latitude') and hasattr(msg, 'longitude'):
                            self.lat = msg.latitude
                            self.lon = msg.longitude
                            self.has_fix = True
                    else:
                        self.has_fix = False
                except pynmea2.ParseError:
                    pass

        except Exception:
            pass

    def get_data(self):
        return {
            "lat": round(self.lat, 6),
            "lon": round(self.lon, 6),
            "speed": round(self.speed, 2),
            "heading": round(self.heading, 2),
            "has_fix": self.has_fix,
            "satellites": self.satellites
        }
