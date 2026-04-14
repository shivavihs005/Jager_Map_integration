# Jager_Dash Autonomous Vehicle System

Real-time, neon-futuristic control dashboard and backend architecture for the Jager_Dash Raspberry Pi-based autonomous vehicle.

## Quick Start (Windows)

Follow these instructions to set up your environment and run the application locally on your Windows machine to view the dashboard UI and logic.

### 1. Set Up the Environment
You only need to do this **once** to create the virtual environment and install the required dependencies (Flask, OpenCV, etc.).
Run the shortcut setup script in your PowerShell:

```powershell
.\setup_env.ps1
```

*(If you encounter an Execution Policy error in PowerShell, run it as `powershell -ExecutionPolicy Bypass -File setup_env.ps1`)*

### 2. Activate the Environment
Every time you open a new terminal window to work on or run the project, you need to activate the virtual environment so it knows where the installed packages are.

```powershell
.\venv\Scripts\Activate.ps1
```

*(You will know it is activated if you see `(venv)` at the beginning of your terminal prompt line).*

### 3. Start the Server
With the environment activated, you can start the Flask backend server:

```powershell
python app.py
```

### 4. Open the Dashboard
Once the server is running, open your web browser and navigate to the local host address:

**[http://127.0.0.1:5000](http://127.0.0.1:5000)**

---

## Directory Structure
- `app.py`: Main Flask application router.
- `navigation/`: State machine logic, A* routing integration, execution loops.
- `hardware/`: Interface files for the motor driver, camera, GPS, and sensors. (Currently configured to mock-mode for safe execution on Windows).
- `setup_env.ps1`: Automated PowerShell setup script.
- `requirements.txt`: Python package dependency list.
- `templates/`: HTML structures.
- `static/`: CSS styling (Neon Future themes) and JS logic.
