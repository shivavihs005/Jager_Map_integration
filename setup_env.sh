#!/bin/bash
# ============================================================
#  Jager Autonomous Vehicle — Full Environment Setup Script
#  Run once on a fresh Raspberry Pi OS (Bullseye / Bookworm)
#  Usage:  chmod +x setup_env.sh && ./setup_env.sh
# ============================================================

set -e   # Stop on first error

echo "========================================================"
echo "  JAGER — Setting up Autonomous Vehicle Environment"
echo "========================================================"

# ── 1. System update ──────────────────────────────────────────────────────────
echo ""
echo "[1/7] Updating system packages..."
sudo apt-get update -y
sudo apt-get upgrade -y

# ── 2. System-level dependencies ──────────────────────────────────────────────
echo ""
echo "[2/7] Installing system packages..."
sudo apt-get install -y \
    python3-venv \
    python3-pip \
    python3-dev \
    git \
    i2c-tools \
    python3-smbus \
    pigpio \
    python3-pigpio \
    libopenblas-dev \
    libatlas-base-dev   # required for numpy on Pi

# ── 3. Enable hardware interfaces ─────────────────────────────────────────────
echo ""
echo "[3/7] Enabling I2C, SPI, Serial, and Camera interfaces..."
sudo raspi-config nonint do_i2c 0       # Enable I2C  (for MPU6500, QMC5883L)
sudo raspi-config nonint do_serial 2    # Enable serial hardware, disable login shell
                                         # (2 = keep hardware port ON, disable login)
sudo raspi-config nonint do_spi 0       # Enable SPI (future use)

# ── 4. Enable and start pigpio daemon ─────────────────────────────────────────
echo ""
echo "[4/7] Enabling pigpio daemon on boot..."
sudo systemctl enable pigpiod
sudo systemctl start  pigpiod
echo "    pigpiod status: $(sudo systemctl is-active pigpiod)"

# ── 5. Create Python virtual environment ──────────────────────────────────────
echo ""
echo "[5/7] Creating Python virtual environment..."
python3 -m venv env
source env/bin/activate

# ── 6. Install all Python packages ────────────────────────────────────────────
echo ""
echo "[6/7] Installing Python dependencies..."

# Core hardware / GPIO
pip install --upgrade pip
pip install pigpio           # pigpio Python bindings
pip install smbus2           # I2C for MPU6500, QMC5883L
pip install pyserial         # UART for NEO6M GPS

# Sensor / math
pip install numpy             # EKF matrix math

# Web dashboard
pip install flask
pip install flask-socketio
pip install "python-socketio[asyncio_client]"
pip install eventlet

# Legacy / existing project dependencies (kept for backward compat)
pip install requests
pip install RPLCD
pip install gpiozero
pip install pynmea2

# ── 7. Verify key installs ────────────────────────────────────────────────────
echo ""
echo "[7/7] Verifying key packages..."
python3 -c "import pigpio;  print('  ✔ pigpio')"
python3 -c "import smbus2;  print('  ✔ smbus2')"
python3 -c "import serial;  print('  ✔ pyserial')"
python3 -c "import numpy;   print('  ✔ numpy')"
python3 -c "import flask;   print('  ✔ flask')"
python3 -c "import flask_socketio; print('  ✔ flask-socketio')"

deactivate

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo "========================================================"
echo "  Setup Complete!"
echo "========================================================"
echo ""
echo "  NEXT STEPS:"
echo ""
echo "  1. Reboot the Pi so all interface changes take effect:"
echo "       sudo reboot"
echo ""
echo "  2. After reboot, activate the environment:"
echo "       cd /home/pi/my-projects/Jager_Map_integration"
echo "       source env/bin/activate"
echo ""
echo "  3. Run the autonomous vehicle system:"
echo "       cd autonomous_vehicle"
echo "       python main_autonomous.py"
echo ""
echo "  4. Open the dashboard in your browser:"
echo "       http://<pi-ip-address>:5001"
echo ""
echo "  IMPORTANT: Make sure pigpiod is running before main_autonomous.py:"
echo "       sudo pigpiod"
echo "========================================================"
# Enable Serial Port (Instructional)
echo "---------------------------------------------------"
echo "Setup Complete!"
echo "IMPORTANT: Ensure Serial Port is enabled on your Raspberry Pi."
echo "1. Run 'sudo raspi-config'"
echo "2. Navigate to Interfacing Options -> Serial"
echo "3. Disable login shell over serial: NO"
echo "4. Enable serial port hardware: YES"
echo "   ALSO: Enable I2C (Interfacing Options -> I2C -> YES) for the LCD."
echo "5. Reboot"
echo "---------------------------------------------------"
echo "To run the app:"
echo "source env/bin/activate"
echo "python app.py"
