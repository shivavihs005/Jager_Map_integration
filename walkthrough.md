# Jager Dashboard & Map Integration Walkthrough

This document guides you through using the new Jager Dashboard, including Map Navigation, Manual Joystick Control, and configuration.


## 0. Headless Pi Setup (Optional)
If you are setting up a fresh Raspberry Pi without a monitor/keyboard:

1.  **Enable SSH**: Create an empty file named `ssh` (no extension) in the boot partition of the SD card.
2.  **Configure Wi-Fi**: Create a file named `wpa_supplicant.conf` in the boot partition with the following content:
    ```conf
    country=IN
    ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
    update_config=1

    network={
        ssid="YOUR_PHONE_HOTSPOT_NAME"
        psk="YOUR_HOTSPOT_PASSWORD"
        key_mgmt=WPA-PSK
    }
    ```
# Update and upgrade system
sudo apt update && sudo apt upgrade -y

# Enable VNC Server
sudo raspi-config nonint do_vnc 0

# Set a default resolution for VNC (recommended for headless)
sudo raspi-config nonint do_resolution 2 16
    


### Initial Git Setup
After connecting to the Pi via SSH, run the following commands to set up the project:

```bash
# Install Git
sudo apt update && sudo apt install git -y

# Configure Git (replace with your actual name and email)
git config --global user.name "shivavihs005"
git config --global user.email "[EMAIL_ADDRESS]"

# Create project folder
mkdir -p ~/my-projects
cd ~/my-projects

# Clone your repository
git clone https://github.com/shivavihs005/Jager_Map_integration.git

# Enter the repository
cd Jager_Map_integration

# To pull updates later
git pull origin main 

# Check status
git status

# Stage changes
git add .

# Commit changes
git commit -m "Your commit message"

# Push to origin
git push origin main


# List files in the repository
ls -la
```

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
    sudo tee /etc/systemd/system/jager.service <<EOF
    [Unit]
    Description=Jager Dashboard
    After=network.target

    [Service]
    ExecStart=$(pwd)/env/bin/python $(pwd)/app.py
    WorkingDirectory=$(pwd)
    StandardOutput=inherit
    StandardError=inherit
    Restart=always
    User=$USER

    [Install]
    WantedBy=multi-user.target
    EOF

    sudo systemctl enable jager.service
    sudo systemctl start jager.service
    

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

## 6. Hardware Testing (Diagnostics)
If you want to test the hardware components separately without running the full dashboard, use the dedicated test apps in `hardware_tests/`.

### A. GPS Test
1.  **Run the App**:
    ```bash
    python hardware_tests/GPS_app.py
    ```
2.  **Open Browser**: Go to `http://<pi-ip>:5001`
3.  **Verify**:
    -   Status should change from "SEARCHING" to "LOCKED" when GPS fix is acquired.
    -   Your location should appear on the map.

### B. Motors Test
1.  **Run the App**:
    ```bash
    python hardware_tests/Motors_app.py
    ```
2.  **Open Browser**: Go to `http://<pi-ip>:5002`
3.  **Verify**:
    -   Use the on-screen Joystick or Buttons to drive.
    -   Check if motors spin correctly (Forward/Reverse).
    -   Check if steering servo moves correctly (Left/Right).

