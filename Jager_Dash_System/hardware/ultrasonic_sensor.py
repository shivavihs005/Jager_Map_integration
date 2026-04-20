import time
import random

try:
    import pigpio
    PI_ENV = True
except ImportError:
    PI_ENV = False

class UltrasonicSensor:
    """
    Interfaces with the HC-SR04 Ultrasonic Distance Sensor.
    TRIG -> GPIO 25 (Output)
    ECHO -> GPIO 9 (Input) - ⚠️ Requires 3.3V voltage divider!
    """
    def __init__(self, trig_pin=25, echo_pin=9):
        self.trig_pin = trig_pin
        self.echo_pin = echo_pin
        self.pi = None
        
        # Mock State
        self.mock_distance = 100.0

        if PI_ENV:
            try:
                self.pi = pigpio.pi()
                if self.pi.connected:
                    self.pi.set_mode(self.trig_pin, pigpio.OUTPUT)
                    self.pi.set_mode(self.echo_pin, pigpio.INPUT)
                    self.pi.write(self.trig_pin, 0) # Ensure trigger is low initially
                    print(f"[ULTRASONIC] HC-SR04 initialized. TRIG: {self.trig_pin}, ECHO: {self.echo_pin}")
                else:
                    print("[ULTRASONIC] pigpio daemon missing, falling back to mock mode.")
            except Exception as e:
                print(f"[ULTRASONIC] Initialization error: {e}")
        else:
            print("[ULTRASONIC] Windows environment detected, running in mock mode.")

    def get_distance(self):
        """Returns distance in centimeters."""
        if PI_ENV and self.pi and self.pi.connected:
            # Trigger 10us pulse
            self.pi.write(self.trig_pin, 1)
            time.sleep(0.00001)
            self.pi.write(self.trig_pin, 0)
            
            start_time = time.time()
            timeout = start_time + 0.1 # 100ms timeout
            
            # Wait for echo to go HIGH
            while self.pi.read(self.echo_pin) == 0 and time.time() < timeout:
                start_time = time.time()
            
            if time.time() >= timeout:
                return 999.0 # Timeout, nothing in range
                
            # Wait for echo to go LOW
            stop_time = time.time()
            timeout = time.time() + 0.1
            while self.pi.read(self.echo_pin) == 1 and time.time() < timeout:
                stop_time = time.time()
                
            if time.time() >= timeout:
                return 999.0 # Timeout
                
            elapsed = stop_time - start_time
            distance = (elapsed * 34300) / 2.0
            return round(distance, 2)
        else:
            # Mock behavior: drift between 25 and 150 cm
            self.mock_distance += random.uniform(-5.0, 5.0)
            if self.mock_distance > 150:
                self.mock_distance = 150
            if self.mock_distance < 20: # Occasionally get closer to trigger evasion
                self.mock_distance = 25
            return round(self.mock_distance, 2)
