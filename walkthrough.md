# Raspberry Pi GPS Map Integration Walkthrough

This document guides you through setting up the Jager Map Integration on a Raspberry Pi with a Neo-6M GPS module.

## 1. Hardware Connections
Connect your Neo-6M GPS module to the Raspberry Pi GPIO header:
- **VCC** -> 3.3V (Pin 1) or 5V (Pin 2) (Check your module specs, usually 3.3V is safer for logic, but some modules require 5V power)
- **GND** -> GND (Pin 6)
- **TX**  -> RXD (GPIO 15 / Pin 10)
- **RX**  -> TXD (GPIO 14 / Pin 8)

## 2. Raspberry Pi Configuration
You must enable the serial port and disable the login shell over serial.
1. Run `sudo raspi-config`
2. Select **Interface Options** -> **Serial Port**
3. **Login shell over serial?** -> **No**
4. **Hardware enabled?** -> **Yes**
5. Reboot the Pi: `sudo reboot`

## 3. Software Setup
Navigate to the project directory on your Pi and run the setup script.

```bash
chmod +x setup_env.sh
./setup_env.sh
```
This script will:
- Update your system
- Create a virtual environment folder named `env`
- Install `flask`, `pyserial`, and `pynmea2` inside that environment

## 4. Running the Application
To start the server, execute:

```bash
source env/bin/activate
python app.py
```
The server will start on port 5000. You can access it from another device on the same WiFi network at `http://<your-pi-ip>:5000`.

## 5. How it Works
- **`gps_reader.py`**: Runs in the background, reading NMEA data from `/dev/serial0`.
- **`app.py`**: Hosted Flask server. Exposes `/api/location` endpoint.
- **`script.js`**: Polls `/api/location` every 2 seconds to update the "You are here" marker on the map.

## Troubleshooting
- **No GPS Fix**: Ensure the GPS module has a clear view of the sky. It may take minutes to get a cold fix. The LED on the module normally blinks when it has a fix.
- **Permission Denied**: If you get serial permission errors, add your user to the dialout group: `sudo usermod -a -G dialout $USER`, then logout and login.
