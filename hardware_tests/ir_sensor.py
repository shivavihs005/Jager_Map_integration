"""
ir_sensor.py — Sharp IR Distance Sensor via MCP3008 ADC
Reads analog voltage from a Sharp GP2Y0A21YK0F IR sensor,
converts to distance in cm, and applies moving average smoothing.

Safety system: provides obstacle detection for the behavior controller.

Wiring (MCP3008 SPI):
    VDD  → 3.3V
    VREF → 3.3V
    AGND → GND
    DGND → GND
    CLK  → GPIO 11 (SPI0 SCLK)
    DOUT → GPIO 9  (SPI0 MISO)
    DIN  → GPIO 10 (SPI0 MOSI)
    CS   → GPIO 8  (SPI0 CE0)

    Sharp IR signal → MCP3008 CH0
"""

import time
import threading
from collections import deque

# --- ADC Driver ---
try:
    import spidev
    MOCK_ADC = False
except ImportError:
    print("[IR] spidev not found. Using Mock ADC.")
    MOCK_ADC = True


class IRSensor:
    """Sharp IR sensor with MCP3008 ADC, smoothing, and obstacle detection."""

    # --- Configuration ---
    ADC_CHANNEL = 0           # MCP3008 channel (0-7)
    ADC_VREF = 3.3            # ADC reference voltage
    ADC_RESOLUTION = 1024     # 10-bit ADC
    SMOOTHING_SAMPLES = 5     # Moving average window
    OBSTACLE_THRESHOLD = 20.0 # cm — anything closer is an obstacle
    MIN_DISTANCE = 5.0        # cm — sensor minimum range
    MAX_DISTANCE = 80.0       # cm — sensor maximum range
    READ_INTERVAL = 0.05      # 20Hz read rate

    def __init__(self, channel=0):
        self.ADC_CHANNEL = channel
        self._distance_buffer = deque(maxlen=self.SMOOTHING_SAMPLES)
        self._distance_cm = self.MAX_DISTANCE
        self._is_obstacle = False
        self._raw_voltage = 0.0
        self._lock = threading.Lock()
        self._running = False

        # Initialize SPI
        if not MOCK_ADC:
            try:
                self.spi = spidev.SpiDev()
                self.spi.open(0, 0)          # Bus 0, CE0
                self.spi.max_speed_hz = 1000000
                self.spi.mode = 0
                print(f"[IR] MCP3008 initialized on CH{self.ADC_CHANNEL}")
            except Exception as e:
                print(f"[IR] SPI init failed: {e}. Using mock mode.")
                self.spi = None
        else:
            self.spi = None

    def _read_adc(self):
        """Read raw 10-bit value from MCP3008 channel."""
        if self.spi is None:
            # Mock: return a safe distance (no obstacle)
            return 300  # ~1.0V → ~40cm

        ch = self.ADC_CHANNEL
        # MCP3008 protocol: start bit, single-ended, channel
        cmd = [1, (8 + ch) << 4, 0]
        result = self.spi.xfer2(cmd)
        value = ((result[1] & 0x03) << 8) | result[2]
        return value

    def _voltage_to_distance(self, voltage):
        """
        Convert Sharp IR sensor voltage to distance in cm.
        Approximate formula for GP2Y0A21YK0F:
            distance_cm ≈ 27.86 / (voltage - 0.42)
        """
        if voltage <= 0.45:
            return self.MAX_DISTANCE  # Too far or invalid
        if voltage >= 2.8:
            return self.MIN_DISTANCE  # Very close

        try:
            dist = 27.86 / (voltage - 0.42)
        except ZeroDivisionError:
            return self.MAX_DISTANCE

        # Clamp to sensor range
        return max(self.MIN_DISTANCE, min(self.MAX_DISTANCE, dist))

    def update(self):
        """Read sensor once and update internal state."""
        raw = self._read_adc()
        voltage = (raw / self.ADC_RESOLUTION) * self.ADC_VREF
        distance = self._voltage_to_distance(voltage)

        with self._lock:
            self._raw_voltage = round(voltage, 3)
            self._distance_buffer.append(distance)
            # Moving average
            self._distance_cm = round(
                sum(self._distance_buffer) / len(self._distance_buffer), 1
            )
            self._is_obstacle = self._distance_cm < self.OBSTACLE_THRESHOLD

    def get_data(self):
        """Thread-safe read of current sensor state."""
        with self._lock:
            return {
                "distance_cm": self._distance_cm,
                "is_obstacle": self._is_obstacle,
                "voltage": self._raw_voltage
            }

    def is_obstacle(self):
        """Quick check for obstacle presence."""
        with self._lock:
            return self._is_obstacle

    def start_loop(self):
        """Start continuous reading in a background thread."""
        self._running = True
        def _loop():
            while self._running:
                self.update()
                time.sleep(self.READ_INTERVAL)
        t = threading.Thread(target=_loop, daemon=True)
        t.start()
        print("[IR] Sensor loop started (20Hz)")

    def stop(self):
        """Stop the read loop."""
        self._running = False
        if self.spi is not None:
            try:
                self.spi.close()
            except Exception:
                pass

    def cleanup(self):
        self.stop()
