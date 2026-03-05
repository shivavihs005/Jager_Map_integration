# Jager Autonomous Vehicle — Complete Walkthrough

---

## 0. Headless Pi Setup (Optional)

If setting up a fresh Raspberry Pi without a monitor:

1. **Enable SSH** — Create an empty file named `ssh` (no extension) in the SD card boot partition.
2. **Configure Wi-Fi** — Create `wpa_supplicant.conf` in the boot partition:

```conf
country=IN
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1

network={
    ssid="YOUR_HOTSPOT_NAME"
    psk="YOUR_HOTSPOT_PASSWORD"
    key_mgmt=WPA-PSK
}
```

### Initial Git Setup (on Pi via SSH)

```bash
sudo apt update && sudo apt install git -y
git config --global user.name "shivavihs005"
git config --global user.email "shivapanner2005@gmail.com"

mkdir -p ~/my-projects && cd ~/my-projects
git clone https://github.com/shivavihs005/Jager_Map_integration.git
cd Jager_Map_integration

# Pull updates later:
git stash && git pull origin main
```

---

## 1. Hardware Connections

### A. NEO-6M GPS (UART — `/dev/serial0`)
| GPS Pin | Pi Pin |
|---------|--------|
| VCC | 3.3V (Pin 1) |
| GND | GND (Pin 6) |
| RX | GPIO 14 / TXD |
| TX | GPIO 15 / RXD |

### B. MPU6500 IMU (I²C — address `0x68`)
| Sensor Pin | Pi Pin |
|------------|--------|
| VCC | 3.3V |
| GND | GND |
| SDA | GPIO 2 (SDA1) |
| SCL | GPIO 3 (SCL1) |

### C. QMC5883L Magnetometer (I²C — address `0x0D`)
| Sensor Pin | Pi Pin |
|------------|--------|
| VCC | 3.3V |
| GND | GND |
| SDA | GPIO 2 (SDA1, shared) |
| SCL | GPIO 3 (SCL1, shared) |

### D. BTS7960 DC Motor Driver
| Driver Pin | GPIO |
|------------|------|
| R_EN | GPIO 23 |
| L_EN | GPIO 24 |
| RPWM (Forward) | GPIO 13 |
| LPWM (Backward) | GPIO 12 |

### E. Steering Servo (pigpio, hardware PWM)
| Servo Pin | GPIO |
|-----------|------|
| Signal | **GPIO 17 (Pin 11)** |
| VCC | 5V external / BEC |
| GND | Common GND |

**Pulse limits:** MAX_LEFT = 680 µs | CENTER = 1060 µs | MAX_RIGHT = 1460 µs

---

## 2. Software Setup (First Time Only)

```bash
cd /home/pi/my-projects/Jager_Map_integration

# Make script executable and run it
chmod +x setup_env.sh
./setup_env.sh
```

The script installs:
- System packages: `pigpio`, `i2c-tools`, `python3-venv`, `libatlas-base-dev` (for numpy)
- Enables hardware interfaces: I²C, SPI, Serial (via `raspi-config`)
- Enables `pigpiod` daemon on boot
- Creates Python virtual environment `env/`
- Installs all Python packages: `pigpio`, `smbus2`, `pyserial`, `numpy`, `flask`, `flask-socketio`, `eventlet`

**After setup — reboot:**
```bash
sudo reboot
```

---

## 3. Running the Autonomous Vehicle

```bash
# 1. Go to the project root
cd /home/pi/my-projects/Jager_Map_integration

# 2. Activate the shared virtual environment
source env/bin/activate

# 3. Install the autonomous_vehicle requirements (first time or after updates)
pip install -r autonomous_vehicle/requirements.txt

# 4. Start the pigpio daemon (required before running — servo & motor won't work without it)
sudo pigpiod

# 5. Run the system
cd autonomous_vehicle
python main_autonomous.py


cd /home/pi/my-projects/Jager_Map_integration
source env/bin/activate
pip install -r autonomous_vehicle/requirements.txt
sudo pigpiod
cd autonomous_vehicle
python main_autonomous.py
```

Open the dashboard: **`http://<pi-ip>:5001`**

> **Tip:** To verify the env is active: `which python` should show `.../env/bin/python`
> **To deactivate later:** `deactivate`

---

## 4. Dashboard Features

```
┌─────────────────────────────────────┐
│  ⬡ JAGER  [ IDLE / NAVIGATE / STOP ]     ● 8 sats │
├─────────────────────────────────────┤
│                                     │
│          LEAFLET MAP                │
│   🔵 Vehicle (live, rotating)       │
│   📍 Destination marker             │
│   ─── Trajectory (blue)             │
│                                     │
├─────────────────┬───────────────────┤
│  Speed  km/h    │  Compass + Roll   │
│  Servo slider   │  Pitch / Yaw      │
│  Navigate btn   │  IMU raw values   │
└─────────────────┴───────────────────┘
```

| Feature | Description |
|---------|-------------|
| **Click map** | Drop a destination waypoint |
| **Navigate** | Starts Pure Pursuit autonomous drive |
| **Abort** | Emergency stop — centers servo |
| **Servo slider** | Manual pulse override (snaps to 1060) |
| **Live heading** | Compass needle rotates with vehicle |

---

## 5. First-Run Calibration (Recommended)

Uncomment these lines in `autonomous_vehicle/main_autonomous.py` for the **very first run only**:

```python
imu.calibrate()                    # Keep vehicle still for ~2 s
mag.calibrate_hard_iron(seconds=15) # Rotate vehicle 360° slowly
```

Then comment them out again for subsequent runs.

---

## 6. Key Tuning Parameters (`vehicle_config.py`)

| Parameter | Default | Effect |
|-----------|---------|--------|
| `PID_KP` | 2.5 | Higher = faster heading correction |
| `PID_KI` | 0.05 | Removes steady-state heading drift |
| `PID_KD` | 0.8 | Dampens steering oscillation |
| `PURE_PURSUIT_LOOKAHEAD_M` | 0.5 m | Shorter = tighter, more oscillation |
| `BASE_SPEED_PCT` | 50% | Cruise motor speed |
| `WAYPOINT_REACHED_M` | 0.30 m | "Close enough" threshold |
| `SERVO_CENTER` | 1060 µs | Edit if physical center drifts |

---

## 7. Module Architecture

```
sensors/ → state_estimator (100 Hz)
             ↓ Madgwick filter → roll, pitch, yaw
             ↓ EKF → x, y, heading, velocity
                ↓
         mission_manager (50 Hz)
             ↓ Pure Pursuit → steering angle
             ↓ PID → servo set_angle()
             ↓ Adaptive speed → motor set_speed()
                ↓
         dashboard (10 Hz WebSocket push)
             ↓ Leaflet.js live map
```

---

## 8. Troubleshooting

| Problem | Fix |
|---------|-----|
| `pigpio: cannot connect` | Run `sudo pigpiod` first |
| Servo not moving | Confirm GPIO 17 wire, check `sudo pigpiod` |
| IMU in mock mode | Check I²C: `i2cdetect -y 1` should show `68` and `0d` |
| GPS no fix | Need outdoor clear sky; check serial: `sudo cat /dev/serial0` |
| Dashboard blank | Ensure port 5001 isn't blocked by firewall |

