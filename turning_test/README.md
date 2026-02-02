# Turning Test Standalone App

This is a standalone application to test autonomous turning logic.

## How to Run

1. Navigate to this directory:
   ```bash
   cd turning_test
   ```

2. Run the application:
   ```bash
   python app.py
   ```

3. Open your browser and go to:
   - `http://localhost:5001` (if running locally)
   - `http://<raspberry-pi-ip>:5001` (if running on Pi)

## Features
- **North/South/East/West Buttons**: Click to turn the car to that heading.
- **Simulation**: Uses dead-reckoning to simulate turning if no hardware is present (Mock Mode).
- **Hardware**: Controls Servo (Pin 18) and Motors (Pins 12/13) if on Raspberry Pi.
