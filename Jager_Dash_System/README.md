# Jager_Dash Autonomous Vehicle System

Real-time, neon-futuristic control dashboard and backend architecture for the Jager_Dash Raspberry Pi-based autonomous vehicle.

## Quick Start (Raspberry Pi)

Follow these instructions to set up your environment and run the application natively on your Raspberry Pi.

### Prerequisites

Ensure you have Python 3 and `venv` tools installed on your Raspberry Pi. Open your Pi's terminal and run:

```bash
sudo apt update
sudo apt install python3 python3-venv python3-pip
```

### 1. Set Up the Environment
You only need to do this **once** to create the virtual environment and install the required dependencies (`Flask`, `opencv-python`, etc.).
Run the shortcut setup script in your terminal:

```bash
chmod +x setup_env.sh
./setup_env.sh
```

### 2. Activate the Environment
Every time you open a new SSH session or terminal window to work on or run the project, you need to activate the virtual environment so the system knows where the installed packages are.

```bash
source venv/bin/activate
```

*(You will know it is activated if you see `(venv)` at the beginning of your terminal prompt line).*

### 3. Hardware Requirements Check
Since you are running natively on the Raspberry Pi:
If you are ready to connect to real hardware (GPIO, i2c), please ensure you update `requirements.txt` to uncomment/include `RPi.GPIO`, `smbus2`, and `pyserial`. You will also need to update the classes in the `hardware/` directory to replace the Windows mock methods with real interface code.

### 4. Start the Server
With the environment activated, you can start the Flask backend server:

```bash
python3 app.py
```

### 5. Open the Dashboard
Once the server is running, open your web browser on any device (laptop, phone, tablet) connected to the same Wi-Fi network and navigate to the Pi's local IP address:

**http://<YOUR_PI_IP_ADDRESS>:5050**

---

## Directory Structure
- `app.py`: Main Flask application router.
- `navigation/`: State machine logic, A* routing integration, execution loops.
- `hardware/`: Interface files for the motor driver, camera, GPS, and sensors.
- `setup_env.sh`: Automated bash setup script for Raspberry Pi execution.
- `setup_env.ps1`: Automated PowerShell script if testing locally on Windows.
- `requirements.txt`: Python package dependency list.
- `templates/`: HTML structures.
- `static/`: CSS styling (Neon Future themes) and JS logic.


cd /home/pi/my-projects/Jager_Map_integration
git stash
git pull origin main
cd /home/pi/my-projects/Jager_Map_integration/Jager_Dash_System
source venv/bin/activate
python app.py