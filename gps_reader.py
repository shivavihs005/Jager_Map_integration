import serial
import time
import threading
import pynmea2

class GPSReader:
    def __init__(self, port='/dev/serial0', baudrate=9600):
        self.port = port
        self.baudrate = baudrate
        self.current_location = {'lat': 0.0, 'lng': 0.0}
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
                            self.current_location = {
                                'lat': msg.latitude,
                                'lng': msg.longitude
                            }
                    except pynmea2.ParseError:
                        continue
            except Exception as e:
                print(f"Error reading GPS: {e}")
                time.sleep(1)

    def get_location(self):
        return self.current_location

# Global instance for easy import if needed, or instantiate in app.py
gps_reader = GPSReader()
