#!/bin/bash
# Shell script to set up environment on Raspberry Pi

# Update system and install python3-venv if not present
echo "Updating system..."
sudo apt-get update
sudo apt-get install -y python3-venv python3-pip

# Create virtual environment in 'env' folder
echo "Creating virtual environment..."
python3 -m venv env

# Activate and install requirements
echo "Installing dependencies..."
source env/bin/activate
pip install -r requirements.txt

# Enable Serial Port (Instructional)
echo "---------------------------------------------------"
echo "Setup Complete!"
echo "IMPORTANT: Ensure Serial Port is enabled on your Raspberry Pi."
echo "1. Run 'sudo raspi-config'"
echo "2. Navigate to Interfacing Options -> Serial"
echo "3. Disable login shell over serial: NO"
echo "4. Enable serial port hardware: YES"
echo "5. Reboot"
echo "---------------------------------------------------"
echo "To run the app:"
echo "source env/bin/activate"
echo "python app.py"
