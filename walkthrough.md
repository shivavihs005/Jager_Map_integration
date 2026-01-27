# Jager Dashboard & Map Integration Walkthrough

This document guides you through using the new Jager Dashboard, including Map Navigation, Manual Joystick Control, and configuration.

## 1. Hardware Connections
(Same as previous)
- **VCC** -> Pin 1/2
- **GND** -> Pin 6
- **TX**  -> GPIO 15 (Pin 10)
- **RX**  -> GPIO 14 (Pin 8)

## 2. Setup & Running
1.  **Start the Server**:
    ```bash
    source env/bin/activate
    python app.py
    ```
2.  **Access Dashboard**: Open `http://<pi-ip>:5000` in your browser.

## 3. Dashboard Features

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

### C. Manual Control (Joystick)
*Only visible in MANUAL mode.*
- Drag the **Virtual Joystick** to drive.
- **Up/Down**: Controls Forward/Reverse speed.
- **Left/Right**: Controls Steering angle.
- Release to stop.

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

## 4. Troubleshooting
- **Joystick not working?**: Ensure you are in MANUAL mode.
- **Car not moving?**: Check connections and ensure Max Speed slider is > 0.
- **Map not routing?**: Ensure the Pi has internet access for OSRM API.
