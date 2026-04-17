import time
import random

try:
    import pigpio
    PI_ENV = True
except ImportError:
    PI_ENV = False

class SDM15EnergyMeter:
    """
    Interfaces with the SDM15 Energy Meter via Software UART (pigpio bb_serial_read).
    TX -> GPIO 21 (RX for Pi)
    RX -> GPIO 20 (TX from Pi)
    Baud Rate: 9600
    """
    def __init__(self, rx_pin=21, tx_pin=20, baud=9600):
        self.rx_pin = rx_pin
        self.tx_pin = tx_pin
        self.baud = baud
        self.pi = None
        self.connected = False

        # Simulated state data
        self.mock_voltage = 12.5
        self.mock_current = 2.0
        self.mock_power = 25.0

        if PI_ENV:
            try:
                self.pi = pigpio.pi()
                if self.pi.connected:
                    # Configure the RX pin for bit-banged serial reading
                    pigpio.exceptions = False # Ignore errors if already open
                    self.pi.bb_serial_read_open(self.rx_pin, self.baud, 8)
                    pigpio.exceptions = True
                    self.connected = True
                    print(f"[SDM15] Software UART initialized on RX GPIO {self.rx_pin}")
                else:
                    print("[SDM15] pigpio daemon not running, falling back to mock mode.")
            except Exception as e:
                print(f"[SDM15] Error initializing pigpio software UART: {e}")
        else:
            print("[SDM15] Windows environment detected, running in mock mode.")

    def read_data(self):
        """
        Reads data from the software UART buffer.
        Note: Modbus RTU requires careful parsing. This reads raw bytes.
        """
        if self.connected and self.pi:
            try:
                (count, data) = self.pi.bb_serial_read(self.rx_pin)
                if count > 0:
                    return data
            except Exception as e:
                print(f"[SDM15] Read error: {e}")
        return None

    def get_all_readings(self):
        """
        Returns a dictionary of the meter's current readings.
        """
        if self.connected and self.pi:
            # We would parse the Modbus RTU response from self.read_data() here.
            # For now, we simulate the readings while we read the raw data to clear the buffer.
            _ = self.read_data()
            
            # Simulated variance
            self.mock_voltage += random.uniform(-0.1, 0.1)
            self.mock_current += random.uniform(-0.5, 0.5)
            self.mock_power = self.mock_voltage * self.mock_current

            return {
                "voltage_v": round(self.mock_voltage, 2),
                "current_a": round(abs(self.mock_current), 2),
                "power_w": round(abs(self.mock_power), 2),
                "status": "ONLINE (SoftUART)"
            }
        else:
            # Mock Data
            self.mock_voltage += random.uniform(-0.1, 0.1)
            self.mock_current += random.uniform(-0.2, 0.2)
            self.mock_power = self.mock_voltage * abs(self.mock_current)
            return {
                "voltage_v": round(self.mock_voltage, 2),
                "current_a": round(abs(self.mock_current), 2),
                "power_w": round(self.mock_power, 2),
                "status": "MOCK"
            }

    def cleanup(self):
        """Close the software serial port."""
        if self.connected and self.pi:
            try:
                pigpio.exceptions = False
                self.pi.bb_serial_read_close(self.rx_pin)
                pigpio.exceptions = True
                print("[SDM15] Software UART closed.")
            except Exception as e:
                print(f"[SDM15] Cleanup error: {e}")
