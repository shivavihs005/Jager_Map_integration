"""
gps.py — NMEA GPS Parser for NEO-6M
Auto-detects baud rate. Parses $GPRMC/$GNRMC for lat, lon, speed, heading.
"""

import time

try:
    import serial
    import pynmea2
    GPS_LIBS_AVAILABLE = True
except ImportError:
    GPS_LIBS_AVAILABLE = False
    print("[GPS] pyserial or pynmea2 not found. GPS will run in mock mode.")

GPS_PORT = "/dev/serial0"
GPS_BAUDS = [9600, 38400, 57600]


class GPS:
    def __init__(self, port=GPS_PORT):
        self.lat = 0.0
        self.lon = 0.0
        self.speed = 0.0       # m/s
        self.heading = 0.0     # degrees true
        self.has_fix = False
        self.satellites = 0
        self.last_update = 0
        self.baud_rate = 0

        self.ser = None
        self.mock_mode = True

        if not GPS_LIBS_AVAILABLE:
            return

        self.ser = self._auto_detect_baud(port)
        if self.ser:
            self.mock_mode = False
        else:
            print("[GPS] No valid baud rate detected. Running in mock mode.")

    def _auto_detect_baud(self, port):
        """Try multiple baud rates and return the first one that gives valid NMEA."""
        for baud in GPS_BAUDS:
            try:
                print(f"[GPS] Trying baud rate: {baud}...")
                ser = serial.Serial(port, baud, timeout=1)
                time.sleep(1)

                # Read a few lines to check for NMEA sentences
                for _ in range(5):
                    line = ser.readline().decode('ascii', errors='replace').strip()
                    if line.startswith('$GP') or line.startswith('$GN'):
                        print(f"[GPS] Locked onto baud {baud}: {line}")
                        self.baud_rate = baud
                        return ser

                ser.close()
            except Exception as e:
                print(f"[GPS] Baud {baud} failed: {e}")
        return None

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
            "satellites": self.satellites,
            "baud": self.baud_rate
        }
