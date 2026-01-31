import serial
import time
import threading
import pynmea2
from map_matcher import map_matcher

class GPSReader:
    def __init__(self, port='/dev/serial0', baudrate=9600):
        self.port = port
        self.baudrate = baudrate
        self.current_location = {'lat': 0.0, 'lng': 0.0, 'heading': 0.0, 'speed': 0.0}
        self.running = False
        self.thread = None

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._read_loop)
        self.thread.daemon = True
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()

    def _read_loop(self):
        try:
            ser = serial.Serial(self.port, self.baudrate, timeout=1)
            print(f"Connected to GPS on {self.port}")
        except Exception as e:
            print(f"Error connecting to GPS: {e}")
            return

        while self.running:
            try:
                line = ser.readline().decode('utf-8', errors='ignore')
                if line.startswith('$GPGGA') or line.startswith('$GNGGA'):
                    try:
                        msg = pynmea2.parse(line)
                        if msg.latitude and msg.longitude:
                            lat = msg.latitude
                            lng = msg.longitude
                            
                            # Attempt Map Matching
                            snapped = map_matcher.match_to_road(lat, lng)
                            if snapped:
                                lat, lng = snapped
                            
                            self.current_location['lat'] = lat
                            self.current_location['lng'] = lng
                    except pynmea2.ParseError:
                        continue
                elif line.startswith('$GPRMC') or line.startswith('$GNRMC'):
                    try:
                        msg = pynmea2.parse(line)
                        if msg.latitude and msg.longitude:
                             lat = msg.latitude
                             lng = msg.longitude
                             
                             # Attempt Map Matching
                             snapped = map_matcher.match_to_road(lat, lng)
                             if snapped:
                                 lat, lng = snapped
                                 
                             self.current_location['lat'] = lat
                             self.current_location['lng'] = lng
                        
                        # Extract Heading (True Course) and Speed
                        if hasattr(msg, 'true_course') and msg.true_course is not None:
                             self.current_location['heading'] = float(msg.true_course)
                        else:
                             self.current_location['heading'] = 0.0 # Default if not moving/available

                        if hasattr(msg, 'spd_over_grnd') and msg.spd_over_grnd is not None:
                             self.current_location['speed'] = float(msg.spd_over_grnd) # Knots usually
                        
                    except pynmea2.ParseError:
                        continue
            except Exception as e:
                print(f"Error reading GPS: {e}")
                time.sleep(1)

    def get_location(self):
        return self.current_location

# Global instance for easy import if needed, or instantiate in app.py
gps_reader = GPSReader()
