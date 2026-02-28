"""
ir_sensor.py — Digital IR Obstacle Sensor (Direct GPIO)
Reads a digital IR obstacle detection module connected directly to a GPIO pin.
No ADC required — the module has a built-in comparator.

Output: HIGH = no obstacle, LOW = obstacle detected
(Some modules are inverted — set ACTIVE_LOW accordingly)

Wiring (3 wires):
    VCC  → 5V
    GND  → GND
    OUT  → GPIO 17 (configurable)

Adjust detection distance using the potentiometer on the IR module.
"""

import time
import threading

try:
    import RPi.GPIO as GPIO
    MOCK_GPIO = False
except ImportError:
    print("[IR] RPi.GPIO not found. Using mock mode.")
    MOCK_GPIO = True


class IRSensor:
    """Digital IR obstacle sensor — direct GPIO read."""

    # --- Configuration ---
    DEFAULT_PIN = 17          # GPIO pin connected to IR module OUT
    ACTIVE_LOW = True         # True: LOW = obstacle, HIGH = clear (most common)
    READ_INTERVAL = 0.05      # 20Hz read rate
    DEBOUNCE_COUNT = 3        # Require N consecutive reads to change state

    def __init__(self, pin=None):
        self.pin = pin if pin is not None else self.DEFAULT_PIN
        self._is_obstacle = False
        self._lock = threading.Lock()
        self._running = False
        self._consecutive = 0  # Debounce counter

        # Initialize GPIO
        if not MOCK_GPIO:
            try:
                GPIO.setmode(GPIO.BCM)
                GPIO.setup(self.pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                print(f"[IR] Digital sensor initialized on GPIO {self.pin}")
            except Exception as e:
                print(f"[IR] GPIO setup failed: {e}. Using mock mode.")
        else:
            print(f"[IR] Mock mode — GPIO {self.pin} (simulated: no obstacle)")

    def _read_pin(self):
        """Read the digital IR sensor pin. Returns True if obstacle detected."""
        if MOCK_GPIO:
            return False  # Mock: no obstacle

        raw = GPIO.input(self.pin)

        if self.ACTIVE_LOW:
            return raw == GPIO.LOW   # LOW = obstacle
        else:
            return raw == GPIO.HIGH  # HIGH = obstacle

    def update(self):
        """Read sensor and apply debounce filtering."""
        reading = self._read_pin()

        with self._lock:
            if reading == self._is_obstacle:
                # Same state — reset debounce counter
                self._consecutive = 0
            else:
                # Different state — count consecutive readings
                self._consecutive += 1
                if self._consecutive >= self.DEBOUNCE_COUNT:
                    self._is_obstacle = reading
                    self._consecutive = 0

    def get_data(self):
        """Thread-safe read of current sensor state."""
        with self._lock:
            return {
                "distance_cm": 10.0 if self._is_obstacle else 80.0,  # Approximate for UI
                "is_obstacle": self._is_obstacle
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
        print(f"[IR] Sensor loop started (20Hz) on GPIO {self.pin}")

    def stop(self):
        """Stop the read loop."""
        self._running = False

    def cleanup(self):
        self.stop()
