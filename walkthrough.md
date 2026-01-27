# Jager Dashboard & Map Integration Walkthrough

This document guides you through using the new Jager Dashboard, including Map Navigation, Manual Joystick Control, and configuration.

## 1. Hardware Connections
Connect the following components to your Raspberry Pi 4 GPIO:

### A. Neo-6M GPS Module (UART)
*Connect to the Pi's Serial Port (`/dev/serial0`)*
- **VCC** -> 3.3V (Pin 1)
- **GND** -> GND (Pin 6)
- **RX**  -> GPIO 14 (TXD) - *Note: GPS RX connects to Pi TX*
- **TX**  -> GPIO 15 (RXD) - *Note: GPS TX connects to Pi RX*

### B. DC Motor Driver (L298N or similar)
- **R_EN** (Right Enable) -> GPIO 23
- **L_EN** (Left Enable)  -> GPIO 24
- **RPWM** (Forward)      -> GPIO 13
- **LPWM** (Backward)     -> GPIO 12
- **GND** -> Ground
- **VCC** -> External Motor Power (e.g., 12V LiPo)

### C. Steering Servo
- **Signal** -> GPIO 18 (PWM)
- **VCC** -> 5V (from external BEC/Battery usually, NOT Pi directly for high torque)
- **GND** -> Ground (Common Ground with Pi)

## 2. Software Setup (First Time)
If you haven't set up the environment yet, run the included setup script:

```bash
# Make executable
chmod +x setup_env.sh

# Run setup
./setup_env.sh
```

This script will:
1. Update your system
2. Create a virtual environment `env`
3. Install dependencies (`flask`, `pyserial`, `pynmea2`, etc.)

**Important**: Ensure Serial Port is enabled in `sudo raspi-config` > Interfacing Options > Serial.

## 3. Setup & Running
1.  **Start the Server**:
    ```bash
    source env/bin/activate
    python app.py
    ```
2.  **Access Dashboard**: Open `http://<pi-ip>:5000` in your browser.

## 4. Dashboard Features

### A. Status Panel
The top-left panel shows real-time telemetry:
- **STATUS**: Current motion (STOPPED, FORWARD, TURNING).
- **MODE**: Current Operation Mode.
- **GPS**: Connection status (SEARCHING vs LOCKED).

### B. Mode Selection
Use the buttons to switch modes. **Note**: Switching modes will stop the car immediately for safety.
- **MANUAL**: Full control via Joystick.
- **SEMI-AUTO**: Map-based navigation.
- **AUTO**: (Future) Fully autonomous.

### C. Manual Control (Split)
*Only visible in MANUAL mode.*
- **Steering**: Use the LEFT Joystick to steer Left/Right.
- **Throttle**: Use the RIGHT Buttons. Hold **FWD** to go forward, **REV** to reverse.
- Release buttons to stop.

### D. Semi-Autonomous Navigation (Map)
*Only visible in SEMI-AUTO mode.*
1.  **Click on Map**: Drop a destination pin.
2.  **Calculate Path**: Click the button to generate a route (Blue Line).
3.  **Start Engine**: Begins autonomous travel to the destination.
4.  **Emergency Stop**: Click "Status" or "Stop" to halt immediately.

### E. Configuration
- **Max Speed**: Limits the top speed output to the motors (0-100%).
- **Max Turn**: Limits the maximum steering angle (0-100%).
- These settings apply to *both* Manual and Semi-Auto modes.

## 5. Troubleshooting
- **Joystick not working?**: Ensure you are in MANUAL mode.
- **Car not moving?**: Check connections and ensure Max Speed slider is > 0.
- **Map not routing?**: Ensure the Pi has internet access for OSRM API.
